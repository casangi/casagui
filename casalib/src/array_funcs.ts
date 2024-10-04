
export function is_empty( array: any ): boolean {
    return Array.isArray(array) && (array.length == 0 || array.every(is_empty))
}
