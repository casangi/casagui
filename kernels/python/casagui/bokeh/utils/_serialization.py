#-------------------------------------------------------------------------------
# Copyright (c) 2012 - 2021, Anaconda, Inc., and Bokeh Contributors
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
# Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
#
# Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# Neither the name of Anaconda nor the names of any contributors
# may be used to endorse or promote products derived from this software
# without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF
# THE POSSIBILITY OF SUCH DAMAGE.
#
#-------------------------------------------------------------------------------
#-- With the conversion from Bokeh 2.3.3 to 2.4.1 the transport of numpy      --
#-- arrays was broken. In time we may need to develop our own packing and     --
#-- unpacking routines for python/javascript however for the time being       --
#-- continuing to use transform_array( ) below from 2.3.3 solved the problem. --
#-------------------------------------------------------------------------------
#
#  This file is a subset of bokeh/util/serialization.py from the Bokeh
#  repository:
#
#  bash$ git config --get remote.origin.url
#  https://github.com/bokeh/bokeh.git
#  bash$
#
#--- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---
#  with the most recent release tag:
#
#  bash$ git show-ref --tags| tail -1
#  8ce5e80640cd16c9afd0045fcec42404ec59a818 refs/tags/2.3.2rc2
#  bash$
#
#--- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---
#  with these further revisions:
#
#  bash$ git log --pretty=oneline --no-merges 8ce5e80640cd16c9..HEAD bokeh/util/serialization.py
#  af9183f00dcff18a51a6a5af75099668463e3012 Add support for lazy annotations boilerplate (#11220)
#  bash$
#
#--- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---
#  which includes this difference:
#
#  bash$ git diff 8ce5e80640cd16c9afd0045fcec42404ec59a818 bokeh/util/serialization.py
#  diff --git a/bokeh/util/serialization.py b/bokeh/util/serialization.py
#  index a73a06358..eeeecf29a 100644
#  --- a/bokeh/util/serialization.py
#  +++ b/bokeh/util/serialization.py
#  @@ -18,6 +18,8 @@ performance and efficiency. The list of supported dtypes is:
#   #-----------------------------------------------------------------------------
#   # Boilerplate
#   #-----------------------------------------------------------------------------
#  +from __future__ import annotations
#  +
#   import logging # isort:skip
#   log = logging.getLogger(__name__)
#
#  bash$
#
#-----------------------------------------------------------------------------
'''
Functions for helping with serialization and deserialization of
Bokeh objects.

Certain NumPy array dtypes can be serialized to a binary format for
performance and efficiency. The list of supported dtypes is:

{binary_array_types}

'''

# pylint: skip-file

#-----------------------------------------------------------------------------
# Boilerplate
#-----------------------------------------------------------------------------
from __future__ import annotations

import logging # isort:skip
log = logging.getLogger(__name__)

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

# Standard library imports
import base64
import datetime as dt
import sys
import uuid
from math import isinf, isnan
from threading import Lock

# External imports
import numpy as np

#-----------------------------------------------------------------------------
# Globals and constants
#-----------------------------------------------------------------------------

#pd = import_optional('pandas')

BINARY_ARRAY_TYPES = {
    np.dtype(np.float32),
    np.dtype(np.float64),
    np.dtype(np.uint8),
    np.dtype(np.int8),
    np.dtype(np.uint16),
    np.dtype(np.int16),
    np.dtype(np.uint32),
    np.dtype(np.int32),
}

DATETIME_TYPES = {
    dt.time,
    dt.datetime,
    np.datetime64,
}

NP_EPOCH = np.datetime64(0, 'ms')
NP_MS_DELTA = np.timedelta64(1, 'ms')

DT_EPOCH = dt.datetime.utcfromtimestamp(0)

#__doc__ = format_docstring(__doc__, binary_array_types="\n".join("* ``np." + str(x) + "``" for x in BINARY_ARRAY_TYPES))

__all__ = (
    'transform_array',
    'convert_datetime_array',
    'serialize_array',
    'encode_base64_dict',
    'encode_binary_dict',
    'decode_base64_dict',
    'transform_array_to_list'
)

#-----------------------------------------------------------------------------
# General API
#-----------------------------------------------------------------------------

def convert_datetime_array(array):
    ''' Convert NumPy datetime arrays to arrays to milliseconds since epoch.

    Args:
        array : (obj)
            A NumPy array of datetime to convert

            If the value passed in is not a NumPy array, it will be returned as-is.

    Returns:
        array

    '''

    if not isinstance(array, np.ndarray):
        return array

    # not quite correct, truncates to ms..
    if array.dtype.kind == 'M':
        array =  array.astype('datetime64[us]').astype('int64') / 1000.

    elif array.dtype.kind == 'm':
        array = array.astype('timedelta64[us]').astype('int64') / 1000.

    # (bev) special case dates, not great
    elif array.dtype.kind == 'O' and len(array) > 0 and isinstance(array[0], dt.date):
        try:
            array = array.astype('datetime64[us]').astype('int64') / 1000.
        except Exception:
            pass

    return array

