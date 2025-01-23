
export function eq(a: any, b: any): boolean {

    if ( a === b ) {
        return true;
    }
    if ( typeof a !== typeof b ) {
        return false;
    }
    if ( Array.isArray(a) && Array.isArray(b) ) {
        if ( a.length !== b.length ) {
            return false;
        }
        for ( let i = 0; i < a.length; i++ ) {
            if ( !eq(a[i], b[i]) ) {
                return false;
            }
        }
        return true;
    }
    if ( typeof a === 'object' && typeof b === 'object' ) {
        const keysA = Object.keys(a);
        const keysB = Object.keys(b);

        if ( keysA.length !== keysB.length ) {
            return false;
        }

        for ( const key of keysA ) {
            if ( !keysB.includes(key) || !eq(a[key], b[key]) ) {
                return false;
            }
        }
        return true;
    }

    return false;
}
