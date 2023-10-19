
export function zip( ...args: [ [any] ] ) {
    return args[0].map((_,c)=>args.map(row=>row[c]))
}

export function unzip( zip: [ any[] ] ) {
    return zip.length <= 0 ? zip : zip.reduce( (acc, tuple) => acc.map( (a,index) => [...a, tuple[index]] ), zip[0].map(_ => []) )
}
