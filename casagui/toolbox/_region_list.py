########################################################################
#
# Copyright (C) 2025
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
import hashlib
from astropy.wcs import WCS
from regions import PixCoord, PolygonPixelRegion

class _Line:

    def __init__( self, style ):
        if not ( 'color' in style and 'width' in style and 'alpha' in style and 'dash' in style ):
            raise RuntimeError( 'style must contain color, width, alpha and dash' )
        self.__style = style

    def color( self ):
        return self.__style['color']

    def width( self ):
        return self.__style['width']

    def alpha( self ):
        return self.__style['alpha']

    def dash( self ):
        return self.__style['dash']

class _Fill:

    def __init__( self, fill ):
        if not ( 'color' in fill and 'alpha' in fill and 'hatch' in fill ):
            raise  RuntimeError( 'fill must contain color, alpha and hatch' )
        self.__fill = fill

    def color( self ):
        return self.__fill['color']

    def alpha( self ):
        return self.__fill['alpha']

    def hatch( self ):
        return self.__fill['hatch']

class Region:

    ### reuse astropy WCS objects based upon fits header strings
    ### to avoid reparsing
    wcs_cache = { }

    def __init__( self, name, xs, ys, channels, line, fill, wcs=None ):
        if type(name) != str:
            raise RuntimeError( 'region names are strings' )
        if len(xs) != len(ys):
            raise RuntimeError( 'X and Y values must be of equal length' )

        self.__ste = { }
        self.__ste['name'] = name
        self.__ste['xs'] = xs
        self.__ste['ys'] = ys
        self.__ste['chan'] = channels
        self.__ste['line'] = line
        self.__ste['fill'] = fill
        self.__ste['wcs'] = None
        if wcs is not None:
            if isinstance(wcs,WCS):
                self.__ste['wcs'] = wcs
            elif type(wcs) == str:
                ## Assume wcs is a FITS header
                hash = hashlib.md5(wcs.encode()).hexdigest()
                if hash not in Region.wcs_cache:
                    Region.wcs_cache[hash] = WCS( header=wcs )
                self.__ste['wcs'] = Region.wcs_cache[hash]
            else:
                raise RuntimeError( f'''Regions initialized with non-FITS header representations of the WCS of type {type(wcs)} are not supported''' )

    def __str__(self):
        return self.__repr__( )

    def __repr__(self):
         return f'''<{self.__class__.__name__}({self.__ste['name']}) @ {hex(id(self))}>'''

    def name( self ):
        return self.__ste['name']

    def xs( self ):
        return self.__ste['xs']

    def ys( self ):
        return self.__ste['ys']

    def vertices( self ):
        return zip( self.__ste['xs'], self.__ste['ys'] )

    def channels( self ):
        return self.__ste['chan']

    def line( self ):
        return _Line( self.__ste['line'] )

    def fill( self ):
        return _Fill( self.__ste['fill'] )

    def to_astropy_pixel( self ):
        ### It seems as though there is no way to create 4 dimensional pixel coordinates (RA,DEC,STOKES,CHAN)
        ### using astropy.
        return PolygonPixelRegion( vertices=PixCoord( self.__ste['xs'], self.__ste['ys'],
                                                      ### meta and visual are not available on regions v0.10 which
                                                      ### seems to be the most recent version available with pip
                                                      #meta={ 'name': self.__ste['name'] },
                                                      #visual={ 'dash': self.__ste['line']['dash'],
                                                      #         'linewidth': self.__ste['line']['width'] }
                                                     ) )
                                                             

    def to_astropy_sky( self, wcs=None ):
        if wcs is None:
            wcs = self.__ste['wcs']
        if wcs is None:
            raise RuntimeError( 'No world coordinate system is available' )
        ### Astropy coordinates seem to be limited to two dimensions so the generalized
        ### WCS object (potentially with stokes and frequency axes) must be converted to
        ### a two coordinate description.
        return self.to_astropy_pixel( ).to_sky( wcs.sub([1,2]) )

