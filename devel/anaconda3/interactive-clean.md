# Interactive Clean

This document describes setting up interactive clean.

## Setup with ``casatools`` Builds

If you need to build ``casatools`` use these instructions:

1. [Install Anaconda](https://www.anaconda.com/) if it is not already installed (check by running ``conda --version``)
1. Setup a casatools build environment using either the [macos or linux build environment file](https://github.com/casangi/casagui/blob/main/devel/anaconda3/c_dev.md#environment) (_first row of table_)
    ```
    bash$ conda env create -f ../casa6-linux.yml
    ```
1. Switch anaconda to not automatically activate the base environment (_unless you would prefer to have anaconda activated upon login_)
    ```
    bash$ conda config --set auto_activate_base false
    ```
1. Open a new shell and activate casatools environment
    ```
    bash$ conda activate casa6-linux
    ```
1. Clone casa6 repository with ``git clone --recursive https://open-bitbucket.nrao.edu/scm/casa/casa6``
1. Build casatools with:
    ```
    bash$ cd casa6/casatools
    bash$ git checkout CAS-6692
    bash$ git submodule update casacore
    bash$ (autoconf && ./configure --enable-system-grpc && ./setup.py --debug bdist_wheel ) 2>&1 | tee build.log.001
    ```
1. Build casatasks with (_library directory may vary_):
    ```
    bash$ cd ../casatasks
    bash$ PYTHONPATH=../casatools/build/lib.linux-x86_64-3.8 ./setup.py bdist_wheel
    ```
1. Checkout casagui
    ```
    bash$ cd ../..
    bash$ git clone https://github.com/casangi/casagui
    ```
1. Install Bokeh, Websockets and Requests --
    (_requests only used by ``casagui/utils.py`` so maybe it should be substituted by something else..._)
    ```
    bash$ conda install -c conda-forge 'bokeh>=2.4.0'
    bash$ conda install -c conda-forge matplotlib
    bash$ conda install -c conda-forge scipy
    bash$ conda install -c conda-forge websockets
    bash$ conda install -c anaconda requests
    ```
1. Run Interactive Clean Demo
    ```
    bash$ cd casagui/tests/manual/iclean-demo
    bash$ PYTHONPATH=../../../casagui python3 ./run-iclean.py
    ```

## Notes

1. I had to fetch the test MS by hand from the unix command line, ``wget https://casa.nrao.edu/download/devel/casavis/data/refim_point_withline-ms.tar.gz``. I don't know what goes wrong in the ``run-iclean.py`` code which **should** fetch it.

1. Bokeh does **not** work with the _Konqueror_ browser
