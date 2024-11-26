'''
Functions to create a scatter xarray Dataset of x/y data from xradio ProcessingSet
'''

from xradio.measurement_set.processing_set import ProcessingSet

from ._ms_data import get_axis_data
from ._ms_select import select_ps
from ._ms_utils import concat_ps_xds

def scatter_data(ps, x_axis, y_axis, selection, data_group, logger):
    '''
    Create scatter xds: y_axis and x_axis.
        ps (xradio ProcessingSet): input MSv4 datasets
        x_axis (str): x-axis to plot
        y_axis (str): y-axis to plot
        data_group (str): name of related correlated data, flags, weights, and uvw data
        selection (dict): select data to plot using ps summary columns, pandas query, or xds dimensions and coordinates
        logger (graphviper logger): logger
    Returns: selected xarray Dataset of plot axes and dimensions
    '''
    selected_ps = select_ps(ps, selection, data_group, logger)
    return concat_ps_xds(selected_ps, logger)
