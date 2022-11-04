###
###  This script was created to test loading larger cubes. This dataset was
###  suggested even though it turned out to just produce 512x512 image planes
###
#from casagui.bokeh.state import initialize_bokeh
#initialize_bokeh( "../../../casalib/dist/esbuild/casalib-v0.0.1.min.js",
#                  "../../../casaguijs/dist/casaguijs.js" )                        ### local build
#initialize_bokeh( "../../../casalib/dist/esbuild/casalib-v0.0.2.min.js" )
#
#initialize_bokeh( bokeh='../../../casaguijs/dist/casaguijs.js' )                   ### local gui/js build + standard bokeh independent library

import os
import ssl
import certifi
import asyncio
import urllib
import tarfile

from casagui.apps import InteractiveClean, MaskMode

##
## demo measurement set to use
##
ms_path = 'sim_data_VLA_jet.ms'
##
## where to fetch the demo measurement set
##
ms_url = "https://casa.nrao.edu/download/devel/casavis/data/ms-vla-sim-jet.tar.gz"
##
## output image file name
##
img = 'test'

if not os.path.isdir(ms_path):
    try:
        context = ssl.create_default_context(cafile=certifi.where())
        tstream = urllib.request.urlopen(ms_url, context=context, timeout=400)
        tar = tarfile.open(fileobj=tstream, mode="r:gz")
        tar.extractall( )
    except urllib.error.URLError:
        print("Failed to open connection to "+ms_url)
        raise

if not os.path.isdir(ms_path):
    raise  RuntimeError("Failed to fetch measurement set")

###
### test runs from test_stk_alma_pipeline_imaging.py
### with alma-sf-E2E6-1-00034-S.tar.gz
### ------------------------------------------------------------------------------------------------------------------------
### measurement set:	/home/casa/data/casatestdata/stakeholder/alma/E2E6.1.00034.S_tclean.ms
### iter0		vis='/home/casa/data/casatestdata/stakeholder/alma/E2E6.1.00034.S_tclean.ms', imagename='standard_cube.iter0', field='1', spw=['0'], imsize=[80, 80], antenna=['0,1,2,3,4,5,6,7,8'], scan=['8,12,16'], intent='OBSERVE_TARGET#ON_SOURCE', datacolumn='data', cell=['1.1arcsec'], phasecenter='ICRS 00:45:54.3836 -073.15.29.413', stokes='I', specmode='cube', nchan=508, start='220.2526743594GHz', width='0.2441741MHz', outframe='LSRK', pblimit=0.2, perchanweightdensity=False, gridder='standard', mosweight=False, deconvolver='hogbom', usepointing=False, restoration=False, pbcor=False, weighting='briggs', restoringbeam='common', robust=0.5, npixels=0, niter=0, threshold='0.0mJy', nsigma=0.0, interactive=0, usemask='auto-multithresh', sidelobethreshold=1.25, noisethreshold=5.0, lownoisethreshold=2.0, negativethreshold=0.0, minbeamfrac=0.1, growiterations=75, dogrowprune=True, minpercentchange=1.0, fastnoise=False, savemodel='none', parallel=False, verbose=True
### iterN		vis='/home/casa/data/casatestdata/stakeholder/alma/E2E6.1.00034.S_tclean.ms', imagename='standard_cube.iter1', field='1', spw=['0'], imsize=[80, 80], antenna=['0,1,2,3,4,5,6,7,8'], scan=['8,12,16'], intent='OBSERVE_TARGET#ON_SOURCE', datacolumn='data', cell=['1.1arcsec'], phasecenter='ICRS 00:45:54.3836 -073.15.29.413', stokes='I', specmode='cube', nchan=508, start='220.2526743594GHz', width='0.2441741MHz', outframe='LSRK', perchanweightdensity=False, usepointing=False, pblimit=0.2, nsigma=0.0, gridder='standard', mosweight=False, deconvolver='hogbom', restoringbeam='common', restoration=True, pbcor=True, weighting='briggs', robust=0.5, npixels=0, niter=20000, threshold='0.354Jy', interactive=0, usemask='auto-multithresh', sidelobethreshold=1.25, noisethreshold=5.0, lownoisethreshold=2.0, negativethreshold=0.0, minbeamfrac=0.1, growiterations=75, dogrowprune=True, minpercentchange=1.0, fastnoise=False, restart=True, calcres=False, calcpsf=False, savemodel='none', parallel=False, verbose=True
### ------------------------------------------------------------------------------------------------------------------------
###
### test from CAS-13924
### with vla-sim-jet.tar.gz
### ------------------------------------------------------------------------------------------------------------------------
### import numpy as np
### os.environ["USE_SMALL_SUMMARYMINOR"]="true"    #### or "false".  Default is "false" for 'casa' and "true" for mpicasa.
### os.system('rm -rf try_cube_hogbom.*')
### vis = '/home/casa/data/casatestdata/unittest/tclean/sim_data_VLA_jet.ms'
### rec = tclean( vis=vis,imagename='try_cube_hogbom',imsize=512,cell='12.0arcsec',
###               specmode='cube',interpolation='nearest',nchan=5,start='1.0GHz',width='0.2GHz',
###               pblimit=-1e-05,deconvolver='hogbom',niter=10000, gain=0.2, 
###               interactive=0,mask='circle[[256pix,256pix],150pix]' )
### np.save('try_cube_hogbom.summary.npy', rec) 
### ------------------------------------------------------------------------------------------------------------------------
###

ic = InteractiveClean( vis=ms_path, imagename=img,
                       imsize=512,
                       cell='12.0arcsec',
                       specmode='cube',
                       interpolation='nearest',
                       nchan=5,
                       start='1.0GHz',
                       width='0.2GHz',
                       pblimit=-1e-05,
                       deconvolver='hogbom',
                       niter=10000,
                       gain=0.2,
                       mask=MaskMode.AUTOMT )

if True:
    print( "Result: %s" % ic( ) )
    print( " Masks: %s" % repr(ic.masks( )) )
else:
    try:
        asyncio.get_event_loop().run_until_complete(ic.show( ))
        asyncio.get_event_loop().run_forever()

    except KeyboardInterrupt:
        print('\nInterrupt received, shutting down ...')
        #os.system('rm -rf {output_image}.* *.html *.log'.format(output_image=output_image))

    print( "Result: %s" % repr(ic.result( )) )
    print( " Masks: %s" % repr(ic.masks( )) )
