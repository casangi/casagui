# casaguijs

This directory contains the build tree for the TypeScript portion of the
`casagui` extensions for [Bokeh](https://bokeh.org/). However, it *only*
contains the _TypeScript_ build infrastructure, not the actual _TypeScript_
source files. The source files are included with the _Python_ files in the
`casagui` tree found in the parent directory. This allows the _TypeScript_
and _Python_ files to be edited from the same directory and keeps the
`npm` clutter out of the _Python_ package directory.

## Build Instructions

`npm` and `bokeh` are used to build these extensions:

1. Ensure that the `bokeh` executable is available
   ```
   bash$ type bokeh
   bokeh is hashed (/opt/local/Library/Frameworks/Python.framework/Versions/3.8/bin/bokeh)
   bash$
   ```
2. Run `bokeh build`
   ```
   bash$ bokeh build
   Working directory: /Users/drs/develop/casagui/kernels/python/casaguijs
   Using different version of bokeh, rebuilding from scratch.
   Running npm install.

   added 41 packages, and audited 42 packages in 1s

   found 0 vulnerabilities
   Using /Users/drs/develop/casagui/kernels/python/casaguijs/tsconfig.json
   Compiling styles
   Compiling TypeScript (2 files)
   Linking modules
   Output written to /Users/drs/develop/casagui/kernels/python/casaguijs/dist
   All done.
   bash$
   ```
3. `bokeh` uses a cache, so if you suspect you are not getting a clean rebuild, try `bokeh build --rebuild`
