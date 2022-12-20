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

import inspect
import itertools
import urllib.request
import urllib.error
import sys

from itertools import groupby, chain
from socket import socket
from os import path as __path
from ._ResourceManager import _ResourceManager
from ._logging import get_logger
from ._regions import polygon_indexes
from ._docenum import DocEnum

from astropy import units as u
from regions import PixCoord
from regions import RectanglePixelRegion, PolygonPixelRegion

try:
    from casatools import regionmanager

    __have_casatools = True
except ImportError:
    __have_casatools = False

logger = get_logger()

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
        for k, v in kwargs.items():
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


@static_vars(mgr=None)
def resource_manager( ):
    if resource_manager.mgr is None:
        resource_manager.mgr = _ResourceManager( )
    return resource_manager.mgr

def reset_resource_manager( ):
    if resource_manager.mgr is not None:
        resource_manager.mgr = _ResourceManager( )

def path_to_url(path):
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


def find_ws_address(address='127.0.0.1'):
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
    sock = socket()
    sock.bind((address, 0))
    result = sock.getsockname()
    sock.close()
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


def error_msg(*args, **kwargs):
    '''standard method for reporting errors which do not result in aborting out of python

    This function takes the standard set of arguments that the python ``print`` function takes.
    The primary difference is that the output will go to ``stderr`` and perhaps other error
    logs.
    '''
    print(*args, file=sys.stderr, **kwargs)


@static_vars(msgs=dict(
    casatools='{package} is not available so interactive clean and plotants will not work',
    casatasks='{package} is not available so interactive clean will not work'
), reported={})
def warn_import(package):
    '''standard method for reporting (optional) package import failure

    Parameters
    ----------
    package: str
        name of a package whose attempted import failed
    '''
    if package not in warn_import.reported:
        warn_import.reported[package] = True
        error_msg("warning, %s" % warn_import.msgs[package].format(package=package))


@static_vars(url='http://clients3.google.com/generate_204')
def have_network():
    '''check to see if an active network with general internet connectivity
    is available. returns ``True`` if we have internet connectivity and
    ``False`` if we do not.
    '''
    ###
    ### see: https://stackoverflow.com/questions/50558000/test-internet-connection-for-python3
    ###
    try:
        with urllib.request.urlopen(have_network.url) as response:
            return response.status == 204
    except urllib.error.HTTPError:
        ### http error
        return False
    except urllib.error.URLError:
        return False
    except urllib.error.ContentTooShortError:
        return False
    except Exception:
        return False


def ranges(iterable, order=sorted, key=lambda x: x):
    '''collect elements of ``iterable`` into tuple ranges where each tuple represents
    a concesecutive range within the iterable. ``key`` can be used to provide ranges
    for other objects where ``key(element)`` returns the key to be used for sorting
    into ranges'''
    for a, b in groupby(enumerate(
            order(iterable, key=key) if 'key' in inspect.getfullargspec(order).kwonlyargs else order(iterable)),
                        lambda pair: key(pair[1]) - pair[0]):
        b = list(b)
        yield b[0][1], b[-1][1]


def contiguous_ranges(iterable, order=sorted, key=lambda x: x):
    '''split iterable into contiguous index sequence, i.e. reduce consecutive index runs
    to a tuple containing the first and last. ``iterable`` can be a sequence of values that
    can be subtracted or a list of more complex values where the function ``key`` returns
    the key to be used for ordering. ``iterable`` is ordered by ``order`` which by default
    sorts ``iterable``.'''
    unique = list(set(iterable))
    for a, b in groupby(
            enumerate(order(unique, key=key) if 'key' in inspect.getfullargspec(order).kwonlyargs else order(unique)),
            lambda pair: key(pair[1]) - pair[0]):
        b = list(b)
        yield b[0][1], b[-1][1]


def expand_range_incl(r):
    '''expand the tuple supplied as ``r`` into a range which *includes* the first
    and last element ``r``'''
    if r[0] == r[1]:
        return [0]
    else:
        return range(r[0], r[1] + 1)


def __get_wcs_object(csys: 'image.coordsys', naxis=2) -> 'image.coordsys()':
    """Generate world coordinate object from coordinate system.

    Returns:
        w: world coordinate object
    """
    try:
        import numpy as np
        from astropy.wcs import WCS

        w = WCS(naxis=naxis)

        rad_to_deg = 180/np.pi
        w.wcs.crpix = csys.referencepixel()['numeric'][0:2]
        w.wcs.cdelt = csys.increment()['numeric'][0:2]*rad_to_deg
        w.wcs.crval = csys.referencevalue()['numeric'][0:2] * rad_to_deg
        w.wcs.ctype = ['RA---SIN', 'DEC--SIN']

        return w

    except ImportError as error:
        print('Error importing module:: ' + str(error))

    except Exception as error:
        print(error)

