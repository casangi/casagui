import { sorted } from "./array_funcs"

/********************************************************************************
*** Parse ranges like: -10:-2, -5:0,12,15, 22-56                              ***
********************************************************************************/
export function strparse_intranges( str: string, allow_reverse: boolean = false ): number[][] {
    const ranges = []
    const rangeStrings = str.split(',')


    for (const rangeStr of rangeStrings) {
        // Split each range into start and end
        const [startStr, endStr] = rangeStr.trim().split(':')

        const start = parseInt(startStr, 10)
        const end = endStr ? parseInt(endStr, 10) : start

        if ( isNaN(start) || isNaN(end) ) {
            throw new Error(`Invalid range: ${rangeStr}`)
        } else {
            if  ( start > end ) {
                if ( allow_reverse )
                    ranges.push( [end, start] )
                else
                    throw new Error(`Invalid range: ${rangeStr}`)
            } else {
                ranges.push( [start, end] )
            }
        }
    }
    return ranges
}

export function intlist_to_rangestr( intlist: number[] | Set<number> ): string {
    const ranges = sorted(intlist).reduce( (acc, v) => { if ( acc[0][0] == null ) return [[v,v]]
                                                         // @ts-ignore: acc[0][1] is possibly 'null'. (typescript has an overactive imagination)
                                                         if ( v > acc[0][1] + 1 ) return [[v,v],...acc]
                                                         return [[acc[0][0],v],...acc.slice(1)]
                                                       }, [[null,-1]] ).reverse( )
    return ranges.map( v => v[0] == v[1] ? `${v[0]}` : `${v[0]}:${v[1]}` ).join(', ')
}
