import gc
import socket
import select
import time
import struct
import asyncio

class ClientError(Exception):
    pass

class Client:

    def __init__(self, sock):
        self._sock = sock
        self._sock.setblocking(False)

        self._poller = select.poll()
        self._poller.register(self._sock, select.POLLIN)

        self.last_read_duration_ms = 0

        self._config_buf = bytearray(struct.calcsize("!bb"))
        self._data_buf = bytearray(0)
        
        self.config = self._read_config()
        
    def _read_data(self, buf, timeout_ms = 1):
        read_timedout = True
        start_ms = time.ticks_ms()
        for sock, event in self._poller.ipoll(timeout_ms): # type: ignore
            if event & select.POLLIN:
                bytes_read = sock.readinto(buf)
                if bytes_read != len(buf):
                    raise ClientError("Failed to read enough data")
                read_timedout = False
                break
            
            if event & select.POLLERR or event & select.POLLHUP:
                raise ClientError("Socket error")
            
        self.last_read_duration_ms = time.ticks_diff(time.ticks_ms(), start_ms)
        return not read_timedout
        
    def _read_config(self):
        if not self._read_data(self._config_buf, 1000):
            raise ClientError("Config read timed out")

        framerate = struct.unpack("!b", self._config_buf[0:1])[0] # type: ignore
        frequency_bands_count = struct.unpack("!b", self._config_buf[1:2])[0] # type: ignore

        frames_count = 4 * frequency_bands_count
        self._data_buf = bytearray(frames_count * struct.calcsize("!f"))

        config = {}
        config['framerate'] = framerate
        config['frequency_bands_count'] = frequency_bands_count
        config['period_ms'] = 1000 // framerate + 1
        config['fft_unpack_fmt'] = f"!{frames_count}f"
        
        return config
        
    def read_fft_data(self):
        start_ms = time.ticks_ms()
        fft_data = None

        if self._read_data(self._data_buf, 1):
            fft_data = struct.unpack(self.config["fft_unpack_fmt"], self._data_buf)

        self.last_read_duration_ms = time.ticks_diff(time.ticks_ms(), start_ms)
        return fft_data
        
    def close(self):
        try:
            self._data_buf = None
            self._config_buf = None
            self.config = {}

            self._poller.unregister(self._sock) # type: ignore
            self._poller = None
            self._sock.close() # type: ignore
            self._sock = None
        except:
            pass

def connect(host, port):
    global fft_buf
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    print("Getting address info")
    addr_info = socket.getaddrinfo(host, port)
    print("Got address info")
    print("Connecting")
    sock.connect(addr_info[0][-1])
    print("Connected")
    
    client = Client(sock)
    return client

async def run(host, port, device):
    global fft_config, fft_buf

    client = None
    
    last_fft_data_ms = 0
    last_output_ms = time.ticks_ms()
    gc.collect()
    fft_values = None
    default_sleep_ms = 13
    try:
        while True:
            try:
                now_ms = time.ticks_ms()
                if client is None:
                    client = connect(host, port)

                try:
                    fft_values = client.read_fft_data()
                except ClientError as e:
                    print("Read error", e)
                    client.close()
                    client = None
                    gc.collect()
                    await asyncio.sleep_ms(64)
                    continue
                
                if fft_values is None:
                    await asyncio.sleep_ms(4 * client.config["period_ms"])
                    continue
                
                if fft_values and last_fft_data_ms > 0:
                    elapsed_ms = time.ticks_diff(time.ticks_ms(), last_fft_data_ms)
                    if elapsed_ms > 25:
                        print("Elapsed", time.ticks_diff(time.ticks_ms(), last_fft_data_ms), "ms", client.last_read_duration_ms)
                    
                last_fft_data_ms = now_ms
                
                await asyncio.sleep_ms(4 * client.config["period_ms"])

            except (ClientError, OSError) as e:
                if client is not None:
                    client.close()
                    client = None
                    gc.collect()
                await asyncio.sleep_ms(100)
                print("Caught exception", e)

    except asyncio.CancelledError:
        client.close()
        client = None
        gc.collect()
        print("Cancelled")