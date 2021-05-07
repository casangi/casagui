# casagui

CASA GUI Desktop application.

## Installation

Developers can build and run casagui with:

1.  `bash$ git  clone https://github.com/casangi/casagui.git`
1.  `bash$ cd casagui`
1.  `bash$ npm install`
1.  `bash$ pushd node_modules/zeromq`
1.  `bash$ HOME=~/.electron-gyp ../.bin/node-gyp rebuild --target=12.0.2 --arch=x64 --dist-url=https://electronjs.org/headers`
1.  `bash$ popd`
1.  `bash$ npm start`

A few standard `npm` packages (`enchannel-zmq-backend`, `jmp`, `jupyter-paths`, `kernelspecs`, and `spawnteract`) are included directly instead of through installed packages to allow for upgrading to the latest `zeromq.js` distribution in the future.

Currently, it is assumed that you have a working `python3` interpreter in your path that has the `ipykernel` package installed. This package can be installed with:
```
bash$ python -m pip install ipykernel
bash$ python -m ipykernel install --user
```
You can check to make sure the Jupyter kernel is available with:
```
bash$ python3 -m ipykernel_launcher --help
```
Any Python packages you want to use must be installed too. In particular:
```
bash$ pip install plotly==4.14.3
```
Finally, a good way to test your kernel is by installing the [nteract desktop app](https://nteract.io/). Some experimentation may be required. This was the case with installing Python with [macports](https://www.macports.org/) and then getting the [nteract desktop app](https://nteract.io/) to use Python from there.
