# casagui C/C++ Development

This page describes the use of [Anaconda](https://www.anaconda.com/) for C/C++ development. Anaconda can be used for creating *sandbox development environments* for Linux, macOS and (perhaps) Windows. It should be usable for the [Qt](https://www.qt.io/) GUIs:

*  [CASAfeather](https://open-bitbucket.nrao.edu/projects/CASA/repos/casafeather/browse)
*  [CASAtablebrowser](https://open-bitbucket.nrao.edu/projects/CASA/repos/casatablebrowser/browse)
*  [CASAlogger](https://open-bitbucket.nrao.edu/projects/CASA/repos/casalogger/browse)
*  [CASAplotms](https://open-bitbucket.nrao.edu/projects/CASA/repos/casaplotms/browse)
*  [CASAplotserver](https://open-bitbucket.nrao.edu/projects/CASA/repos/casaplotserver/browse)
*  [CASAviewer](https://open-bitbucket.nrao.edu/projects/CASA/repos/casaviewer/browse)

It should also be possible to build the standard [CASA 6](https://casadocs.readthedocs.io/en/latest/) components, [casatools](https://open-bitbucket.nrao.edu/projects/CASA/repos/casa6/browse/casatools) and [casatasks](https://open-bitbucket.nrao.edu/projects/CASA/repos/casa6/browse/casatasks). Beyond CASA, the expectation is that Anaconda can also be used to build the [CARTA backend](https://github.com/CARTAvis/carta-backend), but this has not yet been tested.

# Installing and Environments

Instructions for installing Anaconda are [readily avilable](https://docs.anaconda.com/anaconda/install/index.html) online. Anaconda has a number of tools for dealing with environments. In particular, it is easy to export the environment configuration:

```
bash$ conda env export > myenvironment.yml
```
This environment can then be reconstructed with:
```
bash$ conda create -n my-new-environment -f myenvironment.yml
```
This will create a new Anaconda environment called `my-new-environment` using the `myenvironment.yml` environment file. This is how environments files for building `casatools` etc. were created. If you **just** want to create a duplicate environment, you can do that with:

```
bash$ conda create --name test --clone my-new-environment
```
This will create another environment that is identical to the `my-new-environment` conda environment. It is important to remember that these environment files are generally operating system specfic and lack a mechanism to support multiple OSes.

# Using CASA Environments

## Environment

Building portions of CASA are supported by Anaconda environment files (this will be filled out as experience mounts):

| Software | macos | rhel8 | Notes |
| --- | --- | --- | --- |
| casatools | [casa6-macos.yml](casa6-macos.yml) | [casa6-linux.yml](casa6-linux.yml) | does not include openmpi |
| casatools + openmpi | [casa6-mpi-macos.yml](casa6-mpi-macos.yml) | [casa6-mpi-linux.yml](casa6-mpi-linux) | includes openmpi ( libmpi_cxx does not seem to be available and does not seem to be needed) |
| casatablebrowser | [qt4-macos.yml](qt4-macos.yml) | | should **not** be built with openmpi |

