from bokeh.models import Tooltip
from bokeh.models.layouts import LayoutDOM, UIElement
from bokeh.core.properties import Instance, Required, Float, Int, Either

class Tip(LayoutDOM):
    '''Display a tooltip for the child element
    '''

    def __init__(self, *args, **kwargs) -> None:
        if len(args) != 1 and "child" not in kwargs:
            raise ValueError("a 'child' argument must be supplied")
        elif len(args) == 1 and "child" in kwargs:
            raise ValueError("'child' supplied as both a positional argument and a keyword")
        elif len(args) > 1:
            raise ValueError("only one 'child' can be supplied as a positional argument")
        elif len(args) > 0:
            kwargs["child"] = args[0]

        super().__init__(**kwargs)

    child = Required(Instance(UIElement), help="""
    A child, which can be other components including plots, rows, columns, and widgets.
    """)

    tooltip = Required(Instance(Tooltip), help="""
    A tooltip with plain text or rich HTML contents, providing general help or
    description of a widget's or component's function.
    """)

    hover_wait = Either( Float, Int, default=1.5, help='''
    amount of time (in seconds) to wait before displaying
    ''' )

    def _sphinx_height_hint(self):
        if child._sphinx_height_hint() is None:
            return None
        return child._sphinx_height_hint()
