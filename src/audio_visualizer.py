import time
import struct
import asyncio

size_buf = bytearray(struct.calcsize("!I"))
fft_buf = bytearray(10 * struct.calcsize("!f"))

# async def read_size(reader):
#     buf = size_buf
#     bytes_read = 0
    
#     while bytes_read < len(buf):
#         br = await reader.readinto(size_buf)
#         bytes_read += br

#     size = struct.unpack("!I", size_buf)[0]
#     return size

# async def read_data(reader, size):
#     buf = fft_buf
#     bytes_read = 0
    
#     while bytes_read < len(buf):
#         br = await reader.readinto(buf)
#         bytes_read += br
#     return buf

async def read_size(reader):
    prefix_size = struct.calcsize("!I")
    buf = await reader.readexactly(prefix_size)
    size = struct.unpack("!I", buf)[0]
    return size

async def read_data(reader, size):
    buf = await reader.readexactly(size)
    return buf

async def read_fft_data(reader, device):
    size = await read_size(reader)
    data = await read_data(reader, size)
    
    values_count = len(data) // struct.calcsize("!f")
    unpack_format = f'!{values_count}f'
    fft_values = struct.unpack(unpack_format, data)
    # print(fft_values)

async def run(host, port, device):
    tcp_reader = None
    tcp_writer = None
    last_fft_ms = time.ticks_ms()
    durations = []
    last_output_ms = time.ticks_ms()
    
    try:

        while True:
            if tcp_reader is None:
                print("Connecting to FFT stream")
                tcp_reader, tcp_writer = await asyncio.open_connection(host, port)

            try:
                start_ms = time.ticks_ms()
                await read_fft_data(tcp_reader, device)
                read_duration = time.ticks_diff(time.ticks_ms(), start_ms)
                now_ms = time.ticks_ms()
                diff = time.ticks_diff(now_ms, last_fft_ms)
                # durations.append(diff)
                
                if time.ticks_diff(now_ms, last_output_ms) > 1000:
                    print("Diff", diff, read_duration)
                    last_output_ms = now_ms
                
                # if len(durations) > 100:
                    # print(durations, sum(durations) / len(durations))
                    # print(sum(durations) / len(durations))
                    # durations.pop(0)
                last_fft_ms = now_ms
                await asyncio.sleep_ms(13)

            except (EOFError) as e:
                tcp_reader = None
                tcp_writer.close() # type: ignore
                await tcp_writer.wait_closed() # type: ignore
                tcp_writer = None
                print("Disconnected", e)

    except asyncio.CancelledError:
        if tcp_writer is not None:
            tcp_writer.close()
            await tcp_writer.wait_closed()
        print("Cancelled")

    except Exception as e:
        print("Caught exception", e)