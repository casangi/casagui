from bokeh.core.properties import Tuple, String, Int
from bokeh.layouts import column
from bokeh.models import Slider
from bokeh.io import show

class ICleanSlider(Slider):
    """
    Custom extension of Bokeh Slider that implements a websocket connection. For information on 
    Bokeh slider see,
        https://docs.bokeh.org/en/latest/docs/reference/models/widgets.sliders.html

    Args:
        Slider (Class): Basic numerical slider class from Bokeh.
    """
     

    __implementation__ = "iclean_slider.ts"

    socket = Tuple(String, Int, help="""
    A tuple describing the websocket connection info: (string: address, port: int)
    """)