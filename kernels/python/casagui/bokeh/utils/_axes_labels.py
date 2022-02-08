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
'''Functions for coordinate conversion and axis labeling.'''
import numpy as np
from astropy.wcs import WCS
from casatools import image


def get_world_coordinates(ia):
    """
    .. todo::
        Support different world coordiantes
        Provide prettier string formatting

    Get the mapping between pixel coordinates and world coordinates using casatools.coordsys

    Parameters
    -------
    ia: casatools.image

    Returns
    -------
    x_axes_labels, y_axes_labels : (dict, dict)
        Dictionary mapping pixel coordinates to world coordinates
    """
    pix = np.zeros([len(ia.shape()), ia.shape()[0]])
    pix[0, :] = range(ia.shape()[0])
    csys = ia.coordsys()
    world = csys.toworldmany(pix)['numeric']
    x_axes_labels = {i: str(world[0][i]) for i in range(ia.shape()[0])}
    y_axes_labels = {i: str(world[1][i]) for i in range(ia.shape()[0])}
    return x_axes_labels, y_axes_labels


def get_world_coordinates_wcs(csys: image.coordsys) -> list():
    """
    .. todo::
        Support different world coordiantes
        Provide prettier string formatting

    Get the mapping between pixel coordinates and world coordinates using astropy.wcs.WCS

    Parameters
    -------
    csys: casatools.coordsys

    Returns
    -------
    x_axes_labels, y_axes_labels : (dict, dict)
        Dictionary mapping pixel coordinates to world coordinates
    """
    rad_to_deg = 180/np.pi
    w = WCS(naxis=2)
    w.wcs.crpix = csys.referencepixel()['numeric'][0:2]
    w.wcs.cdelt = csys.increment()['numeric'][0:2]*rad_to_deg
    w.wcs.crval = csys.referencevalue()['numeric'][0:2]*rad_to_deg
    w.wcs.ctype = ['RA---SIN', 'DEC--SIN']
    x_axes_labels = {i: w.pixel_to_world(0, i).ra.to_string() for i in range(shp[0] + 1)}
    y_axes_labels = {i: w.pixel_to_world(i, 0).dec.to_string(decimal=True) for i in range(shp[0] + 1)}
    return x_axes_labels, y_axes_labels
