### Remote gclean execution
import os
import sys
sys.path.insert(0, os.path.abspath('../'))
##>>>import casaremote

# Remote functions needed
# finalize, update(), reset

# TODO: How to handle dictionaries? """?
def kwarg_string(*args, **kwargs):
    ret = []
    for arg in args:
        if isinstance(arg, str):
            ret.append(f"'{arg}'")
        else:
            ret.append(f"{arg}")
    for key, value in kwargs.items():
        if isinstance(value, str):
            value = f"'{value}'"
        ret.append(f"{key}={value}")
    return ", ".join(ret)

class gclean_local:

    # def _tclean( self, *args, **kwargs ):
    #     return

    # def _deconvolve( self, *args, **kwargs ):
    #     return
    #     # return ( *args, **kwargs )

    def cmds( self ):
        cmd = casaremote.create_cmd_json("self.gclean_cmds")
        gclean_id = casaremote.exe_remote_subproc(self.kc, cmd)
        ret = casaremote.get_subproc_return_val(self.kc, gclean_id)
        return ret

    def __init__(self, kc, *args, **kwargs):
        self.kc = kc
        print("In remote clean init \n")
        cmd = "t._clean = gclean(" + kwarg_string(*args, **kwargs) + ")"
        casaremote.exe_and_print(kc, cmd)

    def __next__( self ):
        cmd = casaremote.create_cmd_json("self.gclean_next")
        gclean_id = casaremote.exe_remote_subproc(self.kc, cmd)
        ret = casaremote.get_subproc_return_val(self.kc, gclean_id)
        return ret

    def restore(self):
        cmd = casaremote.create_cmd_json("self.gclean_restore")
        gclean_id = casaremote.exe_remote_subproc(self.kc, cmd)
        ret = casaremote.get_subproc_return_val(self.kc, gclean_id)
        return ret

    def has_next(self):
        cmd = casaremote.create_cmd_json("self.gclean_has_next")
        gclean_id = casaremote.exe_remote_subproc(self.kc, cmd)
        ret = casaremote.get_subproc_return_val(self.kc, gclean_id)
        return ret
