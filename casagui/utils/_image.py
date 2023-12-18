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
#        Internet email: aips2-request@nrao.edu.
#        Postal address: AIPS++ Project Office
#                        National Radio Astronomy Observatory
#                        520 Edgemont Road
#                        Charlottesville, VA 22903-2475 USA
#
########################################################################
'''image utilities'''

from os.path import isfile
from io import BytesIO
from pathlib import Path
import PIL.Image
import base64

def image_as_mime( path ):

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
