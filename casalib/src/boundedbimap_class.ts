
import { BiMap } from './bimap_class'

export class BoundedBiMap<K,V> extends BiMap<K,V> {
    private usedKeys: Set<K>
    private availKeys: Set<K>

    constructor( private keyset: Set<K> ) {
        super( )
        this.usedKeys = new Set<K>( )
        this.availKeys = new Set<K>(keyset)
    }

    clear(): void {
        super.clear( )
        this.usedKeys = new Set<K>( )
        this.availKeys = new Set<K>(this.keyset)
    }

    add( value: V ): K | undefined {
        if ( this.availKeys.size === 0 )
            return undefined
        for ( const key of this.availKeys ) {
            this.availKeys.delete(key)
            this.usedKeys.add(key)
            super.set(key,value)
            return key
        }
        return undefined
    }

    get bound( ): Set<K> {
        return new Set<K>(this.keyset)
    }
            
    set(key: K, value: V): void {
        if ( ! this.keyset.has( key ) )
            throw new Error( `${key} is not a valid key` )
        if ( this.availKeys.has( key ) )
            this.availKeys.delete(key)
        if ( ! this.usedKeys.has( key ) )
            this.usedKeys.add(key)
        super.set(key,value)
    }

    delete(key: K): V | undefined {
        if ( key ) {
            this.usedKeys.delete(key)
            this.availKeys.add(key)
        }
        return super.delete(key)
    }

    deleteValue(value: V): K | undefined {
        const key = super.getKey(value)
        if ( key ) {
            this.usedKeys.delete(key)
            this.availKeys.add(key)
        }
        return super.deleteValue(value)
    }
}