def array_encoding_disabled(array):
    ''' Determine whether an array may be binary encoded.

    The NumPy array dtypes that can be encoded are:

    {binary_array_types}

    Args:
        array (np.ndarray) : the array to check

    Returns:
        bool

    '''

    # disable binary encoding for non-supported dtypes
    return array.dtype not in BINARY_ARRAY_TYPES

def transform_array(array, force_list=False, buffers=None):
    ''' Transform a NumPy arrays into serialized format

    Converts un-serializable dtypes and returns JSON serializable
    format

    Args:
        array (np.ndarray) : a NumPy array to be transformed
        force_list (bool, optional) : whether to only output to standard lists
            This function can encode some dtypes using a binary encoding, but
            setting this argument to True will override that and cause only
            standard Python lists to be emitted. (default: False)

        buffers (set, optional) :
            If binary buffers are desired, the buffers parameter may be
            provided, and any columns that may be sent as binary buffers
            will be added to the set. If None, then only base64 encoding
            will be used (default: None)

            If force_list is True, then this value will be ignored, and
            no buffers will be generated.

            **This is an "out" parameter**. The values it contains will be
            modified in-place.


    Returns:
        JSON

    '''

    array = convert_datetime_array(array)

    return serialize_array(array, force_list=force_list, buffers=buffers)

def transform_array_to_list(array):
    ''' Transforms a NumPy array into a list of values

    Args:
        array (np.nadarray) : the NumPy array series to transform

    Returns:
        list or dict

    '''
    if (array.dtype.kind in ('u', 'i', 'f') and (~np.isfinite(array)).any()):
        transformed = array.astype('object')
        transformed[np.isnan(array)] = 'NaN'
        transformed[np.isposinf(array)] = 'Infinity'
        transformed[np.isneginf(array)] = '-Infinity'
        return transformed.tolist()
    #if (array.dtype.kind == 'O' and pd and pd.isnull(array).any()):
    #    transformed = array.astype('object')
    #    transformed[pd.isnull(array)] = 'NaN'
    #    return transformed.tolist()
    return array.tolist()

def serialize_array(array, force_list=False, buffers=None):
    ''' Transforms a NumPy array into serialized form.

    Args:
        array (np.ndarray) : the NumPy array to transform
        force_list (bool, optional) : whether to only output to standard lists
            This function can encode some dtypes using a binary encoding, but
            setting this argument to True will override that and cause only
            standard Python lists to be emitted. (default: False)

        buffers (set, optional) :
            If binary buffers are desired, the buffers parameter may be
            provided, and any columns that may be sent as binary buffers
            will be added to the set. If None, then only base64 encoding
            will be used (default: None)

            If force_list is True, then this value will be ignored, and
            no buffers will be generated.

            **This is an "out" parameter**. The values it contains will be
            modified in-place.

    Returns:
        list or dict

    '''
    if isinstance(array, np.ma.MaskedArray):
        array = array.filled(np.nan)  # Set masked values to nan
    if (array_encoding_disabled(array) or force_list):
        return transform_array_to_list(array)
    if not array.flags['C_CONTIGUOUS']:
        array = np.ascontiguousarray(array)
    if buffers is None:
        return encode_base64_dict(array)
    return encode_binary_dict(array, buffers)

def encode_binary_dict(array, buffers):
    ''' Send a numpy array as an unencoded binary buffer

    The encoded format is a dict with the following structure:

    .. code:: python

        {
            '__buffer__' :  << an ID to locate the buffer >>,
            'shape'      : << array shape >>,
            'dtype'      : << dtype name >>,
            'order'      : << byte order at origin (little or big)>>
        }

    Args:
        array (np.ndarray) : an array to encode

        buffers (set) :
            Set to add buffers to

            **This is an "out" parameter**. The values it contains will be
            modified in-place.

    Returns:
        dict

    '''
    buffer_id = make_id()
    buf = (dict(id=buffer_id), array.tobytes())
    buffers.append(buf)

    return {
        '__buffer__'  : buffer_id,
        'shape'       : array.shape,
        'dtype'       : array.dtype.name,
        'order'       : sys.byteorder,
    }

def encode_base64_dict(array):
    ''' Encode a NumPy array using base64:

    The encoded format is a dict with the following structure:

    .. code:: python

        {
            '__ndarray__' : << base64 encoded array data >>,
            'shape'       : << array shape >>,
            'dtype'       : << dtype name >>,
        }

    Args:

        array (np.ndarray) : an array to encode

    Returns:
        dict

    '''
    return {
        '__ndarray__' : base64.b64encode(array.data).decode('utf-8'),
        'shape'       : array.shape,
        'dtype'       : array.dtype.name,
        'order'       : sys.byteorder,
    }

def decode_base64_dict(data):
    ''' Decode a base64 encoded array into a NumPy array.

    Args:
        data (dict) : encoded array data to decode

    Data should have the format encoded by :func:`encode_base64_dict`.

    Returns:
        np.ndarray

    '''
    b64 = base64.b64decode(data['__ndarray__'])
    array = np.copy(np.frombuffer(b64, dtype=data['dtype']))
    if len(data['shape']) > 1:
        array = array.reshape(data['shape'])
    return array
