"""Demonstration of Interactive Clean running remotely, starting a remote webserver, and
the generated GUI shown locally automatically."""
import os
import sys
sys.path.insert(0, os.path.abspath('./'))
import casaremote
from casagui.utils import find_ws_address

# This is the name of an 'ssh_ipykernel' remote jupyter kernel on your local machine
# See https://pypi.org/project/ssh-ipykernel/ for more details on creating this
remote_jupyter_kernel_name = ""

# Start the remote jupyter kernel and initialize the environment
_, backchannel_port = find_ws_address("localhost")
connect_info_file = casaremote.start_remote_kernel(remote_jupyter_kernel_name, False, backchannel_port=backchannel_port)
kc = casaremote.connect_remote(connect_info_file, "zuul07")

# Initialize the remote kernel environment for Interactive Clean
# TODO: Move this into its own initialization function? Or keep it more explicit here
casaremote.exe_and_print(kc, "import casagui")
casaremote.exe_and_print(kc, "from casagui.apps import InteractiveClean")
casaremote.exe_and_print(kc, "import casaremote")
casaremote.exe_and_print(kc, "import asyncio")
casaremote.exe_and_print(kc, "t = casaremote.TestProc(" + str(backchannel_port)+", asyncio.get_running_loop())")
casaremote.exe_and_print(kc, "t.ic = None")

# Create TestProc object in top-level scope
casaremote.exe_and_print(kc, "t = casaremote.TestProc(" + str(backchannel_port)+", asyncio.get_running_loop())")
casaremote.exe_and_print(kc, "t.start_backchannel()")

# Initialize the remote Interactive Clean instance
ms_path = 'refim_point_withline.ms'
img = 'test'

def init_ic(kc, *args, **kwargs):
    delete_cmd = "os.system('rm -rf + " + kwargs['imagename'] + ".* *.html *.log')"
    casaremote.exe_and_print(kc, delete_cmd)
    cmd = "t.ic = InteractiveClean(" + casaremote.kwarg_string(*args, **kwargs) + ")"
    casaremote.exe_and_print(kc, cmd)

init_ic(kc,
        remote=True,
        serve_webpage=True,
        vis=ms_path,
        imagename=img,
        imsize=512,
        cell='12.0arcsec',
        specmode='cube',
        interpolation='nearest',
        nchan=5,
        start='1.0GHz',
        width='0.2GHz',
        pblimit=-1e-05,
        deconvolver='hogbom',
        threshold='0.001Jy',
        niter=50,
        cycleniter=10,
        cyclefactor=3,
        scales=[0,3,10] )

# Start Interactive Clean remotely
casaremote.exe_and_print(kc, "result = t.ic()")

print("Reconnection info file: ", connect_info_file)

# Query ports, auto port-forward, and open webpage
port_cmd = casaremote.create_cmd_json("self.get_ports")
port_cmd_id = casaremote.exe_remote_subproc(kc, port_cmd)
ports = casaremote.get_subproc_return_val(kc, port_cmd_id)
ssh_cmd = casaremote.build_ssh_tunnel("zuul07", ports)

print("Tunneling connections: " + ssh_cmd)
os.system(ssh_cmd)
os.system("open http://127.0.0.1:" + str(ports[-1]))

input("Press enter to exit")