'''
Common ms plotting functions
'''

import hvplot

def show(plot, title):
    ''' 
    Show interactive Bokeh plot in a browser.
    Plot tools include pan, zoom, hover, and save.
    Groupby axes have selectors: slider, dropdown, etc.
    '''
    if plot is None:
        raise RuntimeError("No plot to show.  Run plot() to create plot.")
    hvplot.show(plot, title=title, threaded=True)


def save(plot, filename, fmt, hist, backend, resources, toolbar, title):
    '''
    Save plot to file.
        filename (str): Name of file to save.
        fmt (str): Format of file to save ('png', 'svg', 'html', or 'gif') or 'auto': inferred from filename.
        hist (bool): Whether to compute and adjoin histogram.
        backend (str): rendering backend, 'bokeh' or 'matplotlib'.
        resources (str): whether to save with 'online' or 'offline' resources.  'offline' creates a larger file.
        toolbar (bool): Whether to include the toolbar in the exported plot.
        title (str): Custom title for exported HTML file.
    '''
    if plot is None:
        raise RuntimeError("No plot to save.  Run plot() to create plot.")

    # embed BokehJS resources inline for offline use, else use content delivery network
    resources = 'inline' if resources == 'offline' else 'cdn'

    if hist:
        hvplot.save(plot.hist(), filename=filename, fmt=fmt, backend=backend, resources=resources, toolbar=toolbar, title=title)
    else:
        hvplot.save(plot, filename=filename, fmt=fmt, backend=backend, resources=resources, toolbar=toolbar, title=title)
