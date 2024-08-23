########################################################################
#
# Copyright (C) 2023
# Associated Universities, Inc. Washington DC, USA.
#
# This script is free software; you can redistribute it and/or modify it
# under the terms of the GNU Library General Public License as published by
# the Free Software Foundation; either version 2 of the License, or (at your
# option) any later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Library General Public
# License for more details.
#
# You should have received a copy of the GNU Library General Public License
# along with this library; if not, write to the Free Software Foundation,
# Inc., 675 Massachusetts Ave, Cambridge, MA 02139, USA.
#
# Correspondence concerning AIPS++ should be adressed as follows:
#        Internet email: casa-feedback@nrao.edu.
#        Postal address: AIPS++ Project Office
#                        National Radio Astronomy Observatory
#                        520 Edgemont Road
#                        Charlottesville, VA 22903-2475 USA
#
########################################################################
'''Implementation of ``DragTool`` class which provides a events or
callbacks in response to dragging gestures on a figure. Unlike the
PanTool all screen points use the plot's frame of reference instead
of the figure's frame of reference, i.e. sx=0, sy=0 is the lower
left corner of the plot.'''

from bokeh.models import Drag, Tool
from bokeh.core.properties import Instance, Nullable
from bokeh.models.callbacks import Callback
from os.path import join,dirname
from pathlib import Path

class DragTool(Drag):
    '''Tool that emits press and pressup events to signal start and end of drag'''

    start = Nullable(Instance(Callback), help="""
    JavaScript to be executed when dragging starts. If no start callback has been provided
    a PanStart event will be triggered when dragging starts.
    """)
    move = Nullable(Instance(Callback), help="""
    JavaScript to be executed as dragging progresses. If no move callback has been provided
    a Pan event will be triggered when dragging progresses.
    """)
    end = Nullable(Instance(Callback), help="""
    JavaScript to be executed when dragging ends. If no end callback has been provided
    a PanEnd event will be triggered when dragging stops.
    """)

    # explicit __init__ to support Init signatures
    def __init__(self, *args, **kwargs) -> None:
        ### neither svg files nor SVGIcon are supported by the icon parameter to a tool
        super().__init__(*args, icon=Path(join(dirname(dirname(dirname(__file__))),'__icons__','drag.png')), **kwargs )

Tool.register_alias("drag", lambda: DragTool())
