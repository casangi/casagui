# Python Package for CASAGUI

This directory contains the _Python_ package implementation for `casagui`.
`casagui` is the visualization front end for the CASA package. The important
thing to understand is that this _Python_ package is designed to be used
in three very different contexts.

## End User

This group of users includes other CASA developers who use _Python_ as well
as _modular CASA_ users. These users will install this package
(often) using _PyPI_ and will import it like:
```
bash$ ipython
Python 3.8.10 (default, Jun 15 2021, 04:49:06) 
Type 'copyright', 'credits' or 'license' for more information
IPython 7.24.1 -- An enhanced Interactive Python. Type '?' for help.

In [1]: import casagui
```
In this usage mode, the visualization elements will appear as a tab in
the user's web browser.

## CASA Application

In the future there will be a CASA application built using Electron. This
application will be based upon `ipykernel` (the Jupyter Notebook kernel
for Python) and this application will import `casagui` to create the
key visualization elements (from _Python_) for display in the desktop,
Electron App.

## Notebook Users

The goal is that _Jupyter Notebook_ cells can import `casagui` and the
key visualization elements will appear, in place, in the notebook.
