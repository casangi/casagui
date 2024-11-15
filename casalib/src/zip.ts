
export function zip<T>(...arrays: T[][]): T[][] {
  const maxLength = Math.max(...arrays.map(arr => arr.length));
  const result: T[][] = [];

  for (let i = 0; i < maxLength; i++) {
    const row = arrays.map(arr => arr[i]);
    result.push(row);
  }

  return result;
}

export function unzip( zip: [ any[] ] ) {
    return zip.length <= 0 ? zip : zip.reduce( (acc, tuple) => acc.map( (a,index) => [...a, tuple[index]] ), zip[0].map(_ => []) )
}
