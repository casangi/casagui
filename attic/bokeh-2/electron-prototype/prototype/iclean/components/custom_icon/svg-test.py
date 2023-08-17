from bokeh.layouts import column
from bokeh.models import Button, CustomJS
from bokeh.plotting import show

from svg_icon import SVGIcon

btn = Button(
    icon=SVGIcon(icon_name="stop",
    fill_color="#E1477E",
    spin_duration=2000), 
    label="", 
    button_type="light", 
    default_size=10,
    height_policy="fit", 
    width_policy="fit", 
    margin=(0, 0, 0, 0), 
    sizing_mode="fixed", 
    width=50, 
    height=50 )

btn.js_on_click(CustomJS(code="alert('It works!')"))

show(column(btn))
