
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

After the build is complete, commit the artifacts to the `casagui-js <https://github.com/casangi/casagui-js>`_ repository, e.g.::

  bash$ cp dist/esbuild/casalib-v0.0.3.min.js* ~/develop/casagui-js/runtime/0.0.6
  bash$ cd ~/develop/casagui-js/runtime
  bash$ git add casalib-v0.0.3.min.js*
  bash$ git commit -m 'update hotkeys-js to 3.10.1'
  bash$ git push

The `casagui-js runtime <https://github.com/casangi/casagui-js/tree/main/runtime>`_ files are made available through `https://cdn.jsdelivr.net/gh/casangi/casagui-js@main/runtime/0.0.6/casalib-v0.0.3.min.js`. In this example, the :code:`casaguijs` version would be :code:`0.0.6`. All of the files for version :code:`0.0.6` of :code:`casaguijs`, are in a :code:`0.0.6` sub-directory. :code:`casalib` has a separate version number, in this case :code:`0.0.3`. These are old version numbers and the current version of these libraries must be substituted.

