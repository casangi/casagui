import {DataPipe} from "./src/bokeh/sources/data_pipe"
import {ImagePipe} from "./src/bokeh/sources/image_pipe"
import {ImageDataSource} from "./src/bokeh/sources/image_data_source"
import {SpectraDataSource} from "./src/bokeh/sources/spectra_data_source"
import {WcsTicks} from "./src/bokeh/format/wcs_ticks"
import {register_models} from "@bokehjs/base"

export { DataPipe, ImagePipe, ImageDataSource, SpectraDataSource, WcsTicks }

register_models({DataPipe, ImagePipe, ImageDataSource, SpectraDataSource, WcsTicks})
