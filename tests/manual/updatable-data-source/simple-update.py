import asyncio
import time

from bokeh.plotting import figure, show
from bokeh.models import CustomJS

from casagui.bokeh.sources import UpdatableDataSource

started_up_future = None
async def event_handler( msg ):
    global started_up_future
    print('>>>>>RECEIVED>>EVENT>>>>>>>>>>>>>',msg)
    started_up_future.set_result(True)
    return { 'result': "OK" }

source = UpdatableDataSource( dict(x=[1, 2, 3], y=[4, 5, 6]),
                              callback=event_handler,
                              js_init=CustomJS( args={},
                                                code='''this.send( {msg: 'STARTED'}, (msg) => { console.log('Recieved', msg) } )''' ),
                             )

# Create a plot
p = figure()
p.scatter('x', 'y', source=source)

# Update the data
source.data = dict(x=[ ], y=[ ])

show(p)

xoff = 4
yoff = 7
async def update_function( ):
    global xoff, yoff
    print(f"In update function at {time.strftime('%X')}")
    await source.update( dict( x=[xoff, xoff+1, xoff+2], y=[yoff, yoff+1, yoff+2] ) )
    xoff = xoff+3
    yoff = yoff+3

async def periodic(interval, func, *args, **kwargs):
    global started_up_future
    started_up_future = asyncio.Future( )
    await started_up_future
    while True:
        await asyncio.sleep(interval)
        await func(*args, **kwargs)

async def main( ):
    future = asyncio.Future( )
    def stop_function( result ):
        print( 'stop function', result )
        future.set_result( result )
    task = asyncio.create_task(periodic(5, update_function))
    async with source.serve( stop_function ) as upsrc:
        await future
        task.cancel( )

if __name__ == "__main__":
    asyncio.run(main())
