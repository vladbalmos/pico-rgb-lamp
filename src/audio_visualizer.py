import gc
import time
import struct
import asyncio

config_buf = bytearray(struct.calcsize("!bb"))
# fft_buf = bytearray(10 * struct.calcsize("!f"))
fft_buf = None
fft_config = {}

async def read_config(reader):
    buf = config_buf
    bytes_read = 0
    
    while bytes_read < len(buf):
        br = await reader.readinto(config_buf)
        bytes_read += br

    framerate = struct.unpack("!b", buf[0:1])[0]
    frequency_bands_count = struct.unpack("!b", buf[1:2])[0]
    return framerate, frequency_bands_count

async def read_data(reader):
    buf = fft_buf
    bytes_read = 0
    
    while bytes_read < len(buf): # type: ignore
        br = await reader.readinto(buf)
        bytes_read += br
    return buf

async def read_fft_data(reader):
    global fft_buf
    
    config = fft_config

    if 'framerate' not in fft_config:
        framerate, frequency_bands_count = await read_config(reader)
        
        config['framerate'] = framerate
        config['frequency_bands_count'] = frequency_bands_count
        config['period_ms'] = 1000 // framerate + 2
        fft_buf = bytearray(frequency_bands_count * struct.calcsize("!f"))
        config['fft_unpack_fmt'] = f"!{frequency_bands_count}f"
        print("Received config", config)

    data = await read_data(reader)
    fft_values = struct.unpack(config["fft_unpack_fmt"], data)
    return fft_values

async def run(host, port, device):
    global fft_config, fft_buf
    tcp_reader = None
    tcp_writer = None
    last_fft_ms = time.ticks_ms()
    last_output_ms = time.ticks_ms()
    config = fft_config
    
    gc.collect()
    lag_count = 0
    count = 0
    try:
        while True:
            if tcp_reader is None:
                print("Connecting to FFT stream")
                tcp_reader, tcp_writer = await asyncio.open_connection(host, port)

            try:
                start_ms = time.ticks_ms()
                fft_data = await read_fft_data(tcp_reader)
                now_ms = time.ticks_ms()
                read_duration_ms = time.ticks_diff(now_ms, start_ms)
                elapsed_ms = time.ticks_diff(now_ms, last_fft_ms)
                
                count += 1
                if elapsed_ms > config['period_ms']:
                    lag_count += 1
                    
                # if elapsed_ms < (config['period_ms'] - 4):
                #     last_fft_ms = time.ticks_ms()
                #     continue # Why?

                if time.ticks_diff(now_ms, last_output_ms) > 1000:
                    print(f"Total {count} Lagged: {lag_count}")
                    count = 0
                    lag_count = 0
                    last_output_ms = now_ms

                remaining_ms = config['period_ms'] - (elapsed_ms - config['period_ms'])
                if remaining_ms < 8:
                    # Skip processing this frame
                    last_fft_ms = time.ticks_ms()
                    print("Skipping frame", elapsed_ms, config['period_ms'], remaining_ms)
                    continue
                
                
                
                last_fft_ms = time.ticks_ms()
                sleep_ms = config['period_ms'] - read_duration_ms
                if sleep_ms < 1:
                    sleep_ms = 1
                await asyncio.sleep_ms(sleep_ms)

            except (EOFError) as e:
                fft_buf = None
                fft_config = {}
                tcp_reader = None
                tcp_writer.close() # type: ignore
                await tcp_writer.wait_closed() # type: ignore
                tcp_writer = None
                gc.collect()
                print("Disconnected", e)

    except asyncio.CancelledError:
        if tcp_writer is not None:
            fft_buf = None
            fft_config = {}
            tcp_writer.close()
            await tcp_writer.wait_closed()
            gc.collect()
        print("Cancelled")

    except Exception as e:
        print("Caught exception", e)