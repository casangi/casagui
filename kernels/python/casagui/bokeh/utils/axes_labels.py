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
    import numpy as np
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
    from astropy.wcs import WCS
    rad_to_deg = 180/np.pi
    w = WCS(naxis=2)
    w.wcs.crpix = csys.referencepixel()['numeric'][0:2]
    w.wcs.cdelt = csys.increment()['numeric'][0:2]*rad_to_deg
    w.wcs.crval = csys.referencevalue()['numeric'][0:2]*rad_to_deg
    w.wcs.ctype = ['RA---SIN', 'DEC--SIN']
    x_axes_labels = {i: w.pixel_to_world(0, i).ra.to_string() for i in range(shp[0] + 1)}
    y_axes_labels = {i: w.pixel_to_world(i, 0).dec.to_string(decimal=True) for i in range(shp[0] + 1)}
    return x_axes_labels, y_axes_labels
