import { cloneDeep } from "lodash";
export const deep_copy = cloneDeep;

// returns the number of keys of an object, e.g., {a:5, b:7, d:'hello'} --> 3
export function len(obj: object | undefined | null): number {
  if (obj == null) {
    return 0;
  }
  return Object.keys(obj).length;
}

export function debug( category: string, mesg: string, ...args: any[] ): void {
//    console.info(`----[${category}]------------------------------------------------------------------------------------------`)
//    args.forEach(arg => console.info(arg))
//    console.trace(mesg)
}
