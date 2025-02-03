import os
import ssl
import certifi
import urllib
import tarfile

import asyncio
import time
import numpy as np

from bokeh.plotting import figure, show
from bokeh.models import CustomJS
from casatools import ms as mstool
from casagui.utils import serialize, deserialize, find_ws_address
from casagui.bokeh.sources import UpdatableDataSource

ms_path = 'tl018b.ms'
ms_url = 'https://casa.nrao.edu/download/devel/casavis/data/tl018b_ms.tar.gz'

if not os.path.isdir(ms_path):
    try:
        context = ssl.create_default_context(cafile=certifi.where())
        tstream = urllib.request.urlopen(ms_url, context=context, timeout=400)
        tar = tarfile.open(fileobj=tstream, mode="r:gz")
        tar.extractall()
    except urllib.error.URLError:
        print("Failed to open connection to "+ms_url)
        raise

ms1 = mstool( )
ms1.open(ms_path)
ms1.msselect({'scan': "91",'baseline':"OV,PT"})

send_count = 0

data1 = None
data2 = None
domain = None
offset = 0
update_size = 1024 * 30

started_up_future = None
async def event_handler( msg ):
    global started_up_future
    print( '>>>ms-update>>event_handler>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>' )
    print( msg )
    started_up_future.set_result(True)
    return { 'result': "OK" }

source = UpdatableDataSource( dict(x=[], y1=[], y2=[]),
                              callback=event_handler,
                              js_init=CustomJS( args={},
                                                code='''this.send( {msg: 'STARTED'}, (msg) => { console.log('Recieved', msg) } )''' ),
                             )

# Create a plot
p = figure()
p.scatter('x', 'y1', source=source, color='blue')
p.scatter('x', 'y2', source=source, color='red')

show(p)

async def update_function( ):
    global data1, data2, domain, offset, update_size, send_count
    print(f"In update function at {time.strftime('%X')}")
    off = min(domain.size,offset+update_size)
    send_count = send_count + 1
    await source.update( dict( x=domain[offset:off], y1=data1[offset:off], y2=data2[offset:off], id=send_count ),
                         lambda reply: print( f'''\tcomplete: {reply}''' ) )
    offset = offset + update_size
    return True if offset >= domain.size else False

async def transmit(func, *args, **kwargs):
    global started_up_future, data1, data2, domain, send_count, update_size
    started_up_future = asyncio.Future( )
    await asyncio.sleep(0.5)
    data = ms1.getdata(['DATA'])
    data1 = np.abs(data['data'][0].flatten( ))
    data2 = np.abs(data['data'][1].flatten( ))
    domain = np.array(range(0,min(data1.size,data2.size)))
    await started_up_future
    stop = False
    while stop is False:
        await asyncio.sleep(0.01)
        stop = await func(*args, **kwargs)
        print( f'''Plot size:\t{send_count*update_size} (x2)''' )


async def main( ):
    global domain
    future = asyncio.Future( )
    def stop_function( result ):
        print( 'stop function', result )
        future.set_result( result )
    async with source.serve( stop_function ) as upsrc:
        task = asyncio.create_task(transmit(update_function))
        await future
        task.cancel( )

if __name__ == "__main__":
    asyncio.run(main())
