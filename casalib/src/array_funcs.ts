
export function is_empty( array: any ): boolean {
    return Array.isArray(array) && (array.length == 0 || array.every(is_empty))
}

export function minmax( ary: number[] ): [number,number] {
    if ( ary.length < 1 ) return [NaN,NaN]
    let min, max
    min = max = ary[0]
    for ( let index = ary.length-1; index > 0; --index ) {
        if ( ary[index] < min ) min = ary[index]
        if ( ary[index] > max ) max = ary[index]
    }
    return [ min, max ]
}

export function sorted( coll: number[] | Set<number> ): number[] {

    if ( coll instanceof Set )
        return Array.from(coll).sort(( a:number, b:number ) => a - b)
    else if ( Array.isArray(coll) )
        return coll.slice().sort((a, b) => a - b)  // copy coll and sort in place

    throw new Error( `unexpected parameter type (${typeof coll})` )
}

export function arrayeq<T>( arr1: T[], arr2: T[] ): boolean {
    return arr1.length === arr2.length && arr1.every((val, index) => val === arr2[index])
}
