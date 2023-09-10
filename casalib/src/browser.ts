/**
 * This file is the entrypoint of browser builds.
 * The code executes when loaded in a browser.
 */
import { object_id } from './object_id'
import { ReconnectState } from "./reconnect_state"

import * as coordtxl from 'coordtxl'
import hotkeys from 'hotkeys-js'
import { contours } from 'd3-contour'

export { coordtxl, hotkeys, contours }

// eslint-disable-next-line @typescript-eslint/no-explicit-any
(window as any).object_id = object_id;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
(window as any).ReconnectState = ReconnectState;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
(window as any).coordtxl = coordtxl;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
(window as any).contours = contours;
