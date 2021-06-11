from bokeh.layouts import column
from bokeh.models import Button, CustomJS
from bokeh.plotting import show

from awesome_icon import AwesomeIcon

btn = Button(icon=AwesomeIcon(icon_name="play", size=2),
             label="")
btn.js_on_click(CustomJS(code="alert('It works!')"))

show(column(btn))
