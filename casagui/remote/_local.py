'''Functions for local execution to create, tunnel, and connect to remote Jupyter kernels.'''
import jupyter_client
##>>>from ssh_ipykernel.kernel import SshKernel
##>>>from ipykernel import get_connection_info
from queue import Empty
import json
import os
import asyncio
import websockets
import time
from uuid import uuid4
from ast import literal_eval

'''Build ssh tunnel forwarding pattern and return list of arguments'''
def build_ssh_tunnel(host, ports, ip="localhost", verbose=False, quiet=True, ssh_config=""):
    # Build ssh command with all flags and tunnels
    # TODO: Handle non-matching remote and local ports
    ssh_tunnels = []
    for port in ports:
        ssh_tunnels += [
            "-L",
            "{local_port}:{ip}:{remote_port}".format(
                local_port=port,
                ip=ip,
                remote_port=port,
            ),
        ]

    if quiet:
        kernel_args = ["-q"]
    elif verbose:
        kernel_args = ["-v"]
    else:
        kernel_args = []

    kernel_args += ["-f", "-N", "-t"]
    if ssh_config != "":
        kernel_args += ["-F", str(ssh_config)]

    # Build rest of ssh command and redirect output
    kernel_args += ssh_tunnels + [host]
    ssh_tunnel_cmd = "ssh " + " ".join(kernel_args) + " &>/dev/null"

    return ssh_tunnel_cmd


'''Tunnel the necessary ports to access a remote jupyter kernel locally'''
def tunnel_remote_kernel(connect_info_file, host):
    connect_info_file_local = jupyter_client.find_connection_file(filename=connect_info_file)
    connect_info_local = json.loads(get_connection_info(connect_info_file_local))

    # Get ports to tunnel
    tunnel_ports = []
    for port_name in ['shell_port', 'iopub_port', 'stdin_port', 'control_port', 'hb_port']:
        tunnel_ports.append(connect_info_local[port_name])

    ssh_tunnel_cmd = build_ssh_tunnel(host, tunnel_ports)

    # # TODO: Check that command was successful
    os.system(ssh_tunnel_cmd)

'''Start a jupyter console connected to a remote kernel session in the current process'''
def connect_console(connect_info_file):
    console_start_cmd = "jupyter-console --existing=" + connect_info_file
    print("\nConsole start command:\n", console_start_cmd)
    os.system(console_start_cmd)

'''Start a remote jupyter kernel and return the full path to the connection info file'''
def start_remote_kernel(kernel_name, sudo=False, timeout=5, env="", backchannel_port=5667):
    # Get details of selected kernel (if exists)
    kern_spec_man = jupyter_client.kernelspec.KernelSpecManager()
    # TODO: Check that kernel name exists
    ic_kernel = kern_spec_man.get_kernel_spec(kernel_name)
    connect_info_file_local = ""

    connect_info_file_local = jupyter_client.find_connection_file()
    connect_info_local = json.loads(get_connection_info(connect_info_file_local))

    # Get remote connection info
    kernel_args = ic_kernel.argv
    host = kernel_args[kernel_args.index('--host') + 1]
    remote_python_path = kernel_args[kernel_args.index('--python') + 1]

    # Create remote kernel information structure
    kernel = SshKernel(host, connect_info_local, remote_python_path, sudo, timeout, env)
    kernel.create_remote_connection_info()

    # Build remote kernel launch command
    sudo = "sudo " if kernel.sudo else ""
    if kernel.env is not None:
        env = " ".join(kernel.env)
    kernel_start_cmd = "{sudo} {env} {python} -m ipykernel_launcher -f {fname}".format(
        sudo=sudo, env=env, python=kernel.python_full_path, fname=kernel.fname
    )

    # Build ssh command with all flags and tunnels
    tunnel_ports = [backchannel_port]
    for port_name in kernel.remote_ports.keys():
        tunnel_ports += [kernel.remote_ports[port_name]]

    ssh_tunnel_cmd = build_ssh_tunnel(host,
                                     tunnel_ports,
                                     verbose=kernel.verbose,
                                     quiet=kernel.quiet,
                                     ssh_config=kernel.ssh_config)
    # Create tunnels
    print("\nSSH Tunnel Command: \n", ssh_tunnel_cmd)
    ret = os.system(ssh_tunnel_cmd)
    # return kernel

    # Local connection info file location
    connect_info_file_local_full = os.path.abspath(connect_info_file_local)

    # Create and run command to start remote jupyter kernel
    remote_kernel_start_command = 'ssh {host} "nohup {cmd} >/dev/null 2>&1 &" &>/dev/null'.format(host=kernel.host, cmd=kernel_start_cmd)
    print("\nRemote Kernel Start Command: \n", remote_kernel_start_command)
    os.system(remote_kernel_start_command)

    # Copy the remote kernel connection file to local machine
    scp_cmd = "scp {host}:{fname} . &>/dev/null".format(host=kernel.host, fname=kernel.fname)
    print("\nSCP Command:\n", scp_cmd)
    os.system(scp_cmd)
    connect_info_file_local_full = os.path.abspath(kernel.fname[5:])

    tunnel_remote_kernel(connect_info_file_local_full, kernel.host)

    # Print command to attach
    console_start_cmd = "jupyter-console --existing=" + connect_info_file_local_full
    print("\nConsole start command:\n", console_start_cmd)
    os.system(ssh_tunnel_cmd)

    return connect_info_file_local_full


