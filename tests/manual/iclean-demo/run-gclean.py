import os
import urllib
import tarfile

from casatasks.private.imagerhelpers._gclean import gclean

##
## demo measurement set to use
##
ms_path = 'refim_point_withline.ms'
##
## where to fetch the demo measurement set
##
ms_url = "https://casa.nrao.edu/download/devel/casavis/data/refim_point_withline-ms.tar.gz"

if not os.path.isdir(ms_path):
    tstream = urllib.request.urlopen(ms_url)
    tar = tarfile.open(fileobj=tstream, mode="r:gz")
    tar.extractall()

def main( ):
    for rec in gclean( vis='refim_point_withline.ms', imagename='test', niter=20 ):
        print(f'\t>>>>--->> {rec}')

if __name__ == "__main__":
    main( )
