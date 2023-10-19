
from bokeh.models.callbacks import Callback
from bokeh.util.callback_manager import EventCallback
from bokeh.events import ButtonClick
from bokeh.models.widgets.buttons import AbstractButton
from bokeh.models.ui.icons import BuiltinIcon
from bokeh.core.properties import Instance, Required, Override, Nullable, Float, Int, Either
from bokeh.models import Tooltip



class TipButton(AbstractButton):
    """ A button with a help symbol that displays additional text when hovered
    over or clicked.
    """

    # explicit __init__ to support Init signatures
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    tooltip = Required(Instance(Tooltip), help="""
    A tooltip with plain text or rich HTML contents, providing general help or
    description of a widget's or component's function.
    """)

    hover_wait = Either( Float, Int, default=1.5, help='''
    amount of time (in seconds) to wait before displaying
    ''' )

    label = Override(default="")

    icon = Override(default=lambda: BuiltinIcon("help", size=18))

    button_type = Override(default="default")

    def on_click(self, handler: EventCallback) -> None:
        ''' Set up a handler for button clicks.

        Args:
            handler (func) : handler function to call when button is clicked.

        Returns:
            None

        '''
        self.on_event(ButtonClick, handler)

    def js_on_click(self, handler: Callback) -> None:
        ''' Set up a JavaScript handler for button clicks. '''
        self.js_on_event(ButtonClick, handler)