'''Connect to a remote Jupyter Kernel'''
def connect_remote(connect_info_file, host):
    kc = jupyter_client.BlockingKernelClient(connection_file = connect_info_file)
    kc.load_connection_file()
    # Start channels if connecting for the first time
    if(not kc.channels_running):
        kc.start_channels()

    # Unsure why this is the case
    try:
        kc.get_iopub_msg(timeout=1)
    except Empty:
        print("Empty IOPub Message Queue...")

    tunnel_remote_kernel(kc.connection_file, host)
    return kc

'''Print the waiting content of messages on the iopub channel.
Kernel responds to execution requests with potentially many responses.'''
def get_io_msgs(kc):
    state='busy'
    data={}
    while state!='idle' and kc.is_alive():
        try:
            msg=kc.get_iopub_msg(timeout=1)
            # print(msg)
            if not 'content' in msg:
                continue
            content = msg['content']
            print(content)
            # pretty_print_jupyter(content)
            if 'data' in content:
                data=content['data']
            if 'execution_state' in content:
                state=content['execution_state']
        except Empty:
            pass

'''Helper function for testing'''
def exe_and_print(kc, cmd):
    print("\nExecuting: {cmd}".format(cmd=cmd))
    kc.execute(cmd)
    get_io_msgs(kc)

'''Execute a command in a subprocess started from a remote Jupyter kernel'''
def exe_in_subproc(kc, cmd):
    # Generate a UUID associated with this command and subprocess instance
    id = str(uuid4())
    # Put UUID into command JSON
    cmd['id'] = id
    exe_and_print("run_subproc_cmd('" + json.dumps(cmd) + "')")
    return id

'''Helper function to send a remote request to a kernel's backchannel websocket'''
async def send_remote_request(request, backchannel_port):
    uri = "ws://localhost:"+str(backchannel_port)
    print("Remote request URI: " + uri)
    async with websockets.connect(uri, ping_interval=None) as websocket:
        await websocket.send(request)
        response = await websocket.recv()
        return response

'''Send a remote request to a kernel's backchannel websocket'''
def remote_request(request, port=5667):
    print("Sending remote request to port " + str(port) + " with request " + str(request))
    response = asyncio.get_event_loop().run_until_complete(send_remote_request(request, port))
    print(f"Response: {response}")

'''Convert arguments to an explicit, stringified representation for remote execution'''
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

'''Create a json representation of a remote subprocess command to execute'''
def create_cmd_json(cmd, *args, **kwargs):
    json_cmd = {}
    json_cmd['id'] = str(uuid4())
    json_cmd['cmd'] = cmd
    json_cmd['args'] = args
    json_cmd['kwargs'] = kwargs
    return json.dumps(json_cmd)

'''Execute a remote command in a subprocess'''
def exe_remote_subproc(kernel_client, json_cmd):
    json_cmd = json.loads(json_cmd)
    id = str(uuid4())
    json_cmd['id'] = id

    # TODO: Properly check output of subproc status
    # exe_and_print(kernel_client, "t.subproc_is_free()")
    # TODO: Figure out how to handle TestProc selection/naming/referencing
    exe_and_print(kernel_client, "t.add_subproc_cmd('"+str(json.dumps(json_cmd))+"')")
    return id

'''Properly print kernel-formatted'''
def pretty_print_jupyter(raw_out):
    if 'text' in raw_out:
        print(raw_out['text'])

    if 'data' in raw_out:
        data = raw_out['data']
        if 'text/plain' in data:
            print(data['text/plain'])

'''Get the returned value from remote kernel output'''
def get_return_val(kc):
    state='busy'
    data={}
    ret = None
    while state!='idle' and kc.is_alive():
        try:
            msg=kc.get_iopub_msg(timeout=1)
            # print(msg)
            if not 'content' in msg:
                continue
            content = msg['content']
            print(content)
            # pretty_print_jupyter(content)
            if 'data' in content:
                data=content['data']
                ret = literal_eval(data['text/plain'])
            if 'execution_state' in content:
                state=content['execution_state']
        except Empty:
            pass
    return ret

'''Get the returned value from a remote subprocess'''
def get_subproc_return_val(kc, id):
    wait_done(kc, id)
    kc.execute("t.get_return_val('" + id + "')")
    ret = get_return_val(kc)
    print("Return value: " + str(ret))
    return ret

'''Wait for the remote subprocess identified by 'id' to be finished'''
def wait_done(kc, id, interval=1):
    is_running = 1

    while is_running:
        kc.execute("t.is_running('" + id + "')")
        is_running = get_return_val(kc)
        print("Ret in wait done: " + str(is_running))
        time.sleep(interval)
