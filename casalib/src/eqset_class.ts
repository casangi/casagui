import { eq } from "./equals"


export class EqSet<T> extends Set<T> {
    constructor( values?: Iterable<T>, private comparator: (a: T, b: T) => boolean = eq  ) {
        super(values);
    }

    add( value: T ): this {
        if ( this.comparator ) {
            for ( const item of this ) {
                if ( this.comparator(value, item) ) {
                    return this; // Don't add if the comparator considers them equal
                }
            }
        }

        return super.add( value );
    }

    has( value: T ): boolean {
        if ( this.comparator ) {
            for ( const item of this ) {
                if ( this.comparator(value,item) ) {
                    return true
                }
            }
            return false
        }
        return super.has(value)
    }

    delete( value: T ): boolean {
        if ( this.comparator ) {
            for ( const item of this ) {
                if ( this.comparator(value,item) ) {
                    super.delete( item )
                    return true
                }
            }
            return false
        }
        return super.delete( value )
    }

    difference( other: Set<T> ): EqSet<T> {
        const result = new EqSet<T>( undefined, this.comparator );

        for ( const item of this ) {
            if ( ! other.has(item) ) {
                result.add( item );
            }
        }
        return result;
    }

    intersection( other: Set<T> ): EqSet<T> {
        const result = new EqSet<T>( undefined, this.comparator );

        for ( const item of this ) {
            if ( other.has( item ) ) {
                result.add( item );
            }
        }

        return result;
    }

    /******************************************************
    ***  To Do; implement the remaining set operations  ***
    ******************************************************/;
}



//const set1 = new EqSet([1, 2, 3]);
//const set2 = new EqSet([2, 3, 4]);

//const differenceSet = set1.difference(set2); // {1}
//const intersectionSet = set1.intersection(set2); // {2, 3}


//const comparator = (a: string, b: string) => a.toLowerCase() === b.toLowerCase();
//const set3 = new EqSet(["apple", "Banana"], comparator);
//const set4 = new EqSet(["Apple", "orange"], comparator);

//const differenceSet = set3.difference(set4); // {"Banana"}
//const intersectionSet = set3.intersection(set4); // {"apple"}
