.. casagui documentation master file, created by
   sphinx-quickstart on Tue Jun 29 18:33:59 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

CASA Visualization Environment
==============================
The :code:`casagui` package provides graphical user interfaces for the :xref:`casa` radio astronomy
package. This new generation of interfaces will be based upon :xref"`bokeh` and will use
web browsers for display. They are implemented in Python.

There are two basic documentation sections the primary section describes the applications that are
provided by :code:`casagui`. This section also describes the application programming interface (API)
which can be used to launch and interact with the applications provided by :code:`casagui`. The
second describes the motivation, the design and the long term goals of :code:`casagui`.

Applications and API
--------------------

The first application provided by :code:`casagui` is interactive clean. It has a simple API which
allows users to performe interactive image reconstruction using CASA.


.. toctree::
   :maxdepth: 3
   :caption: Contents:

   applications/intro


Development and Design
-----------------------

The design and development section describes the motivation, choices and architecture for
:code:`casagui`. It describes the design choice and tradeoffs that have been made. This section
is priarialy useful for those users who would like to understand the design of :code:`casagui`,
develop new :code:`casagui` applications or use the tools found within :code:`casagui` to create
new or different applications.

.. toctree::
   :maxdepth: 3
   :caption: Contents:

   design/intro
   design/boundary
   python/casagui


Index
=======

Automatically generated indexes.

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