def __index_to_stokes(index: int):
    """Convert stokes axis index to alphabetic value.

    Args:
        index (int): enumerated index defining stokes value.

    Returns:
        str: String indicating stokes value. 
    """
    STOKES_MAP = ['I', 'Q', 'U', 'V']
  
    try:
        return [STOKES_MAP[i] for i in index]
    except TypeError:
        return STOKES_MAP[index]

def index_to_stokes(index: int):
    """Convert stokes axis index to alphabetic value.

    Args:
        index (int): enumerated index defining stokes value.

    Returns:
        str: String indicating stokes value. 
    """
    STOKES_MAP = ['I', 'Q', 'U', 'V']
  
    try:
        return [STOKES_MAP[i] for i in index]
    except TypeError:
        return STOKES_MAP[index]

def __get_center_pixels(params: dict):
    """Get center pixel offset value from dictionary.

    Args:
        params (dict): Submask from mask grouping used by itertools

    Returns:
        list: Pixel offset defined in submask.
    """
    return params['d']

def __write_casa_region(region_object: 'astropy.region', coord:str, polygon_shape: str)->list:
    ''' Convert astropy region to casa region string. 

    Parameters
    ----------
    region_objects: astropy region
        Region definition in pixel or world coordinates
    coord: str
        Coordinate system that should be used in the returned masks. Allowed values are 'pixel', 'world'.
    polygon_shape: str
        Region shape definition: rect: centerbox/rotbox, poly:poly 

    '''
    
    meta_value = []
    for key, value in region_object.meta.items():
        if key == 'corr':
            meta_value.append('{key}=[{pol}]'.format(key=key, pol=value))
        elif key == 'range':
            meta_value.append('{key}=[{lower}chan, {upper}chan]'.format(key=key, lower=str(value[0]), upper=str(value[1])))
        else:
            print('Unknown key: {} skipping'.format(key))
        
    meta = ', '.join(meta_value)

    if polygon_shape=='rect':
        if coord=='pixel':
            return 'centerbox[[{x} pix, {y} pix], [{width} pix, {height} pix]], {meta}'.format(
                x=region_object.center.x,
                y=region_object.center.y,
                width=region_object.width,
                height=region_object.height,
                meta=meta
            )
  
        if coord=='world':
            return 'rotbox[[{ra}, {dec}], [{width}, {height}], {angle}], {meta}'.format(
                ra=region_object.center.ra,
                dec=region_object.center.dec,
                width=region_object.width,
                height=region_object.height,
                angle=region_object.angle,
                meta=meta
            )
  
        else:
            raise RuntimeError('Unknown coordinate value: {}'.format(coord))
  
    if polygon_shape=='poly':    
        if coord=='pixel':
            coords_array = []
            for value in region_object.vertices:
                coords_array.append('[{x} pix, {y} pix]'.format(x=value.x, y=value.y))

            coords = ', '.join(coords_array)

            return 'poly[{coords}], {meta}'.format(coords=coords, meta=meta)

        if coord=='world':
            coords_array = []
            for value in region_object.vertices:
                coords_array.append('[{ra}, {dec}]'.format(ra=value.ra, dec=value.dec))

            coords = ', '.join(coords_array)

            return 'poly[{coords}], {meta}'.format(coords=coords, meta=meta)
        else:
            raise RuntimeError('Unknown coordinate value: {}'.format(coord))
    else:
        raise RuntimeError('Unknown polygon shape: {}'.format(polygon_shape))

