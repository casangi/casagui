from __future__ import absolute_import


def setup_session():
    from bokeh.io import output_notebook

    session_settings = {
        "ZMQInteractiveShell": "Running in a Jupyter notebook",
        "TerminalInteractiveShell": "Running in a terminal",
    }
    try:
        session = get_ipython().__class__.__name__
    except NameError:
        session = "Unknown"

    if session == "ZMQInteractiveShell":
        output_notebook()


__all__ = ["plotants", "plotbandpass"]
from .plotants import plotants
from .plotbandpass import plotbandpass

setup_session()
