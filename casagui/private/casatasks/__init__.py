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
#        Internet email: casa-feedback@nrao.edu.
#        Postal address: AIPS++ Project Office
#                        National Radio Astronomy Observatory
#                        520 Edgemont Road
#                        Charlottesville, VA 22903-2475 USA
#
########################################################################
'''casatasks provides on-the-fly creation of inp/go wrappers for tasks
https://bayesianbrad.github.io/posts/2017_loader-finder-python.html
'''

from importlib.abc import Loader as _Loader, MetaPathFinder as _MetaPathFinder

import subprocess
import re
import os
import sys

class CasaTasks_Loader(_Loader):

    def __init__( self, java, jarpath, args, templ, xml ):
        self.__java = java
        self.__jarpath = jarpath
        self.__args = args
        self.__templ = templ
        self.__xml = xml

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        python_source = subprocess.run( [ self.__java, '-jar', self.__jarpath ] + self.__args + [self.__templ, self.__xml], stdout=subprocess.PIPE ).stdout.decode('utf-8')
        exec( python_source, module.__dict__ )


class CasaTasks_Finder(_MetaPathFinder):

    def __init__( self ):
        super(CasaTasks_Finder, self).__init__( )
        self.__java = None
        self.__source_dir = os.path.dirname(__file__)
        self.__jarpath = None
        self.__jarfile_name = "xml-casa-assembly-1.86.jar"
        self.__task_xml_files = None

    def __which( self, program ):
        def is_exe(fpath):
            return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

        fpath, fname = os.path.split(program)
        if fpath:
            if is_exe(program):
                return os.path.realpath(program)
        else:
            os.environ.get("PATH", "")
            for path in os.environ.get("PATH", "").split(os.pathsep):
                exe_file = os.path.join(path, program)
                if is_exe(exe_file):
                    return os.path.realpath(exe_file)
        return None

    def __find_parameters( self, taskname ):
        templ = os.path.join( self.__source_dir, f'''{taskname}.mustache''' )
        if os.path.isfile(templ):
            ### <TASK>.mustache exists -------------------------------------------------------------------------------------------------------------
            with open(templ) as f:
                header = [ (m.group(1), m.group(2), m.group(0)) for m in [ re.match( "^\#+\s*TASK XML\s*>\s*(\S+)(.*)", next(f) ) for _ in range(5) ] if m ]
                if len(header) == 1:
                    ### <TASK>.mustache has processing specification line --------------------------------------------------------------------------
                    task = os.path.splitext(header[0][0])[0]
                    if task in self.__task_xml_files:
                        ### <TASK>.mustache has processing specification line and includes valid CASA task name ------------------------------------
                        return templ, self.__task_xml_files[task], header[0][1].split( )
                    elif taskname in self.__task_xml_files:
                        ### <TASK>.mustache has processing specification line and <TASK> is a valid CASA task --------------------------------------
                        return templ, self.__task_xml_files[taskname], header[0][1].split( )
                elif taskname in self.__task_xml_files:
                    ### <TASK>.mustache does not have a processing specification line but <TASK> is a valid CASA task-------------------------------
                    return templ, self.__task_xml_files[taskname], [ ]

        if taskname in self.__task_xml_files:
            ### <TASK>.mustache does not exist but <TASK> is a valid CASA task ---------------------------------------------------------------------
            templ = os.path.join( self.__source_dir, f'''generic.mustache''' )
            if os.path.isfile(templ):
                ### <TASK> is a valid CASA task and generic.mustache exists ------------------------------------------------------------------------
                with open(templ) as f:
                    header = [ (m.group(1), m.group(2), m.group(0)) for m in [ re.match( "^\#+\s*TASK XML\s*>\s*(\S+)(.*)", next(f) ) for _ in range(5) ] if m ]
                    if len(header) == 1:
                        ### <TASK> is a valid CASA task, generic.mustache exists and has a processing specification line ---------------------------
                        return templ, self.__task_xml_files[taskname], header[0][1].split( )
                    else:
                        ### <TASK> is a valid CASA task, generic.mustache exists but does not have a processing specification line -----------------
                        return templ, self.__task_xml_files[taskname], [ ]

        return None, None, [ ]

    def find_spec(self, fullname, path, target = None):

        if fullname.startswith('casagui.private.casatasks.'):
            if self.__java is None:
                self.__java = self.__which( "java" )
            if self.__jarpath is None:
                p = os.path.join( os.path.dirname(os.path.dirname(__file__)), "__java__", self.__jarfile_name )
                if os.path.isfile(p):
                    self.__jarpath = p
            if self.__task_xml_files is None:
                try:
                    from casatasks import xml_interface_defs
                    self.__task_xml_files = { k:v for (k,v) in xml_interface_defs( ).items( ) if os.path.isfile(v) }
                except: pass

            module = fullname.split(sep='.')[-1]
            templ, xml, args = self.__find_parameters( fullname.split(sep='.')[-1] )
            if templ is not None and xml is not None:
                from importlib.machinery import ModuleSpec
                return ModuleSpec( fullname, CasaTasks_Loader( self.__java, self.__jarpath, args, templ, xml ) )

        return None

sys.meta_path.append(CasaTasks_Finder( ))
