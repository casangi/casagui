import os
import ssl
import certifi
import urllib
import tarfile

from toolviper.dask.client import local_client

from casagui.apps import MsRaster

##
## demo measurement set to use
##
ms_path = 'sis14_twhya_selfcal.ms'
##
## where to fetch the demo measurement set
##
ms_url = "https://casa.nrao.edu/download/devel/casavis/data/sis14_twhya_selfcal.ms.tar.gz"
##
plot_dir = "demo_plots"

# The raster plots can be shown in the webbrowser and/or saved to file.
# If show=True, ^C to exit script.
show = False
save = True

def fetch_ms():
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

def show_plot(msr, layout=None):
    if show:
        msr.show(layout=layout)

def save_plot(msr, filename='demo.png', layout=None, export_range='start'):
    if not os.path.exists(plot_dir):
        os.mkdir(plot_dir)
    if save:
        msr.save(filename=os.path.join(plot_dir, filename), layout=layout, export_range=export_range)
    
def plot_ms_raster():
    ''' Show MsRaster features '''
    # Download test ms
    fetch_ms()

    # Start toolviper dask client
    client = local_client()

    # Converts ms to zarr, and gets xradio ProcessingSet.
    # logging levels are 'debug', 'info' , 'warning', 'error', 'critical'
    msr = MsRaster(ms_path, log_level='info', interactive=False)

    # ProcessingSet selection using summary column name and value.
    # For selection options: msr.summary()
    intent_selection = {'intents': ['OBSERVE_TARGET#ON_SOURCE']}

    # Demo vis_axis options for first spw from data group 'base' (default).
    # This dataset only has group 'base' (no 'corrected', 'model', etc.)
    for vis_axis in ['amp', 'phase', 'real', 'imag']:
        # Default plot is x_axis="baseline", y_axis="time", vis_axis="amp"
        # Frequency and polarization are automatically selected by first index
        title = f"Demo vis_axis {vis_axis}"
        msr.plot(selection=intent_selection, vis_axis=vis_axis)
        show_plot(msr)
        save_plot(msr, f"{vis_axis}.png")

    # Demo x and y axis combinations for first spw
    # (This dataset only has one spectral window, but first would be automatically selected.)
    axes = [
        ('baseline', 'time'),
        ('frequency', 'time'), 
        ('polarization', 'time'),
        ('frequency', 'baseline'),
        ('polarization', 'baseline'),
        ('polarization', 'frequency'),
    ]
    for xaxis, yaxis in axes:
        plot_axes = f"{yaxis}_vs_{xaxis}"
        msr.plot(selection=intent_selection, x_axis=xaxis, y_axis=yaxis)
        show_plot(msr)
        save_plot(msr, f"{plot_axes}.png")

    # Demo ms selection of dimensions instead of automatic first index
    dim_selection = {
        'intents': ['OBSERVE_TARGET#ON_SOURCE'],
        'polarization': 'YY',
        'baseline': 'DA48_A046 & DA49_A029',
    }
    msr.plot(x_axis='frequency', y_axis='time', selection=dim_selection)
    show_plot(msr)
    save_plot(msr, "select_dims.png")

    # Demo layout (start, rows, columns): two separate plots in one row (start=0, rows=1, columns=2).
    # When layout is shown in browser and zoom or pan is used on a plot, all plots are acted upon.
    msr.plot(selection=intent_selection, vis_axis='amp')
    msr.plot(selection=intent_selection, vis_axis='phase', clear_plots=False)
    show_plot(msr, layout=(0, 1, 2))
    save_plot(msr, "amp_phase.png", layout=(0, 1, 2))

    # Demo iter_axis plots with layout or export_range.
    # This dataset has two polarizations.
    msr.plot(selection=intent_selection, iter_axis='polarization')
    show_plot(msr)                                          # no layout shows first iteration plot.
    save_plot(msr, 'polarizations.png')                     # save plot 0 only (export_range='one' is default)
    save_plot(msr, 'polarizations.png', export_range='all') # save all plots with suffix _0, _1, _2, etc.
    # layout (start, rows, columns) of multiple plots will show and save only the plots in the layout. exp_range is ignored.
    show_plot(msr, layout=(0, 1, 2))
    save_plot(msr, 'polarizations_layout.png', layout=(0, 1, 2))
    # layout single plot with start=1, show and save second plot only.
    show_plot(msr, layout=(1, 1, 1))
    save_plot(msr, 'polarizations_plot_1.png', layout=(1, 1, 1), export_range='one')

    # Demo layout of separate plots with iteration to form 2x2 layout.
    msr.plot(selection=intent_selection, vis_axis='amp', iter_axis='polarization')
    msr.plot(selection=intent_selection, vis_axis='phase', iter_axis='polarization', clear_plots=False)
    show_plot(msr, layout=(0, 2, 2))
    save_plot(msr, "amp_phase_pol_iter.png", layout=(0, 2, 2))

    # Demo aggregator: options include max, mean, min, std, sum, var
    # time vs baseline, averaged over frequency. Selects first polarization automatically.
    msr.plot(selection=intent_selection, aggregator='mean', agg_axis='frequency')
    show_plot(msr)
    save_plot(msr, "agg_mean_frequency.png")
    # time vs frequency, max across baselines. Selects first polarization automatically.
    msr.plot(selection=intent_selection, x_axis='frequency', aggregator='max', agg_axis='baseline')
    show_plot(msr)
    save_plot(msr, "agg_max_baseline.png")
    # time vs frequency, max across baselines with polarization iteration + layout.
    msr.plot(selection=intent_selection, x_axis='frequency', aggregator='max', agg_axis='baseline', iter_axis='polarization')
    show_plot(msr, layout=(0, 1, 2))
    save_plot(msr, "agg_max_baseline_pol_iter.png", layout=(0, 1, 2))
    # time vs frequency, max across two dimensions rather than select one dimension.
    msr.plot(selection=intent_selection, x_axis='frequency', aggregator='max', agg_axis=['baseline', 'polarization'])
    show_plot(msr)
    save_plot(msr, "agg_max_baseline_polarization.png")

if __name__ == '__main__':
    plot_ms_raster()
