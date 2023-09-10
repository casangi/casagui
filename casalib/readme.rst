
Custom Bokeh-Independent TypeScript Code for casagui
----------------------------------------------------

Introduction
------------

This section shows the steps involved in building :code:`casalib`. This library includes the *Bokeh-independent* TypeScript code used by :code:`casaguijs`. This includes dedicated TypeScript code created by CASA, the `coordtxl <https://www.npmjs.com/package/coordtxl>`_ world coordinate library and the `hotkeys-js <https://www.npmjs.com/package/hotkeys-js>`_ keyboard management library. All of these pieces are compiled into a *minified* JavaScript library which is available when :code:`casagui` applications are launched.

Build and Install
-----------------

#. ``yarn install``
#. ``yarn build``
#. ``yarn esbuild-browser``

After the build is complete, commit the artifacts to the JavaScript directory in the :code:`casagui` Python package, e.g.::

  bash$ cp dist/esbuild/casalib.min.js ../casagui/__js__/casalib.min.js

The :code:`casagui` JavaScript libraries are installed as part of the Python package and are loaded directly from disk at Bokeh startup time. The version of these JavaScript libraries is intended to match whatever version of Bokeh that :code:`casagui` currently depends upon.
