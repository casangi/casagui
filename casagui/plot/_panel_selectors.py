'''
Create panel widgets for various functions
'''

import panel as pn

from casagui.bokeh.state._palette import available_palettes
from casagui.plot._ms_plot_constants import VIS_AXIS_OPTIONS, AGGREGATOR_OPTIONS, PS_SELECTION_OPTIONS, MS_SELECTION_OPTIONS, DEFAULT_UNFLAGGED_CMAP, DEFAULT_FLAGGED_CMAP

def file_selector(description, start_dir, callback):
    ''' Return a layout for file selection with input description and start directory.
        Includes a TextInput and a FileSelector, with a callback to set TextInput from FileSelector.
    '''
    filename = pn.widgets.TextInput(
        description=description,
        name="Filename",
        placeholder='Enter filename or use file browser below',
    )

    file_select = pn.widgets.FileSelector(start_dir)
    select_file = pn.bind(callback, file_select)

    fs_card = pn.Card(
        file_select,
        title='File browser',
        collapsed=True,
        collapsible=True,
    )

    return pn.Column(
        pn.Row( # [0]
            filename,   # [0]
            select_file # [1]
        ),
        fs_card, # [1]
    )

def title_selector():
    ''' Return a layout for title input using TextInput '''
    return pn.widgets.TextInput(
        description="Plot title",
        name="Title",
        placeholder='Enter title for plot',
    )

def style_selector():
    ''' Return a layout for style parameters.
        Currently supports colormaps, colorbar, and color limits.
    '''
    colormap_options = available_palettes()

    unflagged_cmap_selector = pn.widgets.Select(
        name="Unflagged data colormap",
        options=colormap_options,
        value=DEFAULT_UNFLAGGED_CMAP,
        description="Select colormap for unflagged data",
    )

    flagged_cmap_selector = pn.widgets.Select(
        name="Flagged data colormap",
        options=colormap_options,
        value=DEFAULT_FLAGGED_CMAP,
        description="Select colormap for flagged data",
    )

    colorbar_checkbox = pn.widgets.Checkbox(
        name="Show colorbar",
        value=True,
    )

    auto_color_limits_checkbox = pn.widgets.Checkbox(
        name="Auto color limits",
        value=True,
        sizing_mode='fixed',
    )

    color_range_slider = pn.widgets.RangeSlider(
        name="Color limits",
        sizing_mode='stretch_width',
    )

    return pn.Column(
        pn.Row( # [0]
            unflagged_cmap_selector, # [0]
            flagged_cmap_selector,   # [1]
            colorbar_checkbox,       # [2]
        ),
        pn.Row( # [1]
            auto_color_limits_checkbox, # [0]
            color_range_slider,         # [1]
        )
    )

def axis_selector(x_axis, y_axis, axis_options):
    ''' Return layout of selectors for x-axis, y-axis, and vis-axis '''
    x_options = axis_options if axis_options else [x_axis]
    x_selector = pn.widgets.Select(
        name="X",
        options=x_options,
        description="Select x axis",
        value=x_axis
    )

    y_options = axis_options if axis_options else [y_axis]
    y_selector = pn.widgets.Select(
        name="Y",
        options=y_options,
        description="Select y axis",
        value=y_axis
    )

    vis_selector = pn.widgets.RadioButtonGroup(
        name='Vis Axis',
        options=VIS_AXIS_OPTIONS,
        description="Select vis axis component of complex data"
    )

    return pn.Column(
        pn.Row( # [0]
            x_selector, # [0]
            y_selector  # [1]
        ),
        vis_selector, # [1]
    )

def aggregation_selector(axis_options):
    ''' Return layout of selectors for aggregator and agg axes '''
    agg_selector = pn.widgets.Select(
        name="Aggregator",
        options=AGGREGATOR_OPTIONS,
        description="Select aggregation type"
    )

    agg_axis_selector = pn.widgets.MultiSelect(
        name="Agg axis or axes",
        options=axis_options,
        description="Select one or more axes to aggregate"
    )

    return pn.Row(
        agg_selector,      # [0]
        agg_axis_selector, # [1]
    )

