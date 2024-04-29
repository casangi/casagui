from bokeh.core.properties import Bool
from bokeh.models import Tabs

class CollapsibleTabs(Tabs):
    # explicit __init__ to support Init signatures
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    hidden = Bool( False, help='''
    Wether the TabPanels should be hidden upon startup.
    ''' )
