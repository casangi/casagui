.. _design-system-design:

CASA/Viz Boundary
====================

.. currentmodule:: design

This document describes the boundary between CASA-GUI and CASA (including CASA7 and future versions of
CASA). It is necessarily a high-level view of the principles of this boundary. However,
it is important to layout the system level view of this boundary to prevent choices being
made in the system design of other parts of the CASA and NRAO ecosystem.

For this discussion, only two execution modes will be considered. The "Usage Settings" in the introduction describe
the user context where casagui operates. The "Execution Modes" are less abstract than the "Usage Settings".
This lower level is discussed here both to explain the concepts as well as identify constraints that are
implied by the implementaton of these modes.

The assumption is that there is a GUI and that it is always
running on the user's device. In practice, this means that the GUI will be presented in the
user's browser. The execution that we are talking about is the execution process that creates
images, provides storage for images, modifies images, or collates and organizes data. These
processes could also be on the user's device, but they could also be running on remote systems.

Local Execution
-------------------

.. image:: _static/local_execution.svg
           :align: left
           :width: 220px

With local execution, there is a local Python process which executes all of the image and data
processing code. Currently, this is the user's Python session. Communication between this Python
process and the GUI code in the browser is accomplished with :xref:`websocket`. The user interacts
with the elements of the GUI within the browser. These interactions result in :xref:`websocket`
messages sent to the local Python environment. Within the Python environment, the interfaces
provided by CASA and other packages are used to accomplish the desired processing, and the results
are then returned to the GUI via :xref:`websocket`.


Remote Execution
-------------------

.. image:: _static/remote_execution.svg
           :align: left
           :width: 260px

Remote execution allows the user to start the GUI locally but perform the desired processing
tasks on a remote system which the user can access with SSH. To start a remote processing
execution, the user would first start a local Python session and then start the GUI element
specifying the remote host that should be used. The GUI will start and run locally, but
instead of the local Python session being used to perform the processing it will start
a remote :xref:`jupyterkernel` on the specified remote system. Messages sent to the local
Python session from the GUI via :xref:`websocket` will be converted to :xref:`jupyterprotocol`
messages sent to the remote kernel. These messages will then run the process using the same
interfaces provided by CASA and other packages as was used for local execution.

These two execution models are sufficient as the basis for the usage settings described
in the casagui system document. A variant of these execution models may also be sufficent
for a website implementation. The GUI elements created with :xref:`bokeh` are compatible
with display within a website. The remote :xref:`jupyterkernel` execution is compatible
with processing initiated from a website. The details of the execution model between a
public website portal and the backend execution model lies outside of the CASA/casagui
context.

Implications
----------------

The varied usage and execution environments emphasize a need to clearly separate the processing
functionality from the GUI elements. Pushing as much
functionality down into the processing level as possible as possible, maximizes the ability to
test functionality as part of processing level testing, independent of GUI elements.

The second implication arises from supporting remote execution. Because processing results
must be serialized and returned via :xref:`websocket` and displayed within a browser, the
processing interface must be defined in terms of basic Python types or types which can be
converted to basic Python types. An example of the latter is :xref:`numpy` arrays. The
interactive clean app uses :xref:`numpy` arrays to represent the images which are displayed
within :xref:`bokeh`.

Example - Interactive Clean
----------------

A first version of an interactive clean application is being designed as follows.
( This initial release
will **not** include remote execution, but its design does attempt to conform to the constraints
which remote execution requires.)

A locally running GUI in a browser contains tools for image viewing, mask editing, setting/editing
iteration control parameters, display and navigation of convergence plots. It also contains controls to trigger
iteration blocks in the processing layer and retrieves processing results with which to update
various elements of the display. The parameters and processing results are transferred from Python
to a web browser for display. As a result, they are serializable.

Events from the GUI connect to the processing layer via call-back methods encapsulated within :xref:`gclean`,
a backend application that runs the building blocks of image reconstruction and maintains iteration control
state. This allows for independent testing of the process that supports the GUI.
For this first version of interactive clean, we will consider :xref:`gclean` to be part of the
public API from CASA.

The public process API from CASA that interactive clean depend upon is :xref:`gclean` and
the :code:`shape`, :code:`maskhandler`, :code:`coordsys`, :code:`getregion`, :code:`fitsheader`,
:code:`getchunk`, :code:`putchunk` and :code:`statistics` functions of the :xref:`imagetool`.

gclean
^^^^^^^^^^^^^^^^

:xref:`gclean` is a Python class which encapsulates the process layer of interactive clean. It
allows for automated testing of all of the process interface of interactive clean as part of
the standard (non-interactive) testing of the process layer.

