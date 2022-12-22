
from itertools import product
from matplotlib.path import Path
from math import floor,ceil

def polygon_indexes( xs, ys, shape ):
    '''
    Returns indexes for a 2D array of the given ``shape`` which
    lie within the polygon specified by ``xs`` and ``ys``.

    Parameters
    ----------
    xs: list of numbers
        the X coordinates for the vertices of the polygon
    ys: list of numbers
        the Y coordinates for the vertices of the polygon
    shape: ( int, int )
        the shape of the plane in which the polygon is found

    Returns
    -------
    generator of tuples:
        the stream of tuples that is returned will be the indexes
        of the elements which lie within the polygon
    '''
    assert len(shape) == 2, 'contains only works for 2D shapes, so "shape" should have length equal to two'
    assert len(xs) == len(ys), 'to specify a polygon the number of X values must equal the number of Y values'

    if len(xs) == 4 and len(ys) == 4 :
        uniqx = sorted(set(xs))
        uniqy = sorted(set(ys))
        if len(uniqx) == 2 and len(uniqy) == 2:
            ### we have a proper box, the Path.contains_point implementation seems to
            ### err slightly with very small regions...
            return product(range(floor(uniqx[0]),ceil(uniqx[1])),range(floor(uniqy[0]),ceil(uniqy[1])))

    path = Path(list(zip(xs,ys)))
    xmin, xmax = max([0,min(xs)-1]), max(xs)+1
    ymin, ymax = max([0,min(ys)-1]), max(ys)+1
    return filter( path.contains_point, product(range(floor(xmin),ceil(xmax)), range(floor(ymin),ceil(ymax))) )
