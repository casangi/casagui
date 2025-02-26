import os
import ssl
import certifi
import urllib
import tarfile

import numpy as np
from bokeh.models import CustomJS
from bokeh.plotting import figure, show
from casatools import ms as mstool
from casagui.utils import serialize, deserialize, find_ws_address

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
ms1.open('tl018b.ms')
ms1.msselect({'scan': "91",'baseline':"OV,PT"})

data1 = ms1.getdata(['DATA'])
print( f'''                                Rows in the full MS: {ms1.nrow( )}''' )
print( f'''                Rows without polarization selection: {ms1.nrow(True)}''' )
print( f'''          Data shape without polarization selection: {data1['data'].shape}''' )
print( f'''Type of data element without polarization selection: {type(data1['data'][0][0][0])}''' )

def abort_handler( self, err ):
    print(f'''Abort signaled from browser:\n    {err}''')
    ### signal shutdown here

p = figure( title="Amplitude Plot", x_axis_label="Spectral Index", y_axis_label="Amplitude" )
print( f'''Plot size:\t {data1['data'][0].size} (x2)''' )
p.scatter( list(range(data1['data'][0].size)), np.abs(data1['data'][0].flatten( )), color="blue" )
p.scatter( list(range(data1['data'][1].size)), np.abs(data1['data'][1].flatten( )), color="red" )

show(p)
