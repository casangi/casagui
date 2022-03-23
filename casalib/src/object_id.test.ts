import { object_id } from './object_id'

test('existing object id', () => {
  expect( object_id({ _casagui_id_: 'existing-object-id'}) ).toBe('existing-object-id')
})
