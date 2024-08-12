import gc
import time
import json
import struct
import uasyncio as asyncio
from elastic_queue import Queue

class Client:

    def __init__(self, reader, writer):
        self._reader = reader
        self._writer = writer
        self.disconnected = False

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
        
        samplerate = struct.unpack("!b", self._config_buf[0:1])[0]
        frequency_bands_count = struct.unpack("!b", self._config_buf[1:2])[0]

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
        
    async def _read_data(self, buf):
        bytes_read = 0
        buf_view = memoryview(buf)
        
        now_ms = time.ticks_ms()
        while bytes_read < len(buf):
            count = await self._reader.readinto(buf_view[bytes_read:])
            bytes_read += count

        self.last_read_duration_ms = time.ticks_diff(time.ticks_ms(), now_ms)
        
    async def read_fft_data(self):
        now_ms = time.ticks_ms()
        if self.last_sample_tstamp > 0:
            self.last_sample_time_ms = time.ticks_diff(now_ms, self.last_sample_tstamp)
            
        self.last_sample_tstamp = now_ms

        fft_data = None

        await asyncio.wait_for(self._read_data(self._data_buf), timeout=0.5)
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
            self._writer.close()
            await self._writer.wait_closed()
            self._writer = None
            self.disconnected = True
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

async def render(queue, config, device):
    try:
        # visualizer_config = json.loads(device.get("audio_visualizer_config"))
        visualizer_config = device.get("audio_visualizer_config")
    except ValueError:
        visualizer_config = {}
    
    while True:
        amplitudes = await queue.get()
        device.process_amplitudes(amplitudes, config['samplerate'], visualizer_config)
        
async def disconnect(client, render_task):
    if render_task:
        await stop_task(render_task)
        
    if not client:
        return    

    await client.close()
    gc.collect()
    

async def run(host, port, device):
    render_task = None
    client = None
    
    gc.collect()
    fft_values = None
    fft_queue = Queue(1)
    
    try:
        while True:
            try:
                if client is None or client.disconnected:
                    try:
                        client = await connect(host, port)
                    except Exception as e:
                        print("Connection error", e)
                        await asyncio.sleep_ms(1000)
                        continue

                    print("Connected to FFT server")
                    render_task = asyncio.create_task(render(fft_queue, client.config, device))

                try:
                    fft_values = await client.read_fft_data()
                    fft_queue.put_nowait(fft_values)
                except Exception as e:
                    print("Read error", e)
                    await disconnect(client, render_task)
                    await asyncio.sleep_ms(1000)
                    continue
                
                await asyncio.sleep_ms(10)

            except OSError as e:
                await disconnect(client, render_task)
                await asyncio.sleep_ms(1000)
                print("Caught exception", e)

    except asyncio.CancelledError:
        await disconnect(client, render_task)
        print("Cancelled")