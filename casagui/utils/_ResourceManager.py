import weakref
import atexit
import asyncio
import sys

from ._logging import get_logger
logger = get_logger()

class _ResourceManager:
    """ This class acts as a single place to manage the destruction of system
    resources (event_loops, ports, etc). To start with, get the singleton
    instance via

    import utils.resource_manager
    """
    def __init__(self):
        # A list of webservers to close when the event loop is closed.
        self.webservers_to_close = []
        self.reg_at_exit(self, 'stop_asyncio_loop')

    def reg_webserver(self, websockets_server):
        """ Register a webserver to be closed when the event loop is stopped. """
        self.webservers_to_close.append(weakref.ref(websockets_server))

    def reg_at_exit(self, obj_or_func=None, fname="", *vargs):
        """ Register a function or method to be called when python exits.
        @param obj_or_func An object containing a method fname, or a global/static function.
        @param fname If obj_or_func is an object instance, then this can be the method name
                     of the object to call.
        @param vargs Any extra parameters to pass to the obj_or_func or fname function.
        """
        if (fname == "" and callable(obj_or_func)):
            atexit.register(obj_or_func, *vargs)
        else:
            ref = weakref.ref(obj_or_func)
            atexit.register(self._call_on_ref, ref, fname, *vargs)

    def stop_asyncio_loop(self):
        """ Calls "stop" on the event_loop and closes any webservers registered
        with reg_webserver. """
        logger.debug("stop_asyncio_loop")
        try:
            event_loop = asyncio.get_running_loop()
            self._close_webservers(event_loop)
            event_loop.stop()
            return
        except RuntimeError:
            self._close_webservers(None)
            return

    def _close_webserver(self, server_weakref, event_loop=None):
        """ Close the given webserver. If event_loop != None, then use the loop
        to wait, blocking until the server has finished closing. """
        instance = server_weakref()
        if (instance == None):
            logger.debug("close_webserver(None)")
            return
        logger.debug(f"close_webserver({instance})")
        instance.close()
        if event_loop != None:
            event_loop.run_until_complete(instance.wait_closed())

    def _close_webservers(self, event_loop):
        """ Calls _close_webserver for each server registered with reg_webserver. """
        for webserver in self.webservers_to_close:
            self._close_webserver(webserver, event_loop)
        self.webservers_to_close.clear()

    def _call_on_ref(self, ref, fname, *vargs):
        """ Call the function named fname on the given object instance ref, aka:

        ref.fname(*vargs)
        """
        instance = ref()
        if instance == None:
            logger.debug('call_on_ref(None)')
            return
        if not hasattr(instance, fname):
            logger.debug(f"call_on_ref({instance.__class__.__name__}.{fname} == None)")
            return
        instance_method = getattr(instance, fname)
        if not callable(instance_method):
            logger.debug(f"call_on_ref(non-callable {instance.__class__.__name__}.{fname})")
            return
        logger.debug(f"{instance.__class__.__name__}.{fname}()")
        instance_method(*vargs)