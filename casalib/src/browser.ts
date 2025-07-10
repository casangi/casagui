/**
 * This file is the entrypoint of browser builds.
 * The code executes when loaded in a browser.
 */
import { object_id } from './object_id'
//import { map, reduce } from "./functional"
import { map, reduce, debounce } from "./functional"
import { is_empty, minmax, sorted } from './array_funcs'
import { strparse_intranges, intlist_to_rangestr } from './string_funcs'
import { forexpr } from './loop_funcs'
import { ReconnectState } from "./reconnect_state"
import { zip, unzip } from "./zip"
import { BiMap } from "./bimap_class"
import { BoundedBiMap } from "./boundedbimap_class"
import { EqSet } from "./eqset_class"
import { eq } from "./equals"

import * as coordtxl from 'coordtxl'
import hotkeys from 'hotkeys-js'
import { contours } from 'd3-contour'
// see https://d3js.org/d3-polygon
import { polygonContains, polygonArea } from 'd3-polygon'

//
// In JavaScript "'PROP' in OBJ" only works if the type of OBJ
// is actually an object. 'hasOwnProperty' can only be use
// for objects as well. Also, OBJ.hasOwnProperty('PROP') returns
// false for most Bokeh models presumably because the PROPs
// are defined in a prototype...
//
// 'hasprop' resolves these problems by combining checks checks
// for whether the object is an object, is not null and that the
// PROP is somehow defined... so for example hasprop returns
// false for "hasprop(true)"...
//
function hasprop( obj: any, prop: string ) {
    return typeof obj == 'object' && obj && prop in obj
}

declare global {
    var Bokeh: any
}

function isPtList( value: unknown ): value is [number, number][] {
    if ( !Array.isArray(value) ) return false;
    for (const item of value) {
        if (!Array.isArray(item) || item.length !== 2 || typeof item[0] !== 'number' || typeof item[1] !== 'number') {
            return false;
        }
    }
    return true;
}

function polyArea( pts: number[] | [number, number][], ypts?: number[] ) : number {
    if ( pts.length <= 0 ) return 0
    if ( isPtList( pts ) ) polygonArea( pts )
    // @ts-ignore: Type 'any[]' is not assignable to type '[number, number]'.
    return polygonArea( zip( pts, ypts ) )
}

var casalib = {
    is_empty,
    minmax,
    sorted,
    strparse_intranges,
    intlist_to_rangestr,
    map,
    reduce,
    debounce,
    zip,
    unzip,
    forexpr,
    object_id,
    coordtxl,
    hotkeys,
    ReconnectState,
    polyArea,
    BiMap, BoundedBiMap,
    EqSet, eq,
    d3: { contours, polygonContains, polygonArea },
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


/********************************************************************************
*** Export some symbols directly for use with Bokeh:                          ***
***                                                                           ***
***    hasprop: robust check for property within an object                    ***
***    zip:     zip two lists                                                 ***
***    casalib: all exported casalib symbols                                  ***
***    EqSet: set class that accepts an equality function, e.g. for sets      ***
***           containing arrays                                               ***
***    BiMap: bi-directional map                                              ***
********************************************************************************/
// eslint-disable-next-line @typescript-eslint/no-explicit-any
(window as any).casalib = casalib;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
(window as any).hasprop = hasprop;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
(window as any).zip = zip;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
(window as any).EqSet = EqSet;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
(window as any).BiMap = BiMap;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
(window as any).BoundedBiMap = BoundedBiMap;
