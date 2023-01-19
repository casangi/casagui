import asyncio
import websockets

async def contact_server( ):
    async with websockets.connect( "ws://localhost:8765" ) as socket:
        await socket.send( "Hello world!!!" )
        print( await socket.recv( ) )

asyncio.run( contact_server( ) )
