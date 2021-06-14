from bokeh.core import properties
from bokeh.models.widgets import AbstractIcon

class SVGIcon(AbstractIcon):
    """
    The SVGIcon can be used to add SVG based icons to buttons, menus etc.

    See https://github.com/holoviz/panel/issues/1586 for motivation, possibilities 
    and requirements.

    Args:
        AbstractIcon (Abstract Class): Abstract class that can be used to 
        build custom Icon classes from.
    """
    

    __implementation__ = "svg_icon.ts"

    icon_name = properties.String()
    size = properties.Float()
    fill_color = properties.String()
    spin_duration = properties.Int()
