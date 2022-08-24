casagui - visualization tools and applications for CASA
=======================================================

This is a **pre-alpha**, **prototype** package. It is *not* useful for external users, and all
applications being built with it are currently in various phases of *prototyping*.

Introduction
------------

For some time, the GUIs provided by `CASA <https://casadocs.readthedocs.io/en/latest/>`_ have
been based upon `Qt <https://www.qt.io/>`_. While Qt works well, the compiled nature of C++
code made building and distributing the GUIs for each architecture a hurdle. This in turn
caused the GUIs we developed to tend toward large, monolithic applications which were
difficult to integrate and control from Python. We first used
`DBus <https://www.freedesktop.org/wiki/Software/dbus/>`_ to control our Qt application.
Qt provides a nice interface to DBus, but it became clear that DBus development had slowed
and that DBus was unlikely to make major inroads outside of the Linux Desktop. At that
point, we switched to `gRPC <https://grpc.io/>`_. gRPC supports a variety of platforms
and languages. It also has significant support behind it. However despite the improved
technology, it was still difficult to incorporate a scripting interface which allowed a
stand-alone C++/Qt process to be controlled by a separate Python process at a low enough
level to be practically useful for control at the level of granularity we desire.

Similar to the CASA visualization development experience, the CASA framework as a whole
has experienced the ups and downs of the large C++ development experience. Experience
with a Python parallelization trade study which CASA conducted indicated that the loss
of CPU throughput in a switch from C++ to pure Python can be made up for in gains made
in the selection of parallelization framework like `Dask <https://www.dask.org/>`_ along
with just in time compilation with something like `Numba <http://numba.pydata.org/>`_.
In addition to the focus of the trade study, additional gains are possible by mixing
in GPU resources.

These experiences have led CASA to begin a multi-year transition from being a large
C++ framework attached to Python to being a pure-Python framework for processing
radio astronomy data. This package is visualization portion of that transition.

After an abbreviated trade study where we considered a few pure-Python visualization
frameworks, we selected `Bokeh <https://docs.bokeh.org/en/latest/>`_ as the basis
for creating new visualization infrastructure for CASA. The choice of Bokeh was made
based upon its extensibility, its community support (including
`NumFocus <https://numfocus.org/project/bokeh>`_), and its limited external dependencies
(just JavaScript and a modern web browser). A stand-alone application can be created
by using the
`Bokeh server <https://docs.bokeh.org/en/latest/docs/reference/command/subcommands/serve.html>`_.
These options allow for GUIs to be created and used interactively from a Python
command line session, as a stand-alone mini web server, integrated into a desktop
application (using `Electron <https://www.electronjs.org/>`_) or as part of a
`Jupyter Notebook <https://jupyter.org/>`_.

Beyond this architectural flexibility, our intention is to create a toolbox of
Bokeh based components which can be combined to create a collection of visualization
tools which can be used in each of these settings (Python command line, Notebook
and desktop application) so that we maintain smaller, reusable tools instead of very
large monolithic applications. *Interactive clean* is our path-finder application of
this approach and is currently the only example available.

Installation
------------

casagui is available `from PyPI <https://pypi.org/project/casagui/>`_.

Requirements
````````````

- Python 3.8 or greater

- casatools and casatasks built from `CAS-13743 <https://open-jira.nrao.edu/browse/CAS-13743>`_

Install
```````

- :code:`bash$ casa-CAS-13743-2-py3.8/bin/pip3 install casagui`

Caveats
```````

- Remote access is slow, later a desktop application will be developed (using the same Bokeh
  toolbox) to improve this situation, but for now if running remotely, it is best to pre-start
  your preferred browser on the host where you will be running interactive clean. For example

  * :code:`bash$ export BROWSER=/opt/local/bin/firefox`

  * :code:`bash$ $BROWSER > /dev/null 2>&1 &`

- `Konqueror <https://apps.kde.org/konqueror/>`_ does **not** work. We only test with
  `Chrome <https://www.google.com/chrome/>`_ and
  `Firefox <https://www.mozilla.org/en-US/firefox/new/>`_.

- :code:`node.js` version 14.0.0 or higher is required

Simple Usage Example
--------------------

A simple example of the use of interactive clean is::

  CASA <1>: from casagui.apps import InteractiveClean
  CASA <2>: InteractiveClean( vis=ms_path, imagename=img, imsize=512, cell='12.0arcsec',
                    specmode='cube', interpolation='nearest', nchan=5, start='1.0GHz',
                    width='0.2GHz', pblimit=-1e-05, deconvolver='hogbom', threshold='0.001Jy',
                    niter=50, cycleniter=10, cyclefactor=3, scales=[0,3,10] )( )


In general, the :code:`InteractiveClean` constructor takes a subset of parameters accepted
by `tclean <https://casadocs.readthedocs.io/en/latest/api/tt/casatasks.imaging.tclean.html>`_.
All of the masks used in running interactive clean are available from the
:code:`InteractiveClean` object. To get access to the list of masks, you would create
the object as a separate statement::

  CASA <2>: ic = InteractiveClean( vis=ms_path, imagename=img, imsize=512, cell='12.0arcsec',
                    specmode='cube', interpolation='nearest', nchan=5, start='1.0GHz',
                    width='0.2GHz', pblimit=-1e-05, deconvolver='hogbom', threshold='0.001Jy',
                    niter=50, cycleniter=10, cyclefactor=3, scales=[0,3,10] )( )
  CASA <2>: ic( )
  CASA <3>: print(ic.masks( ))

