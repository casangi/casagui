
from bokeh.models import BoxZoomTool
from bokeh.plotting import ColumnDataSource
from bokeh.core.properties import Instance
from bokeh.util.compiler import TypeScript

class DownsampleBoxZoomTool(BoxZoomTool):
    __implementation__ = TypeScript("")

    def __init__( self, *args, **kwargs ):
        super( ).__init__( *args, **kwargs )
