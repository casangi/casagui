########################################################################
#
# Copyright (C) 2021
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
#        Internet email: aips2-request@nrao.edu.
#        Postal address: AIPS++ Project Office
#                        National Radio Astronomy Observatory
#                        520 Edgemont Road
#                        Charlottesville, VA 22903-2475 USA
#
########################################################################
'''Contains for conversion of data passed between Python and JavaScript
via websockets'''

import numpy as np
from ._serialization import transform_array


def pack_arrays( val ):
    """Convert `numpy` N dimensional arrays stored within a dictionary to
    a format that can be converted into the multi-dimensional arrays that
    are usable for Bokeh data.

    Parameters
    ----------
    val: value

    Returns
    -------
    value
        return value is identical to `val` parameter except that any
        N dimensional `numpy` arrays are converted to Bokeh compatible
        format
    """
    if isinstance( val, dict ):
        result = { }
        for k, v in val.items( ):
            result[k] = pack_arrays(v)
        return result
    if isinstance( val, np.ndarray ):
        return transform_array(val,force_list=True)
    if isinstance( val, range ):
        return list(val)
    return val
