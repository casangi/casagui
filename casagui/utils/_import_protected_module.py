import inspect
import importlib
import sys
import types

def ImportProtectedModule( name, file_mapping ):

    class module_import(types.ModuleType):
        """Import objects, functions and classes for export while avoiding requiring user to
           provide the sub-package name for the file contining the imported object, for example
           allowing:
                         from casagui.apps import iclean

           instead of:
                         from casagui.app._interactive_clean import iclean

           while also not importing '_interactive_clean' (inside of __init__.py) regardless of
           whether the user actually import 'iclean' or not. This is done to allow for some
           dependencies to not be available but for the imports to still work as long as
           the dependencies which are needed for the imported classes are available.
        """

        _module = name
        _mapping = file_mapping

        def __getattr__(self, name):
            if name in self._mapping:
                m = importlib.import_module(self._mapping[name], self._module)  # import submodule
                o = getattr(m, name)                                            # find the required member
                setattr(sys.modules[self._module], name, o)                     # bind it into the package
                return o
            else:
                raise AttributeError(f'module {__name__} has no attribute {name}')

    return module_import
