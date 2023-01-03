The steps involved in building casalib which includes `hotkeys-js <https://github.com/jaywcjlove/hotkeys>`_.


#. ``yarn install``
#. ``yarn build``
#. ``yarn esbuild-browser``

After the build is complete, commit the artifacts to the `casagui-js <https://github.com/casangi/casagui-js>`_ repository, e.g.::

  bash$ cp dist/esbuild/casalib-v0.0.3.min.js* ~/develop/casagui-js/runtime/0.0.6
  bash$ cd ~/develop/casagui-js/runtime
  bash$ git add casalib-v0.0.3.min.js*
  bash$ git commit -m 'update hotkeys-js to 3.10.1'
  bash$ git push

This will make the new library version available as ``https://cdn.jsdelivr.net/gh/casangi/casagui-js@main/runtime/0.0.6/casalib-v0.0.3.min.js``.
