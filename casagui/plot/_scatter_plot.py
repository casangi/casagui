'''
Functions to create a scatter plot of visibility/spectrum data from xarray Dataset
'''

import hvplot.pandas

def scatter_plot(xds, x_axis, y_axis, ms_name, logger):
    '''
    Create scatter plot y_axis vs x_axis.
        xds (xarray Dataset): msv4 xarray Dataset
        x_axis (str): x-axis to plot
        y_axis (str): y-axis to plot
        ms_name (str): ms basename for title
    Returns: plot
    '''
    plot = None # TODO after scatter_data!
    return plot
