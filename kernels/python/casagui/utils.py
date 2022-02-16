########################################################################
#
# Copyright (C) 2021,2022
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
'''General utility functions used by the ``casagui`` tools and applications.'''

from itertools import groupby, chain
from socket import socket
from os import path as __path
import requests


def static_vars(**kwargs):
    '''Initialize static function variables to for use within a function.

    This function is used as a decorator which allows for the initialization of
    static local variables for use within a function. It is used like:

            @static_vars(counter=0)
            def foo():
                foo.counter += 1
                print "Counter is %d" % foo.counter

    This is used from:
    https://stackoverflow.com/questions/279561/what-is-the-python-equivalent-of-static-variables-inside-a-function?rq=1

    Parameters
    ----------
    Initialized static local variables.
    '''
    def decorate(func):
        for k,v in kwargs.items( ):
            setattr(func, k, v)
        return func
    return decorate

def static_dir(func):
    '''return a list of static variables associated with ``func``

    Parameters
    ----------
    func: function
        function with static variables
    '''
    return [a for a in dir(func) if a[0] != '_']

def path_to_url( path ):
    '''Convert a single filesystem path to a URL.

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
    '''
    return "file://" + __path.abspath(path) if __path.exists(path) else path

def find_ws_address( address='127.0.0.1' ):
    '''Find free port on ``address`` network and return a tuple with ``address`` and port number

    This function uses the low level socket function to find a free port and return
    a tuple representing the address plus port number.

    Parameters
    ----------
    address: str
        network to be probed for an available port

    Returns
    -------
    tuple of str and int
        network address (`str`) and port number (`int`)
    '''
    sock = socket( )
    sock.bind((address,0))
    result = sock.getsockname( )
    sock.close( )
    return result

def partition(pred, iterable):
    '''Split ``iterable`` into two lists based on ``pred`` predicate.
    '''
    trues = []
    falses = []
    for item in iterable:
        if pred(item):
            trues.append(item)
        else:
            falses.append(item)
    return trues, falses


@static_vars(url='http://clients3.google.com/generate_204')
def have_network( ):
    '''check to see if an active network with general internet connectivity
    is available. returns ``True`` if we have internet connectivity and
    ``False`` if we do not.
    '''
    ###
    ### see: https://stackoverflow.com/questions/50558000/test-internet-connection-for-python3
    ###
    try:
        response = requests.get(have_network.url, timeout=5)
        return response.status_code == 204
    except requests.exceptions.HTTPError:
        ### http error
        return False
    except requests.exceptions.ConnectionError:
        ### connection error
        return False
    except requests.exceptions.Timeout:
        ### timeout
        return False
    except requests.exceptions.RequestException:
        ### some generic error
        return False
    except Exception:
        ### reachable?
        return False

def convert_js_masks( jsresult, coord='world', format='crtf', result_type='str' ):
    if format == 'raw':
        def convert_elem( vec, f=lambda x: x ):
            result = { }
            for chan_or_poly in vec:
                result[f(chan_or_poly[0])] = chan_or_poly[1]
            return result
        return { 'masks': convert_elem(jsresult['masks'],tuple), 'polys': convert_elem(jsresult['polys']) }
    if format == 'crtf' and coord == 'pixel':
        unique_polygons={ }
        ###
        ### collect masks ordered by (poly_index,dx,dy)
        ###
        for [index,mask] in jsresult['masks']:
            for poly in mask:
                unique_poly = tuple([poly['p']] + poly['d'])
                if unique_poly in unique_polygons:
                    unique_polygons[unique_poly] += [ index ]
                else:
                    unique_polygons[unique_poly] = [ index ]

        polygon_definitions = { index: poly for [ index, poly ] in jsresult['polys'] }

        ###
        ### collect channels into contiguous channel ranges
        ###
        def ranges(i):
            for a, b in groupby(enumerate(sorted(i)), lambda pair: pair[1] - pair[0]):
                b = list(b)
                yield b[0][1], b[-1][1]

        ###
        ### create a region list given the index of the polygon used, the x/y translation, and the
        ### channels the region should be found on
        ###
        def create_regions( poly_index, xlate, channels ):
            if polygon_definitions[poly_index]['type'] == 'poly':
                poly_pts = ','.join( [ f"[{x+xlate[0]}pix,{y+xlate[1]}pix]"
                                       for x in polygon_definitions[poly_index]['geometry']['xs']
                                       for y in polygon_definitions[poly_index]['geometry']['ys'] ] )
                return [ f"poly[{poly_pts}],range=[{r[0]}chan,{r[1]}chan]" for r in ranges([c[1] for c in channels]) ]
            if polygon_definitions[poly_index]['type'] == 'rect':
                xs = polygon_definitions[poly_index]['geometry']['xs']
                ys = polygon_definitions[poly_index]['geometry']['ys']
                box_pts = f"[{min(xs)}pix,{min(ys)}pix],[{max(xs)}pix,{max(ys)}pix]"
                return [ f"box[{box_pts}],range=[{r[0]}chan,{r[1]}chan]" for r in ranges([c[1] for c in channels]) ]

        ###
        ### generate CFTF
        ###
        result = [ create_regions( index[0], index[1:], channels ) for index,channels in unique_polygons.items( ) ]
        if result_type == 'str':
            return '\n'.join(chain.from_iterable(result))
        if result_type == 'list':
            return result
        raise RuntimeError(f"unknown result_type ({result_type})")
    raise RuntimeError(f"invalid format ({format}), or coord ({coord})")
