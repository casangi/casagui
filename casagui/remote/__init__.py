'''Remote Jupyter kernel execution capabilities. These are the dependencies that **may** be installed::

    Successfully installed Send2Trash-1.8.2 anyio-3.7.1 argon2-cffi-23.1.0 argon2-cffi-bindings-21.2.0 babel-2.14.0 beautifulsoup4-4.12.3 bleach-6.1.0 cffi-1.16.0 charset-normalizer-3.3.2 comm-0.2.1 debugpy-1.8.1 defusedxml-0.7.1 deprecation-2.1.0 fastjsonschema-2.19.1 ipykernel-6.29.3 ipython-genutils-0.2.0 json5-0.9.20 jsonschema-4.21.1 jsonschema-specifications-2023.12.1 jupyter-client-6.1.12 jupyter-core-5.7.1 jupyter-packaging-0.12.3 jupyter-server-1.24.0 jupyterlab-3.0.18 jupyterlab-pygments-0.3.0 jupyterlab-server-2.25.3 mistune-3.0.2 nbclassic-0.5.6 nbclient-0.9.0 nbconvert-7.16.2 nbformat-5.9.2 nest-asyncio-1.6.0 notebook-shim-0.2.4 pandocfilters-1.5.1 platformdirs-4.2.0 prometheus-client-0.20.0 psutil-5.9.8 pycparser-2.21 pyzmq-25.1.2 referencing-0.33.0 requests-2.31.0 rpds-py-0.18.0 sniffio-1.3.1 soupsieve-2.5 ssh-ipykernel-interrupt-1.1.2 ssh_ipykernel-1.2.3 terminado-0.18.0 tinycss2-1.2.1 tomlkit-0.12.4 tornado-6.2 urllib3-2.2.1 webencodings-0.5.1 websocket-client-1.7.0

when installing ssh_ipykernel.
'''

from ._local import *
from ._remote_kernel import TestProc
from ._gclean import gclean_local
