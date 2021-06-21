//import {ImagePipe} from "./src/bokeh/sources/image_pipe"
import {ImageDataSource} from "./src/bokeh/sources/image_data_source"
import {register_models} from "@bokehjs/base"

export { /*ImagePipe,*/ ImageDataSource }

register_models({ ImageDataSource /*, ImagePipe*/ })
