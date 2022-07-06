.. _design-system-design:

====================
Cube Mask Design Document
====================

.. currentmodule:: design

The cube mask toolkit is a group of related components that can be used to construct different
GUIs related to image cube applications. Application builders do not need to adopt all of the
lements in this collection. A few of the widgets can be used or all can be used. The only
component that must be used is the ``image`` widget. This component is the central image cube
display window which includes the ability to step through the channels of the image cube, and
it is the users interaction with this component that drives the other component.


Image
====================

An image cube can be displayed with this code::

  import asyncio
  from bokeh.plotting import show
  from bokeh.layouts import row, column
  from casagui.toolbox import CubeMask

  cube = CubeMask( 'g35_sma_usb_12co.image' )
  image = cube.image( )
  cube.connect( )
  show( image )

  try:
      loop = asyncio.get_event_loop( )
      loop.run_until_complete(cube.loop( ))
      loop.run_forever( )
  except KeyboardInterrupt:
      print('\nInterrupt received, stopping GUI...')

  print( f"cube exited with {cube.result( )}" )

The ``image`` function creates a two-dimensional plot that displays one channel from the
image cube which was passed in as a constructor parameter. Even without any controls the
image display can be used to create regions and move through the channels of the cube
(Option-Ctrl-Up on MacOS and Alt-Ctrl-Up on Linux moves to the next channel).

.. image:: image.png
  :width: 400
  :alt: Image Cube

The image update is managed via the ``asyncio`` event loop. The tools along the edge
can be used to draw regions, scroll, pan, zoom, etc. The regions are accessable after
successful completion of GUI interactions.

Channel Scrolling
====================
The ``CubeMask`` object provides access to other GUI components that are integrated with
the image display. Scrolling with a slider that makes traversing the channels much easier,
and it can be added, assuming the same imports as above, like::

  cube = CubeMask( 'g35_sma_usb_12co.image' )
  layout = column( cube.image( ),
                   cube.slider( ) )
  cube.connect( )
  show( layout )

  try:
      loop = asyncio.get_event_loop( )
      loop.run_until_complete(cube.loop( ))
      loop.run_forever( )
  except KeyboardInterrupt:
      print('\nInterrupt received, stopping GUI...')

  print( f"cube exited with {cube.result( )}" )

.. image:: image-slider.png
  :width: 400
  :alt: Image Cube w/ Slider

The component usage is indicated by calling the accessor functions, e.g. ``image`` or
``slider`` here, and the call to the ``connect`` member function connects the *behind
the scenes* connections to make all of the elements (*that are in use*) interact and
update in response to user input.

Spectra (Z-Axis) Display
====================
Another useful component included in ``CubeMask`` is the spectra display. This display
shows the image spectra along the z-axis of the image cube. As with ``slider`` above
the spectra display is accessed with the ``spectra`` member function::

  cube = CubeMask( 'g35_sma_usb_12co.image' )
  layout = column( cube.image( ),
                   cube.slider( ),
                   cube.spectra( width=400 ) )
  cube.connect( )
  show( layout )

  try:
      loop = asyncio.get_event_loop( )
      loop.run_until_complete(cube.loop( ))
      loop.run_forever( )
  except KeyboardInterrupt:
      print('\nInterrupt received, stopping GUI...')

  print( f"cube exited with {cube.result( )}" )

.. image:: image-slider-spectra.png
  :width: 400
  :alt: Image Cube w/ Slider + Spectra

 By default, the spectra display is wider, but these components generally support the
 same parameters supported by the underlying Bokeh components. In this case, the ``width``
 is specified.

