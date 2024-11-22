'''
Functions to create a scatter xarray Dataset of x/y data from xradio ProcessingSet
'''

from xradio.measurement_set.processing_set import ProcessingSet
import xradio.measurement_set._utils._utils.stokes_types

from ._xds_utils import concat_ps_xds
from ._ms_data import get_axis_data

def scatter_data(ps, x_axis, y_axis, selection, logger):
    '''
    Create scatter xds: y_axis and x_axis.
        ps (xradio ProcessingSet): input MSv4 datasets
        x_axis (str): x-axis to plot
        y_axis (str): y-axis to plot
        selection (dict): select metadata (ddi, field, intent), data dimensions (time, baseline, channel, correlation)
        logger (graphviper logger): logger
    Returns: selected xarray Dataset of visibility component and updated selection
    '''
    #TODO selection
    return concat_ps_xds(ps, logger)
