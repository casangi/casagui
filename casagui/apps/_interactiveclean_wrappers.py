from bokeh.models import TextInput, Checkbox
from ..utils import static_vars

###
### These wrappers allow the creation of a SINGLE GUI element that is shared across multiple
### tabs or panels.
###
### THESE FUNCTIONS MAY BE CALLED WITH NO ARGUMENTS TO RETRIEVE THE SINGLE SHARED WIDGET
###

###
### Functions for creating GUI element providing the tclean iteration parameters...
###
@static_vars(reuse=None)
def nmajor( *args, **kwargs ):
    if nmajor.reuse is None:
        if len(args) == 0 and len(kwargs) == 0:
            raise RuntimeError('No widget is available...')
        nmajor.reuse = TextInput( *args, **kwargs )
    return nmajor.reuse

@static_vars(reuse=None)
def niter( *args, **kwargs ):
    if niter.reuse is None:
        if len(args) == 0 and len(kwargs) == 0:
            raise RuntimeError('No widget is available...')
        niter.reuse = TextInput( *args, **kwargs )
    return niter.reuse

@static_vars(reuse=None)
def cycleniter( *args, **kwargs ):
    if cycleniter.reuse is None:
        if len(args) == 0 and len(kwargs) == 0:
            raise RuntimeError('No widget is available...')
        cycleniter.reuse = TextInput( *args, **kwargs )
    return cycleniter.reuse

@static_vars(reuse=None)
def threshold( *args, **kwargs ):
    if threshold.reuse is None:
        if len(args) == 0 and len(kwargs) == 0:
            raise RuntimeError('No widget is available...')
        threshold.reuse = TextInput( *args, **kwargs )
    return threshold.reuse

@static_vars(reuse=None)
def cyclefactor( *args, **kwargs ):
    if cyclefactor.reuse is None:
        if len(args) == 0 and len(kwargs) == 0:
            raise RuntimeError('No widget is available...')
        cyclefactor.reuse = TextInput( *args, **kwargs )
    return cyclefactor.reuse

@static_vars(reuse=None)
def gain( *args, **kwargs ):
    if gain.reuse is None:
        if len(args) == 0 and len(kwargs) == 0:
            raise RuntimeError('No widget is available...')
        gain.reuse = TextInput( *args, **kwargs )
    return gain.reuse

@static_vars(reuse=None)
def nsigma( *args, **kwargs ):
    if nsigma.reuse is None:
        if len(args) == 0 and len(kwargs) == 0:
            raise RuntimeError('No widget is available...')
        nsigma.reuse = TextInput( *args, **kwargs )
    return nsigma.reuse

###
### Wrappers providing GUI for auto-masking parameters...
###
@static_vars(reuse=None)
def noisethreshold( *args, **kwargs ):
    if noisethreshold.reuse is None:
        if len(args) == 0 and len(kwargs) == 0:
            raise RuntimeError('No widget is available...')
        noisethreshold.reuse = TextInput( *args, **kwargs )
    return noisethreshold.reuse

@static_vars(reuse=None)
def sidelobethreshold( *args, **kwargs ):
    if sidelobethreshold.reuse is None:
        if len(args) == 0 and len(kwargs) == 0:
            raise RuntimeError('No widget is available...')
        sidelobethreshold.reuse = TextInput( *args, **kwargs )
    return sidelobethreshold.reuse

@static_vars(reuse=None)
def lownoisethreshold( *args, **kwargs ):
    if lownoisethreshold.reuse is None:
        if len(args) == 0 and len(kwargs) == 0:
            raise RuntimeError('No widget is available...')
        lownoisethreshold.reuse = TextInput( *args, **kwargs )
    return lownoisethreshold.reuse

@static_vars(reuse=None)
def minbeamfrac( *args, **kwargs ):
    if minbeamfrac.reuse is None:
        if len(args) == 0 and len(kwargs) == 0:
            raise RuntimeError('No widget is available...')
        minbeamfrac.reuse = TextInput( *args, **kwargs )
    return minbeamfrac.reuse

@static_vars(reuse=None)
def negativethreshold( *args, **kwargs ):
    if negativethreshold.reuse is None:
        if len(args) == 0 and len(kwargs) == 0:
            raise RuntimeError('No widget is available...')
        negativethreshold.reuse = TextInput( *args, **kwargs )
    return negativethreshold.reuse

@static_vars(reuse=None)
def dogrowprune( *args, **kwargs ):
    if dogrowprune.reuse is None:
        if len(args) == 0 and len(kwargs) == 0:
            raise RuntimeError('No widget is available...')
        dogrowprune.reuse = Checkbox( *args, **kwargs )
    return dogrowprune.reuse
