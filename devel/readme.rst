
Rules for casagui Development
=============================

**AppContext**: each :code:`casagui` application will create an :code:`AppContext` object. Creating this object initializes the :code:`casagui` Bokeh libraries, sets the title for the browser tab, and creates a work directory for the application.

Creating a Conda Environment
============================

This is an example of how to create an Anaconda environment for doing :code:`casagui` development::

  bash$ conda create -n 'bokeh-32' python=3.10 ipython websockets bokeh=3.2 regions scipy --channel=conda-forge
