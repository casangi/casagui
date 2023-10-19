/**
 * This file is the entrypoint of browser builds.
 * The code executes when loaded in a browser.
 */
import { object_id } from './object_id'
import { ReconnectState } from "./reconnect_state"
import { zip, unzip } from "./zip"

import * as coordtxl from 'coordtxl'
import hotkeys from 'hotkeys-js'
import { contours } from 'd3-contour'
// see https://d3js.org/d3-polygon
import { polygonContains } from 'd3-polygon'

declare global {
    var Bokeh: any
}

var casalib = {
    zip,
    unzip,
    object_id,
    coordtxl,
    hotkeys,
    ReconnectState,
    d3: { contours, polygonContains },
    // TypeScript is poor
    // ------------------
    // Without this bit of stupidity, 'casalib' is flagged with a compile time error:
    //    'casalib' implicitly has type 'any' because it does not have a type annotation and is referenced directly or indirectly in its own initializer.
    // Ignoring this error, results in the runtime error:
    //    Uncaught TypeError: {(intermediate value)(intermediate value)(intermediate value)(intermediate value)(intermediate value)} is not a function
    // Is TypeScript an undergrad CS project gone awry?
    _dummy: undefined
}

if ( typeof Bokeh !== "undefined" ) {
    if ( typeof Bokeh._dummy != "undefined" ) {
        casalib._dummy = Bokeh._dummy
    }
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
(window as any).casalib = casalib;
