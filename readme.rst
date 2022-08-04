casagui - visualization tools and applications for CASA
=======================================================

This is a **pre-alpha** package. It is *not* useful for external users, and all
applications being built with it are currently in various phases of *prototyping*.


Worse, this documentation is out of date and needs updating. It is focused on the
installation of :code:`casagui` as a desktop app while development has moved toward
first supporting scripting and visualization from Python using
`Bokeh <https://docs.bokeh.org/en/latest/>`_. It will be updated as testing and
stakeholder input are used to shape the interactive clean application.

Installation
------------

Developers can build and run casagui with::

  bash$ git clone https://github.com/casangi/casagui.git
  bash$ cd casagui
  bash$ npm install
  bash$ pushd node_modules/zeromq
  bash$ HOME=~/.electron-gyp ../.bin/node-gyp rebuild --target=12.0.2 --arch=x64 --dist-url=https://electronjs.org/headers
  bash$ popd
  bash$ npm start

A few standard :code:`npm` packages (:code:`enchannel-zmq-backend`, :code:`jmp`, :code:`jupyter-paths`, :code:`kernelspecs`, and :code:`spawnteract`) are included directly instead of through installed packages to allow for upgrading to the latest :code:`zeromq.js` distribution in the future.

Currently, it is assumed that you have a working `python3` interpreter in your path that has the `ipykernel` package installed. This package can be installed with::

  bash$ python -m pip install ipykernel
  bash$ python -m ipykernel install --user

You can check to make sure the Jupyter kernel is available with::

  bash$ python3 -m ipykernel_launcher --help

Any Python packages you want to use must be installed too. In particular::

  bash$ pip install plotly==4.14.3

Finally, a good way to test your kernel is by installing the `Interact desktop app <https://nteract.io/>`_. Some experimentation may be required. This was the case with installing Python with `macports <https://www.macports.org/>`_ and then getting the `nteract desktop app <https://nteract.io/>`_ to use Python from there.

Development Notes
------------------

1. `coordinate labeling with casatools <https://github.com/casangi/casagui/blob/main/devel/docs/image-tool-labels.md>`_
