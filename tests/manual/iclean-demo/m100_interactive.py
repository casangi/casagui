###
### This is from the "First Look at Imaging" in the casaguides:
###
###    * https://casaguides.nrao.edu/index.php/First_Look_at_Imaging
###
import os
import asyncio
import urllib
import tarfile

from casagui import iclean

##
## demo measurement set to use, from:
##
##     https://casaguides.nrao.edu/index.php?title=M100_Band3_Combine_6.1
##
## $ wget https://bulk.cv.nrao.edu/almadata/sciver/M100Band3_12m/M100_Band3_12m_CalibratedData.tgz
## $ wget https://bulk.cv.nrao.edu/almadata/sciver/M100Band3ACA/M100_Band3_7m_CalibratedData.tgz
## $ tar -xf M100_Band3_12m_CalibratedData.tgz
## $ tar -xf M100_Band3_7m_CalibratedData.tgz
## $ ln -s M100_Band3_7m_CalibratedData/M100_Band3_7m_CalibratedData.ms/
## $ ln -s M100_Band3_12m_CalibratedData/M100_Band3_12m_CalibratedData.ms/
## $ casa -c "split(vis='M100_Band3_12m_CalibratedData.ms', outputvis='M100_12m_CO.ms',spw='0',field='M100', datacolumn='data',keepflags=False); split(vis='M100_Band3_7m_CalibratedData.ms', outputvis='M100_7m_CO.ms',spw='3,5',field='M100', datacolumn='data',keepflags=False); concat(vis=['M100_12m_CO.ms','M100_7m_CO.ms'], concatvis='M100_combine_CO.ms')"
##
ms_path = 'M100_combine_CO.ms'
##
## where to fetch the demo measurement set
##
##
## Using the URL given in the casaguide results in the error:
##
##      File "first_look_interactive.py", line 28, in <module>
##        tar = tarfile.open(fileobj=tstream, mode="r")
##      File "/opt/local/Library/Frameworks/Python.framework/Versions/3.8/lib/python3.8/tarfile.py", line 1601, in open
##        saved_pos = fileobj.tell()
##      io.UnsupportedOperation: seek

#ms_url = "https://bulk.cv.nrao.edu/almadata/public/working/sis14_twhya_calibrated_flagged.ms.tar"
#ms_url = "https://casa.nrao.edu/download/devel/casagui/sis14_twhya_calibrated_flagged.ms.tar.gz"
ms_url = None
##
## output image file name
##
img = 'test'

if not os.path.isdir(ms_path):
    tstream = urllib.request.urlopen(ms_url)
    tar = tarfile.open(fileobj=tstream, mode="r:gz")
    tar.extractall()


ic = iclean( vis=ms_path, imagename=img,
             imsize=800,
             cell=['0.1arcsec'],
             specmode='cube',
             restfreq='115.271201800GHz',
             interpolation='nearest', 
             pblimit=-1e-05,
             gridder='mosaic',
             deconvolver='hogbom',
             nchan=70,
             niter=50,
             cycleniter=10,
             cyclefactor=3,
             threshold='0.0mJy' )

if True:
    print( "Result: %s" % ic( ) )
else:
    try:
        asyncio.get_event_loop().run_until_complete(ic.show( ))
        asyncio.get_event_loop().run_forever()

    except KeyboardInterrupt:
        print('\nInterrupt received, shutting down ...')
        #os.system('rm -rf {output_image}.* *.html *.log'.format(output_image=output_image))

    print( "Result: %s" % ic.result( ) )
