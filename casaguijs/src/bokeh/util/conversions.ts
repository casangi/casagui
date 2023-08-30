import {default_resolver} from "@bokehjs/base"
import {ModelResolver} from "@bokehjs/core/resolvers"
import {Deserializer} from "@bokehjs/core/serialization/deserializer"
import {Serializer} from "@bokehjs/core/serialization/serializer"

const { deserialize } = new class {
    resolver = new ModelResolver(default_resolver)
    deserializer = new Deserializer( this.resolver )
    deserialize = ( value: string ) => {
        try {
            return this.deserializer.decode( JSON.parse( value ) )
        } catch ( e1 ) {
            console.group( "deserialize error" )
            console.log( value )
            console.log( e1 )
            console.groupEnd( )
            return { }
        }
    }
}

const { serialize } = new class {
    serializer = new Serializer( )
    serialize = ( value: any ) => {
        // 'undefined' values cannot be serialized, they should
        // be replaced with 'null' somewhere above...
        return JSON.stringify(this.serializer.encode(value))
    }
}

export { deserialize, serialize }
