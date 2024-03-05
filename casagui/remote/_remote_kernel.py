# Functions for long-running process running in a remote jupyter kernel

from multiprocessing import Process, Pipe
import sys
import os
import json
from time import sleep
from websockets.server import serve
import asyncio

class TestProc:
    _backchannel_task = None # Maintain strong reference to backchannel task

    def __init__(self, port, loop):
        self.loop = loop
        self.port = port
        self.subproc_cmd_pend = []

    async def echo(self, websocket):
        async for message in websocket:
            response = json.dumps({"request": message, "response": eval("self."+message)})
            await websocket.send(response)

    async def backchannel_process(self, port):
        async with serve(self.echo, "localhost", port, ping_interval=None):
            await asyncio.Future()  # run forever

    def start_backchannel(self):
        assert self.loop.is_running()
        self._backchannel_task = asyncio.create_task(self.backchannel_process(self.port))
        return

    '''Check subprocess command to see if it's free (1) or busy (0)'''
    def subproc_is_free(self):
        if len(self.subproc_cmd_pend) == 0:
            return 1

        if any(process[1].is_alive() for process in self.subproc_cmd_pend):
            print("Busy")
            sleep(1)
            return 0
        else:
            print('All processes done')
            return 1

    def add_subproc_cmd(self, cmd_json_str):
        # Check that a subprocess isn't currently running
        if not self.subproc_is_free():
            print("Error: Subprocess is still running. Cannot start new process.")
            return -1

        print(cmd_json_str)
        cmd_json = json.loads(cmd_json_str)
        parent_conn, child_conn = Pipe()
        p = Process(target=eval(cmd_json['cmd']),
                    args=(child_conn,) + tuple(cmd_json['args']),
                    kwargs=cmd_json['kwargs'])

        subproc_details = (cmd_json['id'], p, parent_conn)
        self.subproc_cmd_pend.append(subproc_details)
        p.start()
        return

    # Return the requested process' (identified by the UUID) return value
    def get_return_val(self, id):
        # Check that id is valid
        for process in self.subproc_cmd_pend:
            if id == process[0]:
                print("placeholder")
                # Check that process is done
                # TODO

                # Check parent connection for waiting message
                # ret_obj = process[3].recv() ???

                # Check that ret_obj valid and that didn't timeout
                # return ret_obj

        # Else return ID not found
        return