def iteration_selector(axis_options, callback):
    ''' Return layout of selectors for iteration axis and player selector for value.
        Callback sets values in iter value player and iter value range selectors when iter_axis is selected.
    '''
    iter_options = ['None']
    iter_options.extend(axis_options)

    iter_axis_selector = pn.widgets.Select(
        name="Iteration axis",
        options=iter_options,
        description="Select axis over which to iterate"
    )

    update_iter_values = pn.bind(callback, iter_axis_selector)

    iter_value_type = pn.widgets.RadioButtonGroup(
        name='Iteration selection type',
        options=['Value', 'Range'],
        description="Select iteration value or range"
    )

    # Single value
    iter_value_player = pn.widgets.DiscretePlayer(
        name="Iteration value",
        show_loop_controls=False,
        show_value=False,
        value_align='start',
        visible_buttons=['first', 'previous', 'next', 'last'],
        sizing_mode='stretch_width',
    )

    # Range
    iter_range_start = pn.widgets.IntInput(
        name="Iteration start",
        start=0,
        value=0,
        description="Index of first value in iteration",
    )
    iter_range_end = pn.widgets.IntInput(
        name="Iteration end",
        start=0,
        value=0,
        description="Index of last value in iteration",
    )
    subplot_rows = pn.widgets.IntInput(
        name="Subplot rows",
        start=1,
        end=10,
        description="Number of rows to display iteration plots",
    )
    subplot_columns = pn.widgets.IntInput(
        name="Subplot columns",
        start=1,
        end=10,
        description="Number of columns to display iteration plots",
    )
    iter_range_widgets = pn.Column(
        pn.Row( # [0]
            iter_range_start, # [0]
            iter_range_end,   # [1]
        ),
        pn.Row( # [1]
            subplot_rows,    # [0]
            subplot_columns, # [1]
        ),
        pn.pane.HTML(
            "<b>Multiple subplots will be shown in new tab</b>",
        )
    )

    # Put iter value/range into accordion
    iter_value_selectors = pn.Accordion(
        ('Select Single Iteration Value', iter_value_player), # [0]
        ('Select Iteration Index Range', iter_range_widgets), # [1]
        toggle=True,
    )

    return pn.Column(
        pn.Row( # [0]
            iter_axis_selector, # [0]
            iter_value_type,    # [1]
            update_iter_values,
        ),
        iter_value_selectors, # [1]
    )

def selection_selector():
    ''' Return layout of selectors for ProcessingSet and MSv4 selection. '''
    # Create column of ps selectors; values added from PS summary later.
    ps_selection = pn.Column()
    ps_selection.append(
        pn.widgets.TextInput(
            name="Query",
            placeholder='Enter Pandas DataFrame query for summary columns',
        )
    )
    _add_select_none(ps_selection, PS_SELECTION_OPTIONS)

    # Create column of ms selectors; values added from MS later.
    ms_selection = pn.Column()
    _add_select_none(ms_selection, MS_SELECTION_OPTIONS)

    return pn.Accordion(
        ("Select ProcessingSet", ps_selection),  # [0]
        ("Select MeasurementSets", ms_selection), # [1]
        toggle=False,
    )

def _add_select_none(pn_column, names):
    ''' Add Panel Select widgets for list of names with option 'None'. 
        pn_column is a Panel Column to which to add selectors.
    '''
    for name in names:
        pn_column.append(
            pn.widgets.Select(
                name=name,
                options=['None'],
            )
        )

def plot_starter(callback):
    ''' Create a row with a Plot button and spinner with a button callback to start spinner. '''
    plot_button = pn.widgets.Button(
        name='Plot',
        button_type='primary',
        sizing_mode='fixed',
        width=100,
    )

    plot_spinner = pn.indicators.LoadingSpinner(
        value=False,
        size=25,
    )

    start_spinner = pn.bind(callback, plot_button)

    return pn.Row(
        plot_button,  # [0]
        plot_spinner, # [1]
        start_spinner,
    )
