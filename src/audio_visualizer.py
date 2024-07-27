import gc
import socket
import select
import time
import struct
import asyncio

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

        multiplier = 4
        buffer_size = multiplier * frequency_bands_count
        self._data_buf = bytearray(buffer_size * struct.calcsize("!f"))

        config = {}
        config['framerate'] = framerate
        config['frequency_bands_count'] = frequency_bands_count
        config['buffer_size'] = buffer_size
        config['period_ms'] = 1000 // framerate + 1
        config['fft_unpack_fmt'] = f"!{buffer_size}f"
        config['buffer_length_ms'] = multiplier * config['period_ms']
        
        self.config = config
        
    async def _read_data(self, buf):
        bytes_read = 0
        buf_view = memoryview(buf)
        
        start_ms = time.ticks_ms()
        while bytes_read < len(buf):
            count = await self._reader.readinto(buf_view[bytes_read:]) # type: ignore
            bytes_read += count

        self.last_read_duration_ms = time.ticks_diff(time.ticks_ms(), start_ms)
        
    async def read_fft_data(self):
        start_ms = time.ticks_ms()
        fft_data = None

        await self._read_data(self._data_buf)
        fft_data = struct.unpack(self.config["fft_unpack_fmt"], self._data_buf)

        self.last_read_duration_ms = time.ticks_diff(time.ticks_ms(), start_ms)
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

async def run(host, port, device):
    global fft_config, fft_buf

    client = None
    
    last_fft_data_ms = 0
    gc.collect()
    fft_values = None
    try:
        while True:
            try:
                now_ms = time.ticks_ms()
                if client is None:
                    client = await connect(host, port)

                try:
                    fft_values = await client.read_fft_data()
                except ClientError as e:
                    print("Read error", e)
                    await client.close()
                    client = None
                    gc.collect()
                    await asyncio.sleep_ms(64) # type: ignore
                    continue
                
                if fft_values is None:
                    await asyncio.sleep_ms(client.config['buffer_length_ms']) # type: ignore
                    continue
                
                # if fft_values and last_fft_data_ms > 0:
                #     elapsed_ms = time.ticks_diff(time.ticks_ms(), last_fft_data_ms)
                #     if elapsed_ms > 70:
                #         print("Elapsed", time.ticks_diff(time.ticks_ms(), last_fft_data_ms), "ms", client.last_read_duration_ms)
                #         # print(fft_values)
                    
                last_fft_data_ms = now_ms
                
                await asyncio.sleep_ms(client.config['buffer_length_ms']) # type: ignore

            except (ClientError, OSError) as e:
                if client is not None:
                    await client.close()
                    client = None
                    gc.collect()
                await asyncio.sleep_ms(100) # type: ignore
                print("Caught exception", e)

    except asyncio.CancelledError:
        if client:
            await client.close()
            client = None
        gc.collect()
        print("Cancelled")