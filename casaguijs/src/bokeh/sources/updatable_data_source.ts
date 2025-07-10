import { ColumnDataSource } from "@bokehjs/models/sources/column_data_source"
import * as p from "@bokehjs/core/properties"
import { DataPipe } from "./data_pipe"
import { CallbackLike0, CallbackLike1 } from "@bokehjs/core/util/callbacks";
import {execute} from "@bokehjs/core/util/callbacks"

// Data source where the data is defined column-wise, i.e. each key in the
// the data attribute is a column name, and its value is an array of scalars.
// Each column should be the same length.
export namespace UpdatableDataSource {
  export type Attrs = p.AttrsOf<Props>

  export type Props = ColumnDataSource.Props & {
      js_init: p.Property<CallbackLike0<UpdatableDataSource> | null>;
      js_update: p.Property<CallbackLike1<UpdatableDataSource, [ { [key: string]: any }, { [key: string]: any } ] > | null>;
      pipe: p.Property<DataPipe>
      session_id: p.Property<String>
  }
}

export interface UpdatableDataSource extends UpdatableDataSource.Attrs {}

export class UpdatableDataSource extends ColumnDataSource {
    declare properties: UpdatableDataSource.Props

    static __module__ = "casagui.bokeh.sources._updatable_data_source"

    constructor(attrs?: Partial<UpdatableDataSource.Attrs>) {
        super(attrs);
    }

    send( message: {[key: string]: any}, cb: (msg:any) => any ): void {
        this.pipe.send( this.session_id.valueOf( ), { action: 'callback', message },
            (msg) => {
                if ( 'result' in msg ) cb(msg.result)
                else cb( { error: `expected to find a "result" in "${msg}"`, msg } )
            } ) }
            
    initialize(): void {
        super.initialize();
        const _execute = () => {
            if ( this.js_init != null ) void execute( this.js_init, this )
        }
        _execute( )
    }

    static {
        this.define<UpdatableDataSource.Props>(({ Ref, Any, String }) => ({
            js_init: [ Any, null ],
            js_update: [ Any, null ],
            pipe: [ Ref(DataPipe) ],
            session_id: [ String ],
        }));
    }
}
