import {ID, ByteOrder, DataType} from "./typedefs"
import type {NDArray} from "./ndarray"
import {BYTE_ORDER} from "./platform"

//-------------------- from ./types ----------------------------------------------------------------------
export function isObject(obj: unknown): obj is object {
  const tp = typeof obj
  return tp === "function" || tp === "object" && !!obj
}

export function isPlainObject<T>(obj: unknown): obj is {[key: string]: T} {
  return isObject(obj) && (obj.constructor == null || obj.constructor === Object)
}
//--------------------------------------------------------------------------------------------------------

//-------------------- from ./buffer ---------------------------------------------------------------------
export function buffer_to_base64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer)
  const chars = Array.from(bytes).map((b) => String.fromCharCode(b))
  return btoa(chars.join(""))
}

export function base64_to_buffer(base64: string): ArrayBuffer {
  const binary_string = atob(base64)
  const len = binary_string.length
  const bytes = new Uint8Array(len)
  for (let i = 0, end = len; i < end; i++) {
    bytes[i] = binary_string.charCodeAt(i)
  }
  return bytes.buffer
}

// NOTE: swap{16,32,64} assume byteOffset == 0

function swap16(buffer: ArrayBuffer): void {
  const x = new Uint8Array(buffer)
  for (let i = 0, end = x.length; i < end; i += 2) {
    const t = x[i]
    x[i] = x[i + 1]
    x[i + 1] = t
  }
}

function swap32(buffer: ArrayBuffer): void {
  const x = new Uint8Array(buffer)
  for (let i = 0, end = x.length; i < end; i += 4) {
    let t = x[i]
    x[i] = x[i + 3]
    x[i + 3] = t
    t = x[i + 1]
    x[i + 1] = x[i + 2]
    x[i + 2] = t
  }
}

function swap64(buffer: ArrayBuffer): void {
  const x = new Uint8Array(buffer)
  for (let i = 0, end = x.length; i < end; i += 8) {
    let t = x[i]
    x[i] = x[i + 7]
    x[i + 7] = t
    t = x[i + 1]
    x[i + 1] = x[i + 6]
    x[i + 6] = t
    t = x[i + 2]
    x[i + 2] = x[i + 5]
    x[i + 5] = t
    t = x[i + 3]
    x[i + 3] = x[i + 4]
    x[i + 4] = t
  }
}

export function swap(buffer: ArrayBuffer, dtype: DataType): void {
  switch (dtype) {
    case "uint16":
    case "int16":
      swap16(buffer)
      break
    case "uint32":
    case "int32":
    case "float32":
      swap32(buffer)
      break
    case "float64":
      swap64(buffer)
      break
  }
}
//--------------------------------------------------------------------------------------------------------



export type Shape = number[]

export type BufferRef = {
  __buffer__: string
  order: ByteOrder
  dtype: DataType
  shape: Shape
}

export type NDArrayRef = {
  __ndarray__: string | {toJSON(): string}
  order: ByteOrder
  dtype: DataType
  shape: Shape
}

export function is_NDArray_ref(v: unknown): v is BufferRef | NDArrayRef {
  return isPlainObject(v) && ("__buffer__" in v || "__ndarray__" in v)
}

export type Buffers = Map<ID, ArrayBuffer>

export function decode_NDArray(ref: BufferRef | NDArrayRef, buffers: Buffers): {buffer: ArrayBuffer, dtype: DataType, shape: Shape} {
  const {shape, dtype, order} = ref

  let bytes: ArrayBuffer
  if ("__buffer__" in ref) {
    const buffer = buffers.get(ref.__buffer__)
    if (buffer != null)
      bytes = buffer
    else
      throw new Error(`buffer for ${ref.__buffer__} not found`)
  } else {
    bytes = base64_to_buffer(ref.__ndarray__ as string)
  }

  if (order !== BYTE_ORDER) {
    swap(bytes, dtype)
  }

  return {buffer: bytes, dtype, shape}
}

export function encode_NDArray(array: NDArray, buffers?: Buffers): BufferRef | NDArrayRef {
  const data = {
    order: BYTE_ORDER,
    dtype: array.dtype,
    shape: array.shape,
  }

  if (buffers != null) {
    const __buffer__ = `${buffers.size}`
    buffers.set(__buffer__, array.buffer)
    return {__buffer__, ...data}
  } else {
    const __ndarray__ = {
      toJSON(): string {
        return buffer_to_base64(array.buffer)
      },
    }
    return {__ndarray__, ...data}
  }
}
