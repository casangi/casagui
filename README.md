# casadesk

CASA GUI Desktop application.

## Installation

Developers can build and run casadesk with:

1.  `bash$ git  clone https://github.com/casangi/casadesk.git`
1.  `bash$ cd casadesk`
1.  `bash$ npm install`
1.  `bash$ pushd node_modules/zeromq
1.  `bash$ HOME=~/.electron-gyp ../.bin/node-gyp rebuild --target=12.0.2 --arch=x64 --dist-url=https://electronjs.org/headers
1.  `bash$ popd
1.  `bash$ npm start`

A few standard `npm` packages (`enchannel-zmq-backend`, `jmp`, `jupyter-paths`, `kernelspecs`, and `spawnteract`] are included directly instead of through installed packages to allow for upgrading to the latest `zeromq.js` distribution in the future.
