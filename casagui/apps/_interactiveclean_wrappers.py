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
class SharedWidgets:
    def __init__( self ):
        self._nmajor = None
        self._niter = None
        self._cycleniter = None
        self._threshold = None
        self._cyclefactor = None
        self._gain = None
        self._nsigma = None
        self._noisethreshold = None
        self._sidelobethreshold = None
        self._lownoisethreshold = None
        self._minbeamfrac = None
        self._negativethreshold = None
        self._dogrowprune = None
        self._fastnoise = None

    def nmajor( self, *args, **kwargs ):
        if self._nmajor is None:
            if len(args) == 0 and len(kwargs) == 0:
                raise RuntimeError('No widget is available...')
            self._nmajor = TextInput( *args, **kwargs )
        return self._nmajor

    def niter( self, *args, **kwargs ):
        if self._niter is None:
            if len(args) == 0 and len(kwargs) == 0:
                raise RuntimeError('No widget is available...')
            self._niter = TextInput( *args, **kwargs )
        return self._niter

    def cycleniter( self, *args, **kwargs ):
        if self._cycleniter is None:
            if len(args) == 0 and len(kwargs) == 0:
                raise RuntimeError('No widget is available...')
            self._cycleniter = TextInput( *args, **kwargs )
        return self._cycleniter

    def threshold( self, *args, **kwargs ):
        if self._threshold is None:
            if len(args) == 0 and len(kwargs) == 0:
                raise RuntimeError('No widget is available...')
            self._threshold = TextInput( *args, **kwargs )
        return self._threshold

    def cyclefactor( self, *args, **kwargs ):
        if self._cyclefactor is None:
            if len(args) == 0 and len(kwargs) == 0:
                raise RuntimeError('No widget is available...')
            self._cyclefactor = TextInput( *args, **kwargs )
        return self._cyclefactor

    def gain( self, *args, **kwargs ):
        if self._gain is None:
            if len(args) == 0 and len(kwargs) == 0:
                raise RuntimeError('No widget is available...')
            self._gain = TextInput( *args, **kwargs )
        return self._gain

    def nsigma( self, *args, **kwargs ):
        if self._nsigma is None:
            if len(args) == 0 and len(kwargs) == 0:
                raise RuntimeError('No widget is available...')
            self._nsigma = TextInput( *args, **kwargs )
        return self._nsigma

    ###
    ### Wrappers providing GUI for auto-masking parameters...
    ###
    def noisethreshold( self, *args, **kwargs ):
        if self._noisethreshold is None:
            if len(args) == 0 and len(kwargs) == 0:
                raise RuntimeError('No widget is available...')
            self._noisethreshold = TextInput( *args, **kwargs )
        return self._noisethreshold

    def sidelobethreshold( self, *args, **kwargs ):
        if self._sidelobethreshold is None:
            if len(args) == 0 and len(kwargs) == 0:
                raise RuntimeError('No widget is available...')
            self._sidelobethreshold = TextInput( *args, **kwargs )
        return self._sidelobethreshold

    def lownoisethreshold( self, *args, **kwargs ):
        if self._lownoisethreshold is None:
            if len(args) == 0 and len(kwargs) == 0:
                raise RuntimeError('No widget is available...')
            self._lownoisethreshold = TextInput( *args, **kwargs )
        return self._lownoisethreshold

    def minbeamfrac( self, *args, **kwargs ):
        if self._minbeamfrac is None:
            if len(args) == 0 and len(kwargs) == 0:
                raise RuntimeError('No widget is available...')
            self._minbeamfrac = TextInput( *args, **kwargs )
        return self._minbeamfrac

    def negativethreshold( self, *args, **kwargs ):
        if self._negativethreshold is None:
            if len(args) == 0 and len(kwargs) == 0:
                raise RuntimeError('No widget is available...')
            self._negativethreshold = TextInput( *args, **kwargs )
        return self._negativethreshold

    def dogrowprune( self, *args, **kwargs ):
        if self._dogrowprune is None:
            if len(args) == 0 and len(kwargs) == 0:
                raise RuntimeError('No widget is available...')
            self._dogrowprune = Checkbox( *args, **kwargs )
        return self._dogrowprune

    def fastnoise( self, *args, **kwargs ):
        if self._fastnoise is None:
            if len(args) == 0 and len(kwargs) == 0:
                raise RuntimeError('No widget is available...')
            self._fastnoise = Checkbox( *args, **kwargs )
        return self._fastnoise
