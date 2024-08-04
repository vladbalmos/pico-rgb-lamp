import gc
import socket
import select
import time
import struct
import asyncio
from elastic_queue import Queue

class Client:

    def __init__(self, reader, writer):
        self._reader = reader
        self._writer = writer

        self.last_read_duration_ms = 0
        self.last_sample_time_ms = 0
        self.last_sample_tstamp = 0

        self._config_buf = bytearray(struct.calcsize("!bb"))
        self._data_buf = bytearray(0)
        self.config = {}
        
    async def _acknowledge(self):
        '''
        Acknowledge the receipt of data
        Send a single byte back so that the ACK packet is sent as quickly as possible
        to prevent delaying the next data message
        '''
        self._writer.write(b'1')    
        await self._writer.drain()

    async def init_config(self):
        await self._read_data(self._config_buf)
        await self._acknowledge()
        
        samplerate = struct.unpack("!b", self._config_buf[0:1])[0] # type: ignore
        frequency_bands_count = struct.unpack("!b", self._config_buf[1:2])[0] # type: ignore

        frames_count = 1
        buffer_size = frames_count * frequency_bands_count
        self._data_buf = bytearray(buffer_size * struct.calcsize("!f"))

        config = {}
        config['samplerate'] = samplerate
        config['frames_count'] = frames_count
        config['frequency_bands_count'] = frequency_bands_count
        config['buffer_size'] = buffer_size
        config['period_ms'] = 1000 // samplerate
        config['fft_unpack_fmt'] = f"!{buffer_size}f"
        config['buffer_length_ms'] = frames_count * config['period_ms']
        
        self.config = config
        
    @micropython.native
    async def _read_data(self, buf):
        bytes_read = 0
        buf_view = memoryview(buf)
        
        now_ms = time.ticks_ms()
        while bytes_read < len(buf):
            count = await self._reader.readinto(buf_view[bytes_read:]) # type: ignore
            bytes_read += count

        self.last_read_duration_ms = time.ticks_diff(time.ticks_ms(), now_ms)
        
    @micropython.native
    async def read_fft_data(self):
        now_ms = time.ticks_ms()
        if self.last_sample_tstamp > 0:
            self.last_sample_time_ms = time.ticks_diff(now_ms, self.last_sample_tstamp)
            
        self.last_sample_tstamp = now_ms

        fft_data = None

        await self._read_data(self._data_buf)
        await self._acknowledge()

        fft_data = struct.unpack(self.config["fft_unpack_fmt"], self._data_buf)

        self.last_read_duration_ms = time.ticks_diff(time.ticks_ms(), now_ms)
        return fft_data
        
    async def close(self):
        try:
            self.config = {}
            self._data_buf = None
            self._config_buf = None
            self._reader = None
            self._writer.close() # type: ignore
            await self._writer.wait_closed() # type: ignore
            self._writer = None
        except:
            pass

async def connect(host, port):
    reader, writer = await asyncio.open_connection(host, port)
    client = Client(reader, writer)
    try:
        await asyncio.wait_for(client.init_config(), timeout=1)
    except asyncio.TimeoutError:
        await client.close()
        raise
    return client

async def stop_task(task):
    task.cancel()    
    try:
        await task
    except asyncio.CancelledError:
        pass

@micropython.native
async def render(queue, config, device):
    while True:
        amplitudes = await queue.get()
        device.process_amplitudes(amplitudes, config['samplerate'])

async def run(host, port, device):

    render_task = None
    client = None
    
    gc.collect()
    fft_values = None
    fft_queue = Queue(1)
    
    try:
        while True:
            try:
                if client is None:
                    try:
                        client = await connect(host, port)
                    except Exception as e:
                        print("Connection error", e)
                        await asyncio.sleep_ms(1000)
                        continue

                    render_task = asyncio.create_task(render(fft_queue, client.config, device))

                try:
                    fft_values = await client.read_fft_data()
                except asyncio.TimeoutError as e:
                    continue
                except Exception as e:
                    print("Read error", e)
                    await stop_task(render_task)
                    render_task = None
                    await client.close()
                    client = None
                    gc.collect()
                    await asyncio.sleep_ms(1000) # type: ignore
                    continue
                
                frames_count = client.config['frames_count']
                frame_size = client.config['frequency_bands_count']
                for i in range(0, frames_count):
                    frame = fft_values[i * frame_size:(i + 1) * frame_size] 
                    fft_queue.put_nowait(frame)
                
                await asyncio.sleep_ms(10) # type: ignore

            except OSError as e:
                if client is not None:
                    await stop_task(render_task)
                    render_task = None
                    await client.close()
                    client = None
                    gc.collect()
                await asyncio.sleep_ms(1000) # type: ignore
                print("Caught exception", e)

    except asyncio.CancelledError:
        if client:
            await stop_task(render_task)
            render_task = None
            await client.close()
            client = None
        gc.collect()
        print("Cancelled")