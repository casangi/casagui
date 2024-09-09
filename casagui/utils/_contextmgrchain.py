import asyncio
import logging
import sys

from functools import wraps

###
### from: https://stackoverflow.com/a/38730848
###
class ContextMgrChain(object):

    def __init__(self, *managers):
        self.managers = managers
        self.stack = []
        self.values = []

    async def push(self, manager):
        try:
            if hasattr(manager, '__aenter__'):
                value = await manager.__aenter__()
            else:
                value = manager.__enter__()

            self.stack.append(manager)
            self.values.append(value)
            return value
        except:
            # if we encounter an exception somewhere along our enters,
            # we'll stop adding to the stack, and pop everything we've
            # added so far, to simulate what would happen when an inner
            # block raised an exception.
            swallow = await self.__aexit__(*sys.exc_info())
            if not swallow:
                raise

    async def __aenter__(self):
        value = None

        for manager in self.managers:
            value = await self.push(manager)

        return value

    async def __aexit__(self, exc_type, exc, tb):
        excChanged = False
        swallow = False # default value
        while self.stack:
            # no matter what the outcome, we want to attempt to call __aexit__ on
            # all context managers
            try:
                swallow = await self._pop(exc_type, exc, tb)
                if swallow:
                    # if we swallow an exception on an inner cm, outer cms would
                    # not receive it at all...
                    exc_type = None
                    exc = None
                    tb = None
            except:
                # if we encounter an exception while exiting, that is the
                # new execption we send upward
                excChanged = True
                (exc_type, exc, tb) = sys.exc_info()
                swallow = False

        if exc is None:
            # when we make it to the end, if exc is None, it was swallowed
            # somewhere along the line, and we've exited everything successfully,
            # so tell python to swallow the exception for real
            return True
        elif excChanged:
            # if the exception has been changed, we need to raise it here
            # because otherwise python will just raise the original exception
            if not swallow:
                raise exc
        else:
            # we have the original exception still, we just let python handle it...
            return swallow

    async def _pop(self, exc_type, exc, tb):
        manager = self.stack.pop()
        if hasattr(manager, '__aexit__'):
            return await manager.__aexit__(exc_type, exc, tb)
        else:
            return manager.__exit__(exc_type, exc, tb)
