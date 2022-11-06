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
import sys
import ssl
import certifi
import asyncio
import urllib
import tarfile

from casagui.apps import InteractiveClean, MaskMode

##
## demo measurement set to use
##
ms_path = [ f'2017.1.00661.S/{ms}' for ms in
            [ 'uid___A002_Xc8d560_X66fa_targets_line.ms',
              'uid___A002_Xc91189_X2368_targets_line.ms',
              'uid___A002_Xca525b_X14d6_targets_line.ms',
              'uid___A002_Xca6c94_X4b26_targets_line.ms',
              'uid___A002_Xca6c94_X5376_targets_line.ms',
              'uid___A002_Xcb4a8e_X3734_targets_line.ms',
              'uid___A002_Xcc8b19_X3283_targets_line.ms',
              'uid___A002_Xcc8b19_X7d1b_targets_line.ms' ] ]
##
## where to fetch the demo measurement set
##
ms_url = "https://casa.nrao.edu/download/devel/casavis/data/ms-alma-many-chan-2017_1_00661_S.tar.gz"
##
## output image file name
##
img = 'test'

if not all( map( os.path.isdir, ms_path ) ):
    try:
        response = input('MS is not available, download will be 18GB continue? [Y/N] ')
        while response.lower( ) not in [ 'y', 'n' ]:
            response = input('MS is not available, download will be 18GB continue? [Y/N] ')
        if response.lower( ) == 'y':
            context = ssl.create_default_context(cafile=certifi.where())
            tstream = urllib.request.urlopen(ms_url, context=context, timeout=400)
            tar = tarfile.open(fileobj=tstream, mode="r:gz")
            tar.extractall( )
        else:
            sys.exit("MS not available")
    except urllib.error.URLError:
        print("Failed to open connection to "+ms_url)
        raise

if not all( map( os.path.isdir, ms_path ) ):
    raise  RuntimeError("Failed to fetch measurement set")

###
### https://open-jira.nrao.edu/browse/CAS-13924?focusedCommentId=200087&page=com.atlassian.jira.plugin.system.issuetabpanels%3Acomment-tabpanel#comment-200087
###
### ------------------------------------------------------------------------------------------------------------------------
### tclean(vis=['uid___A002_Xc8d560_X66fa_targets_line.ms', 'uid___A002_Xc91189_X2368_targets_line.ms', 'uid___A002_Xca525b_X14d6_targets_line.ms', 'uid___A002_Xca6c94_X4b26_targets_line.ms', 'uid___A002_Xca6c94_X5376_targets_line.ms', 'uid___A002_Xcb4a8e_X3734_targets_line.ms', 'uid___A002_Xcc8b19_X3283_targets_line.ms', 'uid___A002_Xcc8b19_X7d1b_targets_line.ms'], field='NGC6334I', spw=['16', '16', '16', '16', '16', '16', '16', '16'], antenna=['0,1,2,3,4,5,6,7,8,9,10&', '0,1,2,3,4,5,6,7,8,9,10&', '0,1,2,3,4,5,6,7,8,9&', '0,1,2,3,4,5,6,7,8&', '0,1,2,3,4,5,6,7,8&', '0,1,2,3,4,5,6,7,8,9,10&', '0,1,2,3,4,5,6,7,8,9,10,11&', '0,1,2,3,4,5,6,7,8,9&'], scan=['7,9,12,14,17,19,22,24,27', '7,9,12,14,17,19,22,24,27', '7,9,12,14,17,19,22,24,27', '6,8,11,13,16,18,21,23,26', '6,8,11', '7,9,12,14,17,19,22,24,27', '6,8,11,13,16,18,21,23,26', '6,8,11,13,16,18,21,23,26'], intent='OBSERVE_TARGET#ON_SOURCE', datacolumn='data', imagename='uid___A001_X128e_X222.s38_0.NGC6334I_sci.spw16.cube.I.iter1', imsize=[108, 108], cell=['1.2arcsec'], phasecenter='ICRS 17:20:53.3600 -035.47.00.000', stokes='I', specmode='cube', nchan=2006, start='130.0220940318GHz', width='0.4882638MHz', outframe='LSRK', perchanweightdensity=True, gridder='standard', mosweight=False, usepointing=False, pblimit=0.2, deconvolver='hogbom', restoration=True, restoringbeam='common', pbcor=True, weighting='briggsbwtaper', robust=0.5, npixels=0, niter=99999, threshold='0.292Jy', nsigma=0.0, interactive=0, usemask='auto-multithresh', sidelobethreshold=1.25, noisethreshold=5.0, lownoisethreshold=2.0, negativethreshold=0.0, minbeamfrac=0.1, growiterations=75, dogrowprune=True, minpercentchange=1.0, fastnoise=False, restart=True, savemodel='none', calcres=True, calcpsf=True, parallel=True)
### ------------------------------------------------------------------------------------------------------------------------
###

ic = InteractiveClean( vis=ms_path, imagename=img,
                       field='NGC6334I',
                       spw=['16', '16', '16', '16', '16', '16', '16', '16'],
                       antenna=[ '0,1,2,3,4,5,6,7,8,9,10&', '0,1,2,3,4,5,6,7,8,9,10&', '0,1,2,3,4,5,6,7,8,9&',
                                 '0,1,2,3,4,5,6,7,8&', '0,1,2,3,4,5,6,7,8&', '0,1,2,3,4,5,6,7,8,9,10&',
                                 '0,1,2,3,4,5,6,7,8,9,10,11&', '0,1,2,3,4,5,6,7,8,9&'],
                       scan=['7,9,12,14,17,19,22,24,27', '7,9,12,14,17,19,22,24,27', '7,9,12,14,17,19,22,24,27',
                             '6,8,11,13,16,18,21,23,26', '6,8,11', '7,9,12,14,17,19,22,24,27',
                             '6,8,11,13,16,18,21,23,26', '6,8,11,13,16,18,21,23,26'],
                       intent='OBSERVE_TARGET#ON_SOURCE',
                       datacolumn='data',
                       imsize=[108, 108],
                       cell=['1.2arcsec'],
                       phasecenter='ICRS 17:20:53.3600 -035.47.00.000',
                       stokes='I',
                       specmode='cube',
                       nchan=2006,
                       start='130.0220940318GHz',
                       width='0.4882638MHz',
                       outframe='LSRK',
                       perchanweightdensity=True,
                       gridder='standard',
                       mosweight=False,
                       usepointing=False,
                       pblimit=0.2,
                       deconvolver='hogbom',
                       restoringbeam='common',
                       pbcor=True,
                       weighting='briggsbwtaper',
                       robust=0.5,
                       npixels=0,
                       niter=99999,
                       threshold='0.292Jy',
                       nsigma=0.0,
                       mask=MaskMode.AUTOMT,
                       sidelobethreshold=1.25,
                       noisethreshold=5.0,
                       lownoisethreshold=2.0,
                       negativethreshold=0.0,
                       minbeamfrac=0.1,
                       growiterations=75,
                       dogrowprune=True,
                       minpercentchange=1.0,
                       fastnoise=False,
                       savemodel='none',
                       parallel=True
                     )

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
