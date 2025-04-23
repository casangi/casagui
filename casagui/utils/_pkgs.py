import os
import sys
import importlib.util
from os.path import join, exists, realpath

def find_pkg( name, extra_dirs=[] ):
    """
    Returns list of paths which contain the ``name`` pkg. It is assumed that the
    ``name`` will be the name of a directory (containing the package) or that
    ``name.py(c)`` will be a file that exists. This does not attempt to import the
    package.

    Parameters
    ----------
    name: string
        the name of the package in python "dot" notation to be searched for
    extra_dirs: list of strings
        directories to be searched in addition to those included in ``sys.path``

    Returns
    -------
    list of import specifications
        specifications of ``name`` found by search ``sys.path`` and ``extra_dirs``
    """
    result = [ ]
    filename = (name.split('.'))
    for dir in sys.path[:] + extra_dirs:
        path = join( dir, *filename )
        if exists(path):
            spec = importlib.util.spec_from_file_location(name,path)
            if spec:
                result.append(spec)
        else:
            path = f"{path}.py"
            if exists(path):
                spec = importlib.util.spec_from_file_location(name,path)
                if spec:
                    result.append(spec)
            else:
                path = f"{path}c"
                if exists(path):
                    spec = importlib.util.spec_from_file_location(name,path)
                    if spec:
                        result.append(spec)
    return result

def load_pkg( spec ):
    """
    Loads and returns the module specified by ``spec`` (e.g. as returned from ``find_pkg``)
    If ``spec.name`` does not already exist in ``sys.modules``, it is added.

    Parameters
    ----------
    spec: ModuleSpec
        the module to be loaded

    Returns
    -------
    module
        the loaded module
    """

    import _frozen_importlib
    if not isinstance(spec,_frozen_importlib.ModuleSpec):
        raise ImportError(f"Expected ModuleSpec instead of {type(spec)}")

    pkg = importlib.util.module_from_spec(spec)

    try:
        spec.loader.exec_module(pkg)
    except:
        raise ImportError(f"Could not load {spec.origin}")

    if spec.name not in sys.modules:
        sys.modules[spec.name] = pkg

    return pkg
