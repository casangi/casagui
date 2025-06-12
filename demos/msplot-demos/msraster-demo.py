import os
import ssl
import certifi
import urllib
import tarfile
import time

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
## where to save plots
##
plot_dir = "demo_plots"

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


def plot_ms_raster():
    ''' Show MsRaster features '''
    # Download test ms
    fetch_ms()

    # Create plot directory
    if not os.path.exists(plot_dir):
        os.mkdir(plot_dir)

    # Start toolviper dask client
    client = local_client()

    # Converts ms to zarr, and gets xradio ProcessingSet.
    # logging levels are 'debug', 'info' , 'warning', 'error', 'critical'
    msr = MsRaster(ms=ms_path, show_gui=False, log_level='info')

    # ProcessingSet selection using summary column name and value, or MeasurementSetXds coordinates.
    # For PS selection options: msr.summary()
    intent_selection = {'intents': 'OBSERVE_TARGET#ON_SOURCE'}

    # ------------------------------------------------------------------
    # Demo default plot: x_axis="baseline", y_axis="time", vis_axis="amp" selecting data_group "base" in first spw.
    # The unplotted dimensions "frequency" and "polarization" are also automatically selected by first index.
    # This dataset only has group 'base', but could have 'corrected', 'model', etc.
    # This dataset only has one spectral window, but first spw id would be automatically selected.
    # The color limits for the first spw must be computed, then are saved for future plots.
    msr.plot()
    msr.show()
    msr.save(filename=os.path.join(plot_dir, "default_plot.png"))

    # ------------------------------------------------------------------
    # Demo vis axis options
    for vis_axis in ['amp', 'phase', 'real', 'imag']:
        msr.plot(selection=intent_selection, vis_axis=vis_axis, color_mode='auto')
        msr.show()
        filename=os.path.join(plot_dir, f"{vis_axis}.png")
        msr.save(filename)

    # ------------------------------------------------------------------
    # Demo multiple plots as subplots (rows, columns) in a 2x2 grid.
    # Default subplots is single plot (1, 1).
    # Set clear_plots=False after first plot
    for vis_axis in ['amp', 'phase', 'real', 'imag']:
        clear_plots = True if vis_axis == 'amp' else False
        msr.plot(selection=intent_selection, vis_axis=vis_axis, subplots=(2, 2), color_mode='auto', clear_plots=clear_plots)
    msr.show()
    filename=os.path.join(plot_dir, "vis_axis_layout.png")
    msr.save(filename)

    # ------------------------------------------------------------------
    # Demo dimension combinations for x and y axis
    axes = [
        #('baseline', 'time'),
        ('frequency', 'time'), 
        ('polarization', 'time'),
        ('frequency', 'baseline'),
        ('polarization', 'baseline'),
        ('polarization', 'frequency'),
    ]
    for xaxis, yaxis in axes:
        plot_axes = f"{yaxis}_vs_{xaxis}"
        msr.plot(selection=intent_selection, x_axis=xaxis, y_axis=yaxis, color_mode='auto')
        msr.show()
        filename=os.path.join(plot_dir, f"{plot_axes}.png")
        msr.save(filename)

    # ------------------------------------------------------------------
    # Demo ms selection of dimensions *by value*, instead of automatic first index
    dim_selection = {
        'intents': ['OBSERVE_TARGET#ON_SOURCE'],
        'polarization': 'YY',
        'baseline': 'DA48_A046 & DA49_A029'
    }
    msr.plot(x_axis='frequency', y_axis='time', selection=dim_selection, color_mode='auto')
    msr.show()
    filename=os.path.join(plot_dir, "select_dims.png")
    msr.save(filename)

    # ------------------------------------------------------------------
    # Demo iter_axis: axis over which to iterate values for multiple plots.
    # Single plot starting at first iteration (XX) default iter_range (0, 0).
    msr.plot(selection=intent_selection, iter_axis='polarization', color_mode='auto')
    msr.show()
    filename=os.path.join(plot_dir, "iteration0.png")
    msr.save(filename)

    # Single plot starting at first iteration (XX) iter_range (1, 1).
    msr.plot(selection=intent_selection, iter_axis='polarization', iter_range=(1, 1), color_mode='auto')
    msr.show()
    filename=os.path.join(plot_dir, "iteration1.png")
    msr.save(filename)

    # iter_range with all iterations and single-plot layout:
    # Save all plots individually, starting at first plot, with filename suffix _0, _1, etc.
    # Note: show() would only show first iteration plot using default subplots=(1, 1).
    msr.plot(selection=intent_selection, iter_axis='polarization', iter_range=(0, -1), color_mode='auto')
    filename=os.path.join(plot_dir, "iterations.png")
    msr.save(filename)

    # iter_range with all iterations and 2x2 layout: only first 4 iterations plotted.
    # Show and save only the layout.
    msr.plot(selection=intent_selection, iter_axis='frequency', iter_range=(0, -1), subplots=(2, 2), color_mode='auto')
    msr.show()
    filename=os.path.join(plot_dir, "iter_row_layout.png")
    msr.save(filename)

    # Single column layout
    msr.plot(selection=intent_selection, iter_axis='polarization', iter_range=(0, -1), subplots=(2, 1), color_mode='auto')
    msr.show()
    filename=os.path.join(plot_dir, "iter_col_layout.png")
    msr.save(filename)

    # Demo combining iteration and layout of separate plots.
    # Plot amp with polarization iteration, then phase, to form 2x2 layout. Do not clear plots on second plot.
    msr.plot(selection=intent_selection, vis_axis='amp', iter_axis='polarization', iter_range=(0, -1), subplots=(2, 2), color_mode='auto')
    msr.plot(selection=intent_selection, vis_axis='phase', iter_axis='polarization', iter_range=(0, -1), subplots=(2, 2), color_mode='auto', clear_plots=False)
    msr.show()
    filename=os.path.join(plot_dir, "amp_phase_iter.png")
    msr.save(filename)

    # ------------------------------------------------------------------
    # Demo data aggregation:
    #   aggregator: options include max, mean, median, min, std, sum, var.
    #   agg_axis: dimension over which to aggregate.
    # Plot time vs baseline, averaged over frequency. Selects first polarization automatically.
    msr.plot(selection=intent_selection, aggregator='mean', agg_axis='frequency', color_mode='auto')
    msr.show()
    filename=os.path.join(plot_dir, "agg_mean_frequency.png")
    msr.save(filename)

    # Plot time vs frequency, max across baselines. Selects first polarization automatically.
    msr.plot(selection=intent_selection, x_axis='frequency', y_axis='time', aggregator='max', agg_axis='baseline', color_mode='auto')
    msr.show()
    filename=os.path.join(plot_dir, "agg_max_baseline.png")
    msr.save(filename)

    # time vs frequency, max across baseline and polarization (explicit).
    msr.plot(selection=intent_selection, x_axis='frequency', y_axis='time', aggregator='max', agg_axis=['baseline', 'polarization'], color_mode='auto')
    msr.show()
    filename=os.path.join(plot_dir, "agg_max_baseline_pol.png")
    msr.save(filename)

    # time vs frequency, max across other two dimensions automatically by not setting agg_axis (implicit).
    msr.plot(selection=intent_selection, x_axis='frequency', y_axis='time', aggregator='max', color_mode='auto')
    msr.show()
    filename=os.path.join(plot_dir, "agg_max_auto_baseline_pol.png")
    msr.save(filename)

    # ------------------------------------------------------------------
    # Demo combining aggregator, iteration, and subplots.
    # time vs frequency, max across baselines, with polarization iteration; layout in one row.
    msr.plot(selection=intent_selection, x_axis='frequency', y_axis='time', aggregator='max', agg_axis='baseline', iter_axis='polarization', iter_range=(0, -1), subplots=(1, 2), color_mode='auto')
    msr.show()
    filename=os.path.join(plot_dir, "agg_max_baseline_pol_iter.png")
    msr.save(filename)

if __name__ == '__main__':
    plot_ms_raster()
