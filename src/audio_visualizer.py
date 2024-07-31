import gc
import socket
import select
import time
import struct
import asyncio
from elastic_queue import Queue

class ClientError(Exception):
    pass

class Client:

    def __init__(self, reader, writer):
        self._reader = reader
        self._writer = writer

        self.last_read_duration_ms = 0

        self._config_buf = bytearray(struct.calcsize("!bb"))
        self._data_buf = bytearray(0)
        self.config = {}
        
    async def init_config(self):
        await self._read_data(self._config_buf)
        
        framerate = struct.unpack("!b", self._config_buf[0:1])[0] # type: ignore
        frequency_bands_count = struct.unpack("!b", self._config_buf[1:2])[0] # type: ignore

        frames_count = 1
        buffer_size = frames_count * frequency_bands_count
        self._data_buf = bytearray(buffer_size * struct.calcsize("!f"))

        config = {}
        config['framerate'] = framerate
        config['frames_count'] = frames_count
        config['frequency_bands_count'] = frequency_bands_count
        config['buffer_size'] = buffer_size
        config['period_ms'] = 1000 // framerate
        config['fft_unpack_fmt'] = f"!{buffer_size}f"
        config['buffer_length_ms'] = frames_count * config['period_ms']
        
        self.config = config
        
    @micropython.native
    async def _read_data(self, buf):
        bytes_read = 0
        buf_view = memoryview(buf)
        
        start_ms = time.ticks_ms()
        while bytes_read < len(buf):
            count = await self._reader.readinto(buf_view[bytes_read:]) # type: ignore
            bytes_read += count

        self.last_read_duration_ms = time.ticks_diff(time.ticks_ms(), start_ms)
        
    @micropython.native
    async def read_fft_data(self):
        start_ms = time.ticks_ms()
        fft_data = None

        await self._read_data(self._data_buf)
        fft_data = struct.unpack(self.config["fft_unpack_fmt"], self._data_buf)

        self.last_read_duration_ms = time.ticks_diff(time.ticks_ms(), start_ms)
        self._writer.write(b'1')
        await self._writer.drain() # type: ignore
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
    await client.init_config()
    return client

async def stop_task(task):
    task.cancel()    
    try:
        await task
    except asyncio.CancelledError:
        pass

@micropython.native
async def render(queue, config, device):
    # last_frame_ms = 0
    while True:
        # now_ms = time.ticks_ms()
        amplitudes = await queue.get()
        
        # elapsed_ms = time.ticks_diff(now_ms, last_frame_ms)
        # last_frame_ms = now_ms
        
        device.process_amplitudes(amplitudes, config['framerate'])

async def run(host, port, device):

    render_task = None
    client = None
    
    gc.collect()
    fft_values = None
    fft_queue = Queue(8)
    
    dropped_frames_count = 0
    count = 0
    
    try:
        while True:
            try:
                if client is None:
                    client = await connect(host, port)
                    render_task = asyncio.create_task(render(fft_queue, client.config, device))

                try:
                    fft_values = await client.read_fft_data()
                except ClientError as e:
                    print("Read error", e)
                    await stop_task(render_task)
                    render_task = None
                    await client.close()
                    client = None
                    gc.collect()
                    await asyncio.sleep_ms(30) # type: ignore
                    continue
                
                # TODO: ocassionally drop frames to prevent out of sync issues
                # TODO: reconnect strategy
                
                if dropped_frames_count < 50:
                    dropped_frames_count += 1
                    await asyncio.sleep_ms(30) # type: ignore
                    continue
                
                frames_count = client.config['frames_count']
                frame_size = client.config['frequency_bands_count']
                for i in range(0, frames_count):
                    frame = fft_values[i * frame_size:(i + 1) * frame_size] 
                    fft_queue.put_nowait(frame)
                
                # await asyncio.sleep_ms(client.config['buffer_length_ms'] - 6) # type: ignore
                # await asyncio.sleep_ms(client.config['buffer_length_ms'] - 6) # type: ignore

            except (ClientError, OSError) as e:
                if client is not None:
                    await stop_task(render_task)
                    render_task = None
                    await client.close()
                    client = None
                    gc.collect()
                await asyncio.sleep_ms(100) # type: ignore
                dropped_frames_count = 0
                print("Caught exception", e)

    except asyncio.CancelledError:
        if client:
            await stop_task(render_task)
            render_task = None
            await client.close()
            client = None
        gc.collect()
        print("Cancelled")