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
'''Implementation of ``CBResetTool`` which is a version of the
``ResetTool`` which resets a graph and calls a callback to allow
 for resetting other state'''

from bokeh.models import ResetTool, Tool
from bokeh.core.properties import Instance, Nullable
from bokeh.models.callbacks import Callback

class CBResetTool(ResetTool):
    '''Tool that emits press and pressup events to signal start and end of drag'''

    precallback = Nullable(Instance(Callback), help="""
    Callback to be called before resetting the graph.
    """)

    postcallback = Nullable(Instance(Callback), help="""
    Callback to be called after resetting the graph.
    """)

    # explicit __init__ to support Init signatures
    def __init__(self, *args, **kwargs) -> None:
        ### neither svg files nor SVGIcon are supported by the icon parameter to a tool
        super().__init__(*args, **kwargs )

Tool.register_alias("cbreset", lambda: CBResetTool())