class _Iter:
    def __init__( self, ste ):
        self.__ste = ste

    def __iter__(self):
        for name, rgn in self.__ste['raw'].items( ):
            yield ( name, Region( name, rgn['geometry']['xs'], rgn['geometry']['ys'],
                                    rgn['channels'], rgn['styling']['line'],
                                    rgn['styling']['fill'], wcs=self.__ste['wcs'] ) )

class RegionList:
    '''This class is for representing regions within casagui applications. Currently it only wowrks with the
    `createregion` app. It is not (currently) designed as an end user class but rather as an output class for
    the user.

    Currently it only accepts a dictionary like for `regiondict`:
    ```
    {'rg0': {'channels': [[0, 0]], 'geometry': {'xs': [33.51816859449925, 31.611101128190022, 121.40193309213468], 'ys': [195.13666993774888, 232.39613665715922, 229.12483086356568]}, 'styling': {'line': {'color': '#ffffff', 'width': 1, 'alpha': 1, 'dash': 'solid'}, 'fill': {'color': '#ffffff', 'alpha': 0, 'hatch': 'blank'}}}, 'rg1': {'channels': [[0, 0]], 'geometry': {'xs': [289.43821781788444, 347.2289277115166, 351.7707259199244], 'ys': [236.68983013019135, 232.27134277978703, 186.01834737432947]}, 'styling': {'line': {'color': '#ffffff', 'width': 1, 'alpha': 1, 'dash': 'solid'}, 'fill': {'color': '#ffffff', 'alpha': 0, 'hatch': 'blank'}}}, 'rg2': {'channels': [[0, 0]], 'geometry': {'xs': [346.576046788646, 334.82618711394673, 270.71434943666696], 'ys': [61.16382772497764, 9.769953019597281, 16.587407740876944]}, 'styling': {'line': {'color': '#ffffff', 'width': 1, 'alpha': 1, 'dash': 'solid'}, 'fill': {'color': '#ffffff', 'alpha': 0, 'hatch': 'blank'}}}, 'rg3': {'channels': [[0, 0]], 'geometry': {'xs': [17.33383873194185, 20.60032838342714, 105.68674392600984], 'ys': [65.03236450671528, 26.158256778791444, 15.71542171880079]}, 'styling': {'line': {'color': '#ffffff', 'width': 1, 'alpha': 1, 'dash': 'solid'}, 'fill': {'color': '#ffffff', 'alpha': 0, 'hatch': 'blank'}}}, 'rg4': {'channels': [[0, 0]], 'geometry': {'xs': [194.1150775408404, 186.7420925740613, 247.32924839610087, 257.7778686999655, 220.3835500015239], 'ys': [100.28458653562863, 138.0450054510982, 136.91400495710235, 109.48993737427867, 75.12723329938433]}, 'styling': {'line': {'color': '#ffffff', 'width': 1, 'alpha': 1, 'dash': 'solid'}, 'fill': {'color': '#ffffff', 'alpha': 0, 'hatch': 'blank'}}}}
    ```
    The `wcs` parameter could either be a string representation of a FITS wcs header or it could be an
    astropy `WCS` object.
    '''

    def __init__( self, regiondict, wcs ):

        self.__ste = { 'wcs': wcs }
        self.__summary_size = 22

        if type(regiondict) != dict:
            raise RuntimeError( 'RegionList must be initialized with a dictionary representation of regions' )
        self.__ste['raw'] = regiondict

    def __iter__(self):
        return _Iter(self.__ste).__iter__( )

    def __str__(self):
        return self.__repr__( )

    def __repr__(self):
        added = 0
        names = ''
        keys = self.__ste['raw'].keys( )
        for name in keys:
            if len(names) + len(names) > self.__summary_size: break
            names = names + (',' if len(names) > 0 else '') + name
            added = added + 1
        if added < len(keys):
            names = f'''{names}...'''
        return f'''<{self.__class__.__name__}[{names}] @ {hex(id(self))}>'''
    
