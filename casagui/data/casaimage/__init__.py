########################################################################
#
# Copyright (C) 2023, 2024
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
'''image utilities'''

from os.path import isfile, exists
from io import BytesIO
from pathlib import Path
import PIL.Image
import base64

try:
    import casatools as ct
    from casatools import image as imagetool
except:
    ct = None
    from casagui.utils import warn_import
    warn_import('casatools')

def as_mime( path ):

    value = path
    if isinstance( value, str ) and isfile(value):
        value = Path(value)

    if isinstance( value, Path ):
        value = PIL.Image.open(value)

    if isinstance( value, PIL.Image.Image ):
        out = BytesIO()
        fmt = value.format or "PNG"
        value.save(out, fmt)
        encoded = base64.b64encode( out.getvalue() ).decode( 'ascii' )
        return f"data:image/{fmt.lower()};base64,{encoded}"

    raise RuntimeError( f'''could not load {path}''' )

def new( pattern, path, overwrite=False ):
    '''Create a new image using ``pattern`` as a pattern. ``pattern`` supplies the
    shape for the new image as well as the coordinate system for the new image.

    Parameters
    ----------
    path: str
        path to the image to be created

    pattern: str
        path to the image on which the new image should be based

    overwrite: bool
        overwrite any existing image, directory or file
    '''
    if ct is None:
        raise RuntimeError( 'casaimage.new: casatools is not available' )
    if exists(path) and not overwrite:
        raise RuntimeError( '''casaimage.new: image already exists (and 'overwrite=False')''' )
    if not exists(pattern):
        raise RuntimeError( 'casaimage.new: an original image is required' )
    im = imagetool( )
    im.open(pattern)
    print(repr(im.coordsys( )))
    newim = im.newimagefromshape( path, shape=im.shape( ), csys=im.coordsys( ).torecord( ), overwrite=overwrite )
    im.close( )
    im.done( )
    result = newim.name( )
    newim.close( )
    newim.done( )
    return result

def shape( path ):
    '''Return the shape of an image.

    Parameters
    ----------
    path: str
        path to the image

    Returns
    -------
    list of int
        shape of image
    '''
    if not exists(path):
        raise RuntimeError( '''casaimage.shape: image does not exist''' )
    im = imagetool( )
    im.open(path)
    result = im.shape( )
    im.close( )
    im.done( )
    return result
