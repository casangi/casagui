
Rules for casagui Development
=============================

1. **AppContext** each :code:`casagui` application will create an :code:`AppContext` object. Creating this object initializes the :code:`casagui` Bokeh libraries, sets the title for the browser tab and creates a work directory for the application.

Creating a Conda Environment
============================

This is an example of how to create an Anaconda environment for doing :code:`casagui` development::

  :code:`bash$ conda create -n 'bokeh-32' python=3.10 ipython websockets bokeh=3.2 regions scipy --channel=conda-forge`
