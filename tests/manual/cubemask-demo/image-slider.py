##
## image available at:
##
##    https://casa.nrao.edu/download/devel/casavis/data/g35-12co-img.tar.gz
##
import asyncio
from bokeh.plotting import show
from bokeh.layouts import row, column
from casagui.toolbox import CubeMask

cube = CubeMask( 'g35_sma_usb_12co.image' )
layout = column( cube.image( ),
                 cube.slider( ) )
cube.connect( )
show( layout )

try:
    loop = asyncio.get_event_loop( )
    loop.run_until_complete(cube.loop( ))
    loop.run_forever( )
except KeyboardInterrupt:
    print('\nInterrupt received, stopping GUI...')

print( f"cube exited with {cube.result( )}" )
