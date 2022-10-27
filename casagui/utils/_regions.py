
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
    path = Path(list(zip(xs,ys)))
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    return filter( path.contains_point, product(range(floor(xmin),ceil(xmax)), range(floor(ymin),ceil(ymax))) )
