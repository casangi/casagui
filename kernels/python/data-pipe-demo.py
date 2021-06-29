import os
from uuid import uuid4
from casagui.bokeh.state import initialize_bokeh
#initialize_bokeh( "casaguijs/dist/casaguijs.min.js" )        ### local build
initialize_bokeh(dev=2)                                       ### fetch from https://casa.nrao.edu/
from bokeh.plotting import ColumnDataSource
from casagui.bokeh.sources import DataPipe
from casagui.utils import find_ws_address
from bokeh.layouts import column, row, Spacer
from bokeh.plotting import figure, show
from bokeh.models import TextInput, Button, Paragraph, CustomJS

import asyncio
import websockets
from random import randint

import numpy as np
from math import sin, cos, tan, fabs

pipe = DataPipe( address=find_ws_address( ) )
### all elemens of columndatasource must be same size
yinit = [ "list(np.linspace(6,5+1/25,25)) + list(np.linspace(5,2+3/25,25)) + list(np.linspace(2,4-2/25,25)) + list(np.linspace(4,7-3/25,25))",
          "list(map(lambda x: fabs(sin(x)),np.linspace(0,5,100)))",
          "list(map(lambda x: x**2 / 4, np.linspace(0,5,100)))" ]
cds = ColumnDataSource( data = { 'x1': np.linspace(0,5,100),
                                 'y1': eval(yinit[0]),
                                 'x2': np.linspace(0,5,100),
                                 'y2': eval(yinit[1]),
                                 'x3': np.linspace(0,5,100),
                                 'y3': eval(yinit[2])
                                } )


fig = figure( plot_height=500, plot_width=500 )
fig.line( x='x1', y='y1', source=cds )
fig.line( x='x2', y='y2', source=cds )
fig.line( x='x3', y='y3', source=cds )

inputs = []
for num in [0,1,2]:
    inputs.append( TextInput( value=yinit[num], default_size=400 ) )

threshold = TextInput( value="0.5", default_size=100 )

send = Button( label="send", max_width=40 )
cont = Button( label="continue", max_width=60 )
cont_id = str(uuid4( ))

send.js_on_click( CustomJS( args=dict( cont_id=cont_id, cds=cds, inputs=inputs, pipe=pipe ), code="""
    function update_plot( msg ) {
        cds.data = msg.value
    }
    pipe.send( cont_id,
               { action: 'calculate',
                 value: { y1: inputs[0].value,
                          y2: inputs[1].value,
                          y3: inputs[2].value } },
                 update_plot )
""" ) )

cont.js_on_click( CustomJS( args=dict(cont=cont, send=send, cont_id=cont_id, pipe=pipe, threshold=threshold), code="""
    function from_python( msg ) {
        console.log("in from_python(", msg, ")")
        if ( msg.action === "unsleep" ) {
            cont.label = "continue"
            cont.disabled = false
            send.disabled = false
        } else if ( msg.action === "sleep" ) {
            cont.label = "sleeping: " + msg.value.toString( )
        }
        return { 'action': 'nop' }
    }
    function to_python_cb( msg ) {
        console.log("in to_python_cb(", msg, ")")
        if ( msg.action === 'sleep' ) {
            send.disabled = true
            cont.disabled = true
            cont.label = "sleeping: " + msg.value.toString( )
        }
    }
    if ( ! ('cont_callback_initialized' in cont )) {
        console.log("do initialize here")
        console.log("uuid:", cont_id)
        pipe.register( cont_id, from_python )
        cont.cont_callback_initialized = true
    }
    pipe.send( cont_id, {action: 'continue', threshold: threshold.value}, to_python_cb )
""" ) )

loop = asyncio.get_event_loop( )
print("uuid: %s" % cont_id)

clean_wait_ticks = 0

def awaken_ack( msg ):
    return { 'action': 'ack', 'value': True }

async def awaken_gui( ):
    await pipe.send( cont_id, { 'action': 'unsleep' }, awaken_ack )
async def update_sleeping_gui( value ):
    await pipe.send( cont_id, { 'action': 'sleep', 'value': value }, awaken_ack )


layout = column( fig,
                 row ( column( row( Paragraph(text='y1'), inputs[0] ),
                               row( Paragraph(text='y2'), inputs[1] ),
                               row( Paragraph(text='y3'), inputs[2] ) ),
                       send ),
                 Spacer(width=400, height=1, background="black", sizing_mode='scale_width'),
                 row( Paragraph(text="threshold"), threshold, cont ) )

show(layout)


def handle_continue_send( msg ):
    if msg['action'] == 'continue':
        global clean_wait_ticks
        clean_wait_ticks = randint(2,10)
        return { 'action': 'sleep', 'value': clean_wait_ticks }
    else:
        value = msg['value']
        return { 'action': 'result',
                 'value': { 'x1': list(np.linspace(0,5,100)),
                            'y1': eval(value['y1']),
                            'x2': list(np.linspace(0,5,100)),
                            'y2': eval(value['y2']),
                            'x3': list(np.linspace(0,5,100)),
                            'y3': eval(value['y3']) } }

pipe.register( cont_id, handle_continue_send )

async def check_state( ):
    global clean_wait_ticks
    if clean_wait_ticks > 0:
        clean_wait_ticks -= 1
        if clean_wait_ticks == 0:
            await awaken_gui( )
        else:
            await update_sleeping_gui( clean_wait_ticks )

async def periodic( ):
    while True:
        await asyncio.gather( asyncio.sleep(1), check_state( ) )

async def async_loop( f1, f2 ):
    res = await asyncio.gather(  f1, f2 )

start_server = websockets.serve( pipe.process_messages, pipe.address[0], pipe.address[1] )
loop.run_until_complete(async_loop(start_server, periodic( )))
loop.run_forever()
