from bokeh.models import TickFormatter
from bokeh.util.compiler import TypeScript
from bokeh.core.properties import Instance, String
from casagui.bokeh.sources import ImageDataSource

class WcsTicks(TickFormatter):

    ## which axis are we labeling
    axis = String( )

    ## source containing the WCS information
    image_source = Instance(ImageDataSource)

    __implementation__ = TypeScript("")

    def __init__( self, *args, **kwargs ):
        super( ).__init__( *args, **kwargs )
