########################################################################3
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
########################################################################3
from socket import socket
from os import path as __path

def path_to_url( path ):
    """Convert a single filesystem path to a URL.

    If the string specified in the ``path`` parameter exists. It is turned into a
    fully qualified path and converted to a URL and returned. If ``path`` does not
    exist, ``path`` is returned unchanged.

    Parameters
    ----------
    path: str
        path to be checked and expanded

    Returns
    -------
    str
        ``path`` converted to a URL if ``path`` exists, otherwise ``path`` unchanged
    """
    return "file://" + __path.abspath(path) if __path.exists(path) else path

def find_ws_address( ip='127.0.0.1' ):
    """Find free port on ``ip`` network and return a tuple with ``ip`` and port number

    This function uses the low level socket function to find a free port and return
    a tuple representing the address plus port number.

    Parameters
    ----------
    ip: str
        network to be probed for an available port

    Returns
    -------
    tuple of str and int
        network address (`str`) and port number (`int`)
    """
    sock = socket( )
    sock.bind((ip,0))
    result = sock.getsockname( )
    sock.close( )
    return result
