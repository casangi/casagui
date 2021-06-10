from bokeh.core.properties import Tuple, String, Int
from bokeh.layouts import column
from bokeh.models import Button, CustomJS
from bokeh.io import show

class ICleanButton(Button):
    """
    Custom extension of Bokeh Button that implements a websocket connection. For information on 
    Bokeh button see,
        https://docs.bokeh.org/en/latest/docs/reference/models/widgets.buttons.html

    Args:
        Button (Class): Basic button class from Bokeh.
    """
     

    __implementation__ = "iclean_button.ts"

    socket = Tuple(String, Int, help="""
    A tuple describing the websocket connection info: (string: address, port: int)
    """)