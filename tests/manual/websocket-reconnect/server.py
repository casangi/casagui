import time
import asyncio
import websockets
import traceback

message_count = 0
async def timeserver( websocket ):
    global message_count
    try:
        async for message in websocket:
            message_count += 1
            print(f'{message_count}\t{message}')
            await websocket.send(time.strftime('%Y-%m-%d.%H:%M:%S'))
    except websockets.exceptions.ConnectionClosedError:
        print('browser connection dropped...')
    except Exception:
        print(traceback.print_exc())

async def main( ):
    async with websockets.serve( timeserver, "localhost", 8765 ):
        await asyncio.Future( )

asyncio.run(main( ))
