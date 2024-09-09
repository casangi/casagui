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
#        Internet email: casa-feedback@nrao.edu.
#        Postal address: AIPS++ Project Office
#                        National Radio Astronomy Observatory
#                        520 Edgemont Road
#                        Charlottesville, VA 22903-2475 USA
#
########################################################################
'''tiling utilities'''

from math import ceil, log

class TMSTiles(object):
    ###
    ### This class is based upon https://github.com/OSGeo/gdal/blob/master/swig/python/gdal-utils/osgeo_utils/gdal2tiles.py
    ### written by:       Klokan Petr Pridal (klokan at klokan dot cz)
    ###                   Even Rouault (even dot rouault at spatialys.com)
    ###                   Idan Miara (idan@miara.com)
    ### It is a small subset of the original source code, and it is highly modified to only
    ### handle raster profile tiling. The original source code has many useful details and
    ### supports mercator and geodetic data. The subset of gdal2tiles.py used here is less
    ### than 3% of the original file (42 lines out of 1697). While this is not considered
    ### a substantial portion, it was invaluable for understanding the TMS tile layout.
    ###
    def __init__( self, dimension, title='' ):
        '''
        Construct a tiling object which will provide the coordinates of tiles, the size to
        be read, the size of the scaled tile and the write offset within the :code:`tile_size`
        output tile.

        Parameters
        ----------
        dimension: list or tuple
            should contain at least two elements (X,Y)
        '''

        def calculate_indexes( tz, result={ } ):

            ti = 0
            tile_details = []
            tminx, tminy, tmaxx, tmaxy = self.tminmax[tz]

            for ty in range(tmaxy, tminy - 1, -1):
                for tx in range(tminx, tmaxx + 1):
                    ti += 1
                    ytile = ty
                    index = ( tz, tx, ty )

                    tsize = int(self.tsize[tz])   # tile_size in raster coordinates for actual zoom
                    xsize = self.__dimension[0]
                    ysize = self.__dimension[1]
                    querysize = self.__tile_size

                    rx = tx * tsize
                    rxsize = 0
                    if tx == tmaxx:
                        rxsize = xsize % tsize
                    if rxsize == 0:
                        rxsize = tsize

                    ry = ty * tsize
                    rysize = 0
                    if ty == tmaxy:
                        rysize = ysize % tsize
                    if rysize == 0:
                        rysize = tsize

                    wx, wy = 0, 0
                    wxsize = int(rxsize / float(tsize) * self.__tile_size)
                    wysize = int(rysize / float(tsize) * self.__tile_size)

                    ry = ysize - (ty * tsize) - rysize
                    if wysize != self.__tile_size:
                        wy = self.__tile_size - wysize

                    result[index] = dict( src=dict( idx=(rx, ry), dim=(rxsize, rysize),
                                                    t=(( 0, 0 if rysize == tsize else tsize - rysize ), tsize ) ),
                                          dst=dict( idx=(wx, wy), dim=(wxsize, wysize) ) )
            return result

        self.__title = title
        self.__tile_size = 256
        self.__dimension = dimension
        self.__zoom = (0, max( 0, int( max( ceil(log(dimension[0] / float(self.__tile_size), 2 )),
                                            ceil( log(dimension[1] / float(self.__tile_size), 2 )) ) ) ) )
        native_zoom = self.__zoom[1]

        # Generate table with min max tile coordinates for all zoomlevels
        self.tminmax = list(range(self.__zoom[0], self.__zoom[1] + 1))
        self.tsize = list(range(self.__zoom[0], self.__zoom[1] + 1))
        for tz in range(self.__zoom[0], self.__zoom[1] + 1):
            tsize = 2.0**(native_zoom - tz) * self.__tile_size
            tminx, tminy = 0, 0
            tmaxx = int(ceil(dimension[0] / tsize)) - 1
            tmaxy = int(ceil(dimension[1] / tsize)) - 1
            self.tsize[tz] = ceil(tsize)
            self.tminmax[tz] = (tminx, tminy, tmaxx, tmaxy)

        self.__units_per_pixel = { }
        for z in range(self.__zoom[0], self.__zoom[1] + 1):
            self.__units_per_pixel[z] = 2**(self.__zoom[1] - z)

        self.__tile_details = { }
        for z in range(self.__zoom[0], self.__zoom[1] + 1):
            calculate_indexes( z, self.__tile_details )

    def profile( self ):
        return "raster"

    def dim( self ):
        return self.__dimension

    def tile_size( self ):
        return self.__tile_size

    def tile( self, z, x=None, y=None ):
        try:
            if (type(z) == tuple or type(z) == list) and len(z) == 3 and x is None and y is None:
                return self.__tile_details[ (int(z[0]),int(z[1]),int(z[2])) ]
            elif type(x) is not None and type(y) is not None:
                return self.__tile_details[ (int(z),int(x),int(y)) ]
            else:
                raise RuntimeError( 'tile requires 3 integer parameters or 1 tuple[3] parameter' )
        except KeyError:
            return None

    def zoom_levels( self, reverse=False ):
        return sorted( list(self.__units_per_pixel.keys( )), reverse=reverse )

    def units_per_pixel( self, zoom_level ):
        if zoom_level not in self.__units_per_pixel:
            raise RuntimeError(f'''{zoom_level} is not an existing zoom level''')
        return self.__units_per_pixel[zoom_level]

    def __str__( self ):
        return f'''<?xml version="1.0" encoding="utf-8"?>
    <TileMap version="1.0.0" tilemapservice="http://tms.osgeo.org/1.0.0">
      <Title>{self.__title}</Title>
      <Abstract></Abstract>
      <SRS></SRS>
      <BoundingBox minx="0.0000" miny="0.0000" maxx="{self.__dimension[0]}.0000" maxy="{self.__dimension[1]}.0000"/>
      <Origin x="0.0000" y="0.0000"/>
      <TileFormat width="256" height="256" mime-type="image/png" extension="png"/>
      <TileSets profile="raster">''' + "\n" + '\n'.join( map( lambda z: f'''        <TileSet href="{z}" units-per-pixel="{self.units_per_pixel(z)}.0000" order="{z}"/>''',
                                                              self.zoom_levels( ) ) ) + f'''
      </TileSets>
    </TileMap>
'''
