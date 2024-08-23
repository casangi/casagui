# Copyright (C) 2021
# Associated Universities, Inc. Washington DC, USA.
#
# This library is free software; you can redistribute it and/or modify it
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
# Correspondence concerning AIPS++ should be addressed as follows:
#        Internet email: casa-feedback@nrao.edu.
#        Postal address: AIPS++ Project Office
#                        National Radio Astronomy Observatory
#                        520 Edgemont Road
#                        Charlottesville, VA 22903-2475 USA
import re
from os.path import join, abspath, dirname, exists
from os import system
import setuptools

name = 'casagui'
version = None
long_description = None
root = dirname(abspath(__file__))

keywords = """
CASA
common astronomy software applications
scientific computing
bokeh
visualization
jupyter
"""

with open(join(root,name,"resources.py"), "r", encoding='utf-8') as fh:
    for line in fh:
        if line.startswith('version'):
            version = re.match('.*?(\d+\.\d+\.\d+).*',line).group(1)

with open(join(root,name,"README.md"), 'r', encoding='utf-8') as fh:
    long_description = fh.read( )

setuptools.setup(
    name=name,
    version=version,
    author="CASA development team",
    author_email="casa-feedback@nrao.edu",
    description="CASA visualization framework",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://casagui.readthedocs.io/",
    download_url="https://github.com/casangi/casagui",
    license="GNU Library or Lesser General Public License (LGPL)",
    classifiers=[ 'Programming Language :: Python :: 3' ],
    keywords=keywords,
    packages=[ 'casagui', 'casagui.bokeh', 'casagui.bokeh.utils',
               'casagui.bokeh.sources', 'casagui.proc',
               'casagui.bokeh.components',
               'casagui.bokeh.components.button',
               'casagui.bokeh.components.button_group',
               'casagui.bokeh.components.custom_icon',
               'casagui.bokeh.components.slider' ],
    package_dir = { '': '.' },
    python_requires=">=3.7",
    package_data={ 'casagui': [ 'bokeh/components/slider/iclean_slider.ts',
                                'bokeh/components/custom_icon/svg_icon.ts',
                                'bokeh/components/custom_icon/CustomIcon.ts',
                                'bokeh/components/button/iclean_button.ts',
                                'bokeh/components/button_group/button_group.ts',
                                'README.md', 'LICENSE' ] },
    install_requires=['bokeh == 2.4.1', 'websockets >= 10.0', 'casatasks == 6.4.3.4a6692.dev3']
)
