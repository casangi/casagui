########################################################################
#
# Copyright (C) 2024
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
from casagui.bokeh.state import initialize_bokeh
from tempfile import TemporaryDirectory
from bokeh.io import output_file
from bokeh.plotting import curdoc
from os.path import join
import unicodedata
import re

class AppContext:

    def _slugify(self, value, allow_unicode=False):
        """
        Taken from https://github.com/django/django/blob/master/django/utils/text.py
        Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
        dashes to single dashes. Remove characters that aren't alphanumerics,
        underscores, or hyphens. Convert to lowercase. Also strip leading and
        trailing whitespace, dashes, and underscores.
        https://stackoverflow.com/a/295466/2903943
        """
        value = str(value)
        if allow_unicode:
            value = unicodedata.normalize('NFKC', value)
        else:
            value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
        value = re.sub(r'[^\w\s-]', '', value.lower())
        return re.sub(r'[-\s]+', '-', value).strip('-_')

    def __init__( self, title, prefix=None, theme=None ):

        ###
        ### Setup up Bokeh paths, inject casagui libraries into Bokeh HTML output
        ###
        initialize_bokeh( )

        if prefix is None:
            ## create a prefix from the title
            prefix = self._slugify(title)[:10]

        if type(theme) is str:
            if theme.startswith('dark'):
                curdoc( ).theme = 'dark_minimal'
            elif theme.startswith('caliber'):
                curdoc().theme = 'caliber'
            elif theme.startswith('light'):
                curdoc().theme = 'light_minimal'
            elif theme.startswith('night'):
                curdoc().theme = 'night_sky'
            elif theme.startswith('contrast'):
                curdoc().theme = 'contrast'
            else:
                raise RuntimeError(f'''Unknown theme: '{theme}' ''')

        self.__workdir = TemporaryDirectory(prefix=prefix)
        self.__htmlpath = join( self.__workdir.name, f'''{self._slugify(title)}.html''' )
        output_file( self.__htmlpath, title=title )

    def __del__( self ):
        ### remove work directory and its contents
        self.__workdir.cleanup( )

    def workdir( self ):
        return self.__workdir.name