def convert_masks(masks: dict, coord='pixel', cdesc=None)->list:
    '''Convert masks in standard format (as defined by ``CubeMask.jsmask_to_raw``) into
    other formats like list of CRTF, single region, etc.

    Parameters
    ----------
    masks: dict
        Dictionary containing ``masks`` and ``polys`` keys. The values for ``masks`` are the polygon
        references for each channel and the values for ``polys`` contain the points making up each
        polygon.
    coord: str
        Coordinate system that should be used in the returned masks. Allowed values are 'pixel'.
    cdesc: dict
        Dictionary containing ``csys`` and ``shape`` which describes the coordinate system to be
        used for creating world coordinate coordinates. The ``shape`` is required along with the
        coordinate system for coordinate conversion.
    '''

    if cdesc is None or 'csys' not in cdesc or 'shape' not in cdesc:
        raise RuntimeError('region operations requires a coordinate description (cdesc parameter)')
    else:
        if not isinstance( cdesc['shape'], tuple ):
            raise RuntimeError("coordinate description must contain a 'shape' element of type 'tuple'")

        if isinstance( cdesc['csys'], dict ):
            csys = cdesc['csys']


    full_mask_params = []

    # Get the wcs object of the request format is world
    if coord == 'world':
        wcs = __get_wcs_object(cdesc['csys'])

    # Build list containing masks with channel and polaization information
    # in a more accesible way for the grouping funciton
    for index, mask in masks['masks'].items():
        for sub_mask in mask:
            sub_mask['s'], sub_mask['c'] = index
            full_mask_params.append(sub_mask)

    region_list = []

    # Group masks by unique center pixel and determine channel range. Extract 
    # mask properties and build astropy region for each center pixel and geometry
    # including region meta data.
    for key, props in itertools.groupby(full_mask_params, __get_center_pixels):
        channel_range = []
        for prop in props:
            channel_range.append(prop['c'])
            poly = prop['p']
            center_pixels = prop['d']
      
            mask_shape = masks['polys'][poly]['type']
      
            xs = masks['polys'][poly]['geometry']['xs']
            ys = masks['polys'][poly]['geometry']['ys']

            width = max(xs) - min(xs)
            height = max(ys) - min(ys)

            stokes_index = prop['s']
    
        if mask_shape=='rect':
            region = RectanglePixelRegion(
                PixCoord(x=center_pixels[0], y=center_pixels[1]), 
                width=width, height=height, angle=0*u.deg
        )
        elif mask_shape=='poly':
            region = PolygonPixelRegion(
                vertices=PixCoord(x=xs, y=ys)
        )

        else:
            raise RuntimeError('Invalid mask shape: {func}-->mask={mask}'.format(func=__convert_masks.__qualname__, mask=mask_shape))

        if coord=='world':
            region = region.to_sky(wcs)
            region.meta = {
                'corr': __index_to_stokes(stokes_index),
                'range': [min(channel_range), max(channel_range)]
            }

            region_list.append(__write_casa_region(region, coord=coord, polygon_shape=mask_shape))
        if coord=='pixel':

            region.meta = {
                'corr': __index_to_stokes(stokes_index),
                'range': [min(channel_range), max(channel_range)]
            }

            region_list.append(__write_casa_region(region, coord=coord, polygon_shape=mask_shape))

    return region_list

