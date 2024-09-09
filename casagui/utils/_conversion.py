########################################################################
#
# Copyright (C) 2021,2023
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
'''Contains for conversion of data passed between Python and JavaScript
via websockets'''

import json
import numpy as np
from bokeh.util.serialization import transform_array
from bokeh.core.serialization import Serializer, Deserializer
from bokeh.core.json_encoder import serialize_json
from ._static import static_vars

def strip_arrays( val ):
    '''convert all numpy arrays contained within val to lists
    '''
    if isinstance( val, dict ):
        result = { }
        for k, v in val.items( ):
            result[k] = strip_arrays(v)
        return result
    if isinstance( val, np.ndarray ):
        return val.tolist( )
    if isinstance( val, range ):
        return list(val)
    return val

@static_vars( encoder=Serializer(deferred=False) )
def serialize( val ):
    '''convert python values to a string that can be sent via websockets
    '''
    return serialize_json(serialize.encoder.serialize(val))

@static_vars( decoder=Deserializer( ) )
def deserialize( val ):
    '''convert an encoded value received from websockets
    '''
    value = json.loads(val)
    return deserialize.decoder.deserialize(value)

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
        if isinstance(val, np.ma.MaskedArray):
            return transform_array(val.filled(0))
        else:
            return transform_array(val)
    if isinstance( val, range ):
        return list(val)
    return val
