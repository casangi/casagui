
import os 
from casagui import plotants
current_dir = os.path.dirname(os.path.realpath(__file__))

msname = 'ic2233_1.ms'
plotants(os.path.join(current_dir,msname),logpos=True).show( )
##telescope, names, ids, xpos, ypos, stations = getPlotantsAntennaInfo( msname, False, [ ], False )
##print('telescope:\t%s' % telescope)
##print('names:\t%s' % names)
##print('ids:\t\t%s' % ids)
##print('xpos:\t\t%s' % xpos)
##print('ypos:\t\t%s' % ypos)
##print('stations:\t%s' % stations)
