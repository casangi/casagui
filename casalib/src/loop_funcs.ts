
/**********************************************************************************
*** A for loop that behaves like an expression...                               ***
***                                                                             ***
***      forexpr( start, end, ( acc, val, index ) => reducer, initial reducer ) ***
**********************************************************************************/
export function forexpr<T>( start: number, end: number, reducer: (accumulator: T, currentValue: number, index: number) => T, initialValue: T): T {
  let accumulator = initialValue;

  for ( let i = start; i <= end; i++ ) {
    accumulator = reducer(accumulator, i, i - start);
  }

  return accumulator;
}