A :xref:`gclean` object is constructed with input parameters that are
relevant to interactive use. Once constructed,
:xref:`gclean` implements the `Python iterator protocol <https://docs.python.org/3/howto/functional.html#iterators>`_.
This means that it provides :code:`__next__` and :code:`__iter__` functions. The :code:`__next__` function
provides the functionality required for
`iterative image reconstruction <https://casadocs.readthedocs.io/en/stable/api/tt/casatasks.imaging.tclean.html#description>`_
using calls to :xref:`tclean` for the residual update step, calls to :xref:`deconvolve` for the
model update step, and methods to manage iteration control state and checks for global stopping
criteria.  Each time :code:`__next__` is (*indirectly*) called a new :xref:`returndict` is returned
which contains new state from one model update and one residual update along with the state from
previous :code:`__next__` calls. The :code:`__next__` function is not invoked directly but indirectly
as part of a loop::

  for imgdict in gclean(...):
      # loop body

or with an explicit iterator call via :code:`next(gclean_object)`. Iteration control state is
maintained as the :xref:`returndict` grows with each set of iteration blocks that are executed, and summarizes
the entire convergence history of the current imaging run. This :xref:`returndict` is returned to the GUI
and used to update the contents of the convergence plots and convergence state messages.

:xref:`gclean` deviates somewhat from the typical iterator object by also
including an :code:`update` function which accepts a dictionary of parameters to change for
the next generation step. These parameters are the modifications the user has indicated from
the interactive clean GUI.

The functions implemented within :xref:`gclean` are :

    :green:`construct gclean object` -- :code:`cl = gclean(...)` 
    The :xref:`gclean` object is
    constructed (with a subset of :xref:`tclean` parameters). Internal state is initialized,
    but no processing is done.

    :green:`run one set of iterations and retrieve the next convergence dictionary` -- :code:`next(cl)`
    One model update step (deconvolution) is run, followed by one residual update step (major cycle).
    For the initial call,
    only one residual update step is run.  Iteration control state is defined by user-supplied parameters
    of code:`niter`, code:`nmajor`, :code:`cycleniter` and :code:`threshold` and a series of ordered
    stopping criteria. The code:`next(cl)` function exits, and a dictionary returned after one major cycle
    is complete, after an error is encountered, or after global convergence criteria have been satisfied. The
    :code:`mask` which is provided specifies the area of the image cube to which the
    imaging algorithm should be applied. If the :code:`mask` contains all false or 0 values, no processing
    is performed.

    :green:`modifying iteration control setup` -- :code:`cl.update( {...} )`
    The purpose of
    interactive clean is to allow for adjustments to the :code:`mask` and control
    parameters as processing progresses. This adjustment can be done before each
    call to code:`next(cl)`. This update is optional and
    retrieving all dictionaries generated is expected to create the same final
    image as running :xref:`gclean` in a loop with no pauses in processing. The entries which
    can be supplied in the dictionary parameter are :code:`niter`, :code:`cycleniter`,
    :code:`niter`, :code:`nmajor`, :code:`threshold`, and :code:`cyclefactor`.
    :code:`update` returns a tuple composed of an error code and a message.
    The first element of the tuple (error code) is zero if the update was
    successful and negative one if the update failed. If the update failed,
    the message contains an error message. In addition to updating the loop
    parameters with :code:`update`, the mask image on disk may be modified
    directly.

    :green:`creating the restored image` -- :code:`cl.restore( )` called after the completion
    of the :xref:`gclean` processing. This creates the final, restored image and
    returns a dictionary which contains an :code:`image` field whose value is the
    path to the restored image.

The typical interactive clean pattern of :code:`gclean` usage is::

  cl = gclean( )
  retdict = next(cl)
  while user_continues( ):
      cl.update( user_parameters( ) )
      retdict = next(cl)
  cl.restore( )

where :code:`user_continues` enables interactive mask editing and then
checks whether the user wishes to stop and
:code:`user_parameters` fetches updates to the control parameters from the user.
:code:`retdict` is used to update convergence plots on the GUI.

The typical implementation of :code:`next(cl)` within :xref:`gclean` is as follows::

  if !has_converged(global_state):
      ret_mod = run_model_update()
      if ret_mod['iterdone']>0 :
         ret_res = run_residual_update()
         ret_dict = merge(ret_mod,ret_res)
         global_state.append(ret_dict)
  return read(global_state)

The interactive clean application currently being developed uses :xref:`tclean` for
run_residual_update() and :xref:`deconvolve` for run_model_update(), and implements
iteration control state and convergence checks using custom code within :xref:`gclean`.
These building blocks could (in the future) be replaced to implement alternate options
for the processing layer, as long as all the return dictionaries retain their structure.
