from bokeh.core.properties import Tuple, String, Int
from bokeh.layouts import column
from bokeh.models import Button, CustomJS, RadioButtonGroup
from bokeh.io import show

class ICleanButtonGroup(RadioButtonGroup):
    """
    Custom extension of Bokeh Button that implements a websocket connection. For information on 
    Bokeh button see,
        https://docs.bokeh.org/en/latest/docs/reference/models/widgets.buttons.html

    Args:
        Button (Class): Basic button class from Bokeh.
    """
     

    __implementation__ = "button_group.ts"

    #socket = Tuple(String, Int, help="""
    #A tuple describing the websocket connection info: (string: address, port: int)
    #""")