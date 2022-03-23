
export function object_id( obj: { [key: string]: any } ): string {
    if ( typeof obj._casagui_id_ === 'undefined' ) {
        let array = null
        if ( typeof window === 'undefined' ) {
            if ( typeof crypto !== 'undefined' ) {
                // src/utils/object_id.ts:10:39 - error TS2339: Property 'randomBytes' does not exist on type 'Crypto'.
                // crypto in node has randomBytes (not sure how to fix this correctly)
                // @ts-ignore
                let ranbytes = crypto.randomBytes(8)
                array = new Uint32Array(ranbytes.buffer.slice(-4))
            }
        }  else {
            array = new Uint32Array(1)
            window.crypto.getRandomValues(array)
        }
        let d = new Date()
        let seconds = Math.floor(d.getTime() / 1000)
        obj._casagui_id_ = `${array ? array[0] : seconds}-${seconds}`
    }
    return obj._casagui_id_
}
