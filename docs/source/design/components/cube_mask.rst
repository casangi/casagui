.. _design-system-design:

Cube Mask Design Document
====================

.. currentmodule:: design

The cube mask toolkit is a group of related components that can be used to construct different
GUIs that are composed of GUI elements taken from a collection of interacting widgets/components.
Application builders do not have to adopt all of the elements in this collection. A few of the
widgets can be used or all can be used. The only component that must be used is the ``image``
widget. This component is the central image cube display window which includes the ability to
step through the channels of the image cube, and it is the users interaction with this component
that drives the other component.
