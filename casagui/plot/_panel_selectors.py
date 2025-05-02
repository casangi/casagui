'''
Create panel widgets for various functions
'''

import panel as pn

from casagui.bokeh.state._palette import available_palettes
from casagui.plot._ms_plot_constants import VIS_AXIS_OPTIONS, AGGREGATOR_OPTIONS, DEFAULT_UNFLAGGED_CMAP, DEFAULT_FLAGGED_CMAP

def file_selector(description, start_dir, callback):
    ''' Return a layout for file selection with input description and start directory.
        Includes a TextInput and a FileSelector, with a callback to set TextInput from FileSelector.
    '''
    filename = pn.widgets.TextInput( 
        description=description,
        name="Filename",
        placeholder='Enter filename or use file browser below',
    )

    file_selector = pn.widgets.FileSelector(start_dir)
    select_file = pn.bind(callback, file_selector)

    fs_card = pn.Card(
        file_selector,
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
    agg_options = ['None']
    agg_options.extend(AGGREGATOR_OPTIONS)

    agg_selector = pn.widgets.Select(
        name="Aggregator",
        options=agg_options,
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
        Player values are set by callback when axis is selected. '''
    iter_options = ['None']
    iter_options.extend(axis_options)

    iter_axis_selector = pn.widgets.Select(
        name="Iteration axis",
        options=iter_options,
        description="Select axis over which to iterate"
    )

    iter_value_player = pn.widgets.DiscretePlayer(
        name="Iteration value",
        options=[],
        show_loop_controls=False,
        show_value=False,
        value_align='start',
        visible_buttons=['first', 'previous', 'next', 'last'],
        sizing_mode='stretch_width',
    )

    update_iter_values = pn.bind(callback, iter_axis_selector)

    return pn.Row(
        iter_axis_selector, # [0]
        iter_value_player,  # [1]
        update_iter_values,
    )
