
from bokeh.models import BoxZoomTool
from bokeh.plotting import ColumnDataSource
from bokeh.core.properties import Instance
from bokeh.util.compiler import TypeScript
from ..models import DownsampleState

class ImageBoxZoomTool(BoxZoomTool):
    downsample_state = Instance(DownsampleState)
    __implementation__ = TypeScript("")

    def __init__( self, downsample_state, *args, **kwargs ):
        super( ).__init__( *args, **kwargs )
        self.downsample_state = downsample_state
