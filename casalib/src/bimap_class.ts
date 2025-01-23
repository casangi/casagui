
export class BiMap<K, V> {
    private readonly forwardMap: Map<K, V>
    private readonly inverseMap: Map<V, K>

    constructor() {
        this.forwardMap = new Map<K, V>()
        this.inverseMap = new Map<V, K>()
    }

    set(key: K, value: V): void {
        this.forwardMap.set(key, value)
        this.inverseMap.set(value, key)
    }

    get(key: K): V | undefined {
        return this.forwardMap.get(key)
    }

    getKey(value: V): K | undefined {
        return this.inverseMap.get(value)
    }

    delete(key: K): V | undefined{
        const value = this.forwardMap.get(key)
        if (value !== undefined) {
            this.forwardMap.delete(key)
            this.inverseMap.delete(value)
            return value
        }
        return undefined
    }

    deleteValue(value: V): K | undefined{
        const key = this.inverseMap.get(value)
        if (key !== undefined) {
            this.inverseMap.delete(value)
            this.forwardMap.delete(key)
            return key
        }
        return undefined
    }

    has(key: K): boolean {
        return this.forwardMap.has(key)
    }

    hasValue(value: V): boolean {
        return this.inverseMap.has(value)
    }

    clear(): void {
        this.forwardMap.clear()
        this.inverseMap.clear()
    }

    get size(): number {
        return this.forwardMap.size
    }

    *entries(): IterableIterator<[K, V]> {
        return this.forwardMap.entries()
    }

    map<R>(callback: (value: V, key: K, map: BiMap<K, V>) => R): R[] {
        const result: R[] = []
        for (const [key, value] of this.entries( ) ) {
            result.push(callback(value, key, this))
        }
        return result;
    }
}
//Example usage:
//TypeScript

//const bimap = new BiMap<string, number>()
//bimap.set("one", 1)
//bimap.set("two", 2)

//console.log(bimap.get("one")) // 1
//console.log(bimap.getKey(2)) // "two"