def __convert_masks(masks, format='crtf', coord='pixel', ret_type='str', cdesc=None):
    '''Convert masks in standard format (as defined by ``CubeMask.jsmask_to_raw``) into
    other formats like list of CRTF, single region, etc.

    Parameters
    ----------
    masks: dict
        Dictionary containing ``masks`` and ``polys`` keys. The values for ``masks`` are the polygon
        references for each channel and the values for ``polys`` contain the points making up each
        polygon.
    format: str
        Format string that indicates the format that should be returned. Allowed values are
        'region' or 'crtf'.
    coord: str
        Coordinate system that should be used in the returned masks. Allowed values are 'pixel'.
    ret_type: str
        Data structure that should be returned the allowed values are 'str', 'list', 'singleton'
    cdesc: dict
        Dictionary containing ``csys`` and ``shape`` which describes the coordinate system to be
        used for creating world coordinate coordinates. The ``shape`` is required along with the
        coordinate system for coordinate conversion.
    '''
    if format == 'region':
        if __have_casatools == False:
            raise RuntimeError('casatools is not available, cannot create CASA regions')
        if cdesc is None or 'csys' not in cdesc or 'shape' not in cdesc:
            raise RuntimeError('region operations requires a coordinate description (cdesc parameter)')
        else:
            if not isinstance(cdesc['shape'], tuple):
                raise RuntimeError("coordinate description must contain a 'shape' element of type 'tuple'")
            if isinstance(cdesc['csys'], dict):
                csys_dict = cdesc['csys']
            else:
                csys_dict = cdesc['csys'].torecord()

    unique_polygons = {}
    ###
    ### collect masks ordered by (poly_index,dx,dy)
    ###
    for index, mask in masks['masks'].items():
        for poly in mask:
            unique_poly = tuple([poly['p']] + poly['d'])
            if unique_poly in unique_polygons:
                unique_polygons[unique_poly] += [index]
            else:
                unique_polygons[unique_poly] = [index]

    polygon_definitions = {index: poly for index, poly in masks['polys'].items()}

    if format == 'region' and coord == 'pixel':
        rg = regionmanager()
        rg.setcoordinates(csys_dict)

        ###
        ### create a region list given the index of the polygon used, the x/y translation, and the
        ### channels the region should be found on
        ###
        def create_regions(poly_index, xlate, channels):
            def create_result(shape, points):
                return [rg.fromtext(
                    f"{shape}[{points}],range=[{chan_range[0]}chan,{chan_range[1]}chan],corr=[{','.join(index_to_stokes(expand_range_incl(stokes_range)))}]" ,
                    shape=list(cdesc['shape']))
                        for chan_range in contiguous_ranges([c[1] for c in channels]) for stokes_range in
                        contiguous_ranges([c[0] for c in channels])]

            if polygon_definitions[poly_index]['type'] == 'poly':
                poly_pts = ','.join([f"[{x + xlate[0]}pix,{y + xlate[1]}pix]"
                                     for x in polygon_definitions[poly_index]['geometry']['xs']
                                     for y in polygon_definitions[poly_index]['geometry']['ys']])
                return create_result('poly', poly_pts)
            if polygon_definitions[poly_index]['type'] == 'rect':
                xs = polygon_definitions[poly_index]['geometry']['xs']
                ys = polygon_definitions[poly_index]['geometry']['ys']
                box_pts = f"[{min(xs) + xlate[0]}pix,{min(ys) + xlate[1]}pix],[{max(xs) + xlate[0]}pix,{max(ys) + xlate[1]}pix]"
                return create_result('box', box_pts)

        ### flatten list of unique polygon regions
        result = list(chain.from_iterable(
            [create_regions(index[0], index[1:], channels) for index, channels in unique_polygons.items()]))
        if ret_type == 'singleton':
            if len(result) == 0:
                raise RuntimeError("no regions created")
            if len(result) == 1:
                return result[0]
            ###return dict(enumerate(result)))          ## see: CAS-13764
            return rg.makeunion(dict(map(lambda t: (str(t[0]), t[1]), list(enumerate(result)))))
        if ret_type == 'list':
            return result
        raise RuntimeError(f"unknown ret_type for region format ({ret_type})")

    if format == 'crtf' and coord == 'pixel':
        ###
        ### create a region list given the index of the polygon used, the x/y translation, and the
        ### channels the region should be found on
        ###
        def create_regions(poly_index, xlate, channels):
            def create_result(shape, points):
                return [
                    f"{shape}[{points}],range=[{chan_range[0]}chan,{chan_range[1]}chan],corr=[{','.join(index_to_stokes(expand_range_incl(stokes_range)))}]"
                    for chan_range in contiguous_ranges([c[1] for c in channels]) for stokes_range in
                    contiguous_ranges([c[0] for c in channels])]

            if polygon_definitions[poly_index]['type'] == 'poly':
                poly_pts = ','.join([f"[{x + xlate[0]}pix,{y + xlate[1]}pix]"
                                     for x in polygon_definitions[poly_index]['geometry']['xs']
                                     for y in polygon_definitions[poly_index]['geometry']['ys']])
                return create_result('poly', poly_pts)
            if polygon_definitions[poly_index]['type'] == 'rect':
                xs = polygon_definitions[poly_index]['geometry']['xs']
                ys = polygon_definitions[poly_index]['geometry']['ys']
                box_pts = f"[{min(xs) + xlate[0]}pix,{min(ys) + xlate[1]}pix],[{max(xs) + xlate[0]}pix,{max(ys) + xlate[1]}pix]"
                return create_result('box', box_pts)

        ###
        ### generate CFTF
        ###
        result = [create_regions(index[0], index[1:], channels) for index, channels in unique_polygons.items()]
        if ret_type == 'str':
            return '\n'.join(chain.from_iterable(result))
        if ret_type == 'list':
            return list(chain.from_iterable(result))
        raise RuntimeError(f"unknown ret_type for crtf format ({ret_type})")
    raise RuntimeError(f"invalid format ({format}), or coord ({coord})")


def set_attributes(obj, **kw):
    '''Given an object and a set of keyword arguments, set the attributes
    in the object that correspond to the keywords to the specified values.

    Parameters
    ----------
    obj: object
        Object whose attributes should be set
    kw: keyword and object
        Attributes to be set

    Returns
    -------
    object
        ``obj`` parameter
    '''
    for k, v in kw.items():
        setattr(obj, k, v)
    return obj
