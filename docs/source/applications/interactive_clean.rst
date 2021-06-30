
Interactive Clean
======================

.. currentmodule:: applications

The visualization infrastructure of CASA will be built out by completing pathfinder
applications. These applications will build team knowledge and expand our codebase
as we encounter new opportunities and challenges. Interactive clean is the first
pathfinder application for the :ref:`terminal usage setting <design-terminal-usage>`.
This is an important use case because it pushes the boundraries of what is possible
in this usage setting.

Infrastructure
----------------------

For this use case, we had certain requirements that stretched the capabilities of :xref:`bokeh`
browser plotting:

* two directional communication was necessary between Python and the
  interactive clean display in the web browser
* state needed to be returned to the Python session where :code:`tclean` is running

:xref:`bokeh`'s solution for the first issue is to serve the browser code from a
``bokeh server`` process. Unfortunately, this python process is separate from the
:code:`tclean` process, and interactive clean requires an ongoing dialog between
the imageing code in Python and the display the user interacts with in a browser.

To solve these problems, we introduced a :xref:`websocket` based infrastructure
to handle the update of browser display as :code:`tclean` proceeds.

Implementation
---------------------

While we are only in the prototyping phase of the interactive clean application, we have
prototyped a GUI that will go beyond what is currently possible with current
implementations of interactive clean, as show in this figure:

.. image:: _static/iclean_prototype_gui.png
           :align: left
           :width: 800px

