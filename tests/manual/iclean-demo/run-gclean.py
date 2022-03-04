from casatasks.private.imagerhelpers._gclean import gclean

def main( ):
    for rec in gclean( vis='refim_point_withline.ms', imagename='test', niter=20 ):
        print(f'\t>>>>--->> {rec}')

if __name__ == "__main__":
    main( )
