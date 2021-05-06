import numpy as np
from bokeh.plotting import figure, show

def bokehdemo01( ):
    N=4000
    x = np.random.random(size=N) * 100
    y = np.random.random(size=N) * 100
    radii = np.random.random(size=N) * 1.5
    colors = ["#%02x%02x%02x" % ( r, g, 150 ) for r, g in zip( np.floor(50+2*x).astype(np.int16), np.floor(30+2*y).astype(np.int16) )]
    p = figure( )
    p.circle( x, y, radius=radii, fill_color=colors, fill_alpha=0.6, line_color=None )
    show(p)
