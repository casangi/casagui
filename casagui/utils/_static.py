########################################################################
#
# Copyright (C) 2021,2023
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
'''Contains functions for attaching static value as attributes of functions'''

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

