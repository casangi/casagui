'''
Create panel widgets for various functions
'''

import panel as pn

from casagui.bokeh.state._palette import available_palettes
from casagui.plot.ms_plot._ms_plot_constants import VIS_AXIS_OPTIONS, AGGREGATOR_OPTIONS, DEFAULT_UNFLAGGED_CMAP, DEFAULT_FLAGGED_CMAP

def file_selector(description, start_dir, callback):
    ''' Return a layout for file selection with input description and start directory.
        Includes a TextInput and a FileSelector, with a callback to set TextInput from FileSelector.
    '''
    filename = pn.widgets.TextInput(
        description=description,
        name="Filename",
        placeholder='Enter filename or use file browser below',
        sizing_mode='stretch_width',
    )

    file_select = pn.widgets.FileSelector(
        start_dir,
    )
    select_file = pn.bind(callback, file_select)

    fs_card = pn.Card(
        file_select,
        title='File browser',
        collapsed=True,
        collapsible=True,
        sizing_mode='stretch_width',
    )

    return pn.Column(
        pn.Row( # [0]
            filename,   # [0]
            select_file # [1]
        ),
        fs_card, # [1]
        width_policy='min',
    )

def style_selector(style_callback, color_range_callback):
    ''' Return a layout for style parameters.
        Currently supports colormaps, colorbar, and color limits.
    '''
    cmaps = available_palettes()

    cmap_selector = pn.widgets.Select(
        name="Unflagged data colormap",
        options=cmaps,
        value=DEFAULT_UNFLAGGED_CMAP,
        sizing_mode='scale_width',
    )

    flagged_cmap_selector = pn.widgets.Select(
        name="Flagged data colormap",
        options=cmaps,
        value=DEFAULT_FLAGGED_CMAP,
        sizing_mode='scale_width',
    )

    colorbar_checkbox = pn.widgets.Checkbox(
        name="Show colorbar",
        value=True,
    )

    flagged_colorbar_checkbox = pn.widgets.Checkbox(
        name="Show flagged colorbar",
        value=True,
    )

    select_style = pn.bind(style_callback, cmap_selector, flagged_cmap_selector, colorbar_checkbox, flagged_colorbar_checkbox)

    color_mode_selector = pn.widgets.RadioBoxGroup(
        options=["No color range", "Auto color range", "Manual color range"],
    )

    color_range_slider = pn.widgets.RangeSlider(
        name="Colorbar range",
    )

    select_color_range = pn.bind(color_range_callback, color_mode_selector, color_range_slider)

    return pn.Column(
        pn.Row( # [0]
            cmap_selector,         # [0]
            flagged_cmap_selector, # [1]
        ),
        pn.Row( # [1]
            colorbar_checkbox,         # [0]
            flagged_colorbar_checkbox, # [1]
        ),
        select_style, # [2]
        pn.Row( # [3]
            color_mode_selector, # [0]
            color_range_slider,  # [1]
        ),
        select_color_range, # [4]
        width_policy='min',
    )

def title_selector(callback):
    ''' Return a layout for title input using TextInput '''
    title_input = pn.widgets.TextInput(
        name="Title",
        placeholder="Enter title for plot ('ms' to use MS name)",
        sizing_mode='stretch_width',
    )
    select_title = pn.bind(callback, title_input)
    return pn.Row(
        title_input,
        select_title,
        width_policy='min',
    )

def axis_selector(x_axis, y_axis, axis_options, include_vis, callback):
    ''' Return layout of selectors for x-axis, y-axis, and vis-axis '''
    x_options = axis_options if axis_options else [x_axis]
    x_selector = pn.widgets.Select(
        name="X Axis",
        options=x_options,
        value=x_axis,
        sizing_mode='scale_width',
    )

    y_options = axis_options if axis_options else [y_axis]
    y_selector = pn.widgets.Select(
        name="Y Axis",
        options=y_options,
        value=y_axis,
        sizing_mode='scale_width',
    )

    if include_vis:
        # for raster plot
        vis_label = pn.pane.LaTeX(
            r"Vis Axis",
        )
        vis_selector = pn.widgets.RadioBoxGroup(
            options=VIS_AXIS_OPTIONS,
            inline=True,
        )
        select_axes = pn.bind(callback, x_selector, y_selector, vis_selector)
        return pn.Column(
            pn.Row( # [0]
                x_selector, # [0]
                y_selector  # [1]
            ),
            vis_label,    # [1]
            vis_selector, # [2]
            select_axes,
            width_policy='min',
        )

    # for scatter plot
    select_axes = pn.bind(callback, x_selector, y_selector)
    return pn.Column(
        pn.Row( # [0]
            x_selector, # [0]
            y_selector  # [1]
        ),
        select_axes,
        width_policy='min',
    )


def aggregation_selector(axis_options, callback):
    ''' Return layout of selectors for aggregator and agg axes '''
    agg_selector = pn.widgets.Select(
        name="Aggregator",
        options=AGGREGATOR_OPTIONS,
        description="Select aggregation type",
        sizing_mode='scale_width',
    )

    agg_axis_selector = pn.widgets.MultiSelect(
        name="Agg axis or axes",
        options=axis_options,
        description="Select one or more axes to aggregate",
        sizing_mode='scale_width',
    )

    select_agg = pn.bind(callback, agg_selector, agg_axis_selector)

    return pn.Row(
        agg_selector,      # [0]
        agg_axis_selector, # [1]
        select_agg,
        width_policy='min',
    )

def iteration_selector(axis_options, axis_callback, iter_callback):
    ''' Return layout of selectors for iteration axis and player selector for value.
        Callback sets values in iter value player and iter value range selectors when iter_axis is selected.
    '''
    iter_options = ['None']
    iter_options.extend(axis_options)

    iter_axis_selector = pn.widgets.Select(
        name="Iteration axis",
        options=iter_options,
        description="Select axis over which to iterate",
        sizing_mode='scale_width',
    )

    update_iter_values = pn.bind(axis_callback, iter_axis_selector)

    iter_value_type = pn.widgets.RadioBoxGroup(
        options=['By Value', 'By Range'],
        inline=True,
    )

    # Single value
    iter_value_player = pn.widgets.DiscretePlayer(
        name="Iteration value",
        show_loop_controls=False,
        show_value=False,
        value_align='start',
        visible_buttons=['first', 'previous', 'next', 'last'],
        sizing_mode='scale_width',
    )

    # Range
    iter_range_start = pn.widgets.IntInput(
        name="Iteration start",
        start=0,
        value=0,
        description="Index of first value in iteration",
        sizing_mode='scale_width',
    )
    iter_range_end = pn.widgets.IntInput(
        name="Iteration end",
        start=0,
        value=0,
        description="Index of last value in iteration",
        sizing_mode='scale_width',
    )
    subplot_rows = pn.widgets.IntInput(
        name="Subplot rows",
        start=1,
        end=10,
        description="Number of rows to display iteration plots",
        sizing_mode='scale_width',
    )
    subplot_columns = pn.widgets.IntInput(
        name="Subplot columns",
        start=1,
        end=10,
        description="Number of columns to display iteration plots",
        sizing_mode='scale_width',
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
        pn.pane.LaTeX(
            r"Multiple subplots will be shown in new tab",
        ),
    )

    # Put iter value/range into accordion
    iter_value_selectors = pn.Accordion(
        ('Select Single Iteration Value', iter_value_player), # [0]
        ('Select Iteration Index Range', iter_range_widgets), # [1]
        toggle=True,
        sizing_mode='stretch_width',
    )

    select_iter = pn.bind(iter_callback, iter_axis_selector, iter_value_type, iter_value_player, iter_range_start, iter_range_end, subplot_rows, subplot_columns)

    return pn.Column(
        pn.Row( # [0]
            iter_axis_selector, # [0]
            iter_value_type,    # [1]
            update_iter_values,
        ),
        iter_value_selectors, # [1]
        select_iter,
        width_policy='min',
    )

def selection_selector(ps_callback):
    ''' Return layout of selectors for ProcessingSet and MSv4 selection. '''
    # Create column of ps selectors; values added from PS summary later.
    ps_selection = pn.Column(
        height_policy='min',
    )
    ps_selection.append(
        pn.widgets.TextInput(
            name="Query",
            placeholder='Enter query for summary columns',
            sizing_mode='stretch_width',
        )
    )
    select_ps = pn.bind(ps_callback, ps_selection[0])
    ps_selection.append(select_ps)

    selection_cards = pn.Accordion(
        ("Select ProcessingSet", ps_selection),  # [0]
        toggle=True,
        sizing_mode='stretch_width',
    )

    return pn.Column(
        selection_cards,
        width_policy='min',
    )

def _add_multi_choice(ps_selection, names):
    ''' Add Panel Select widgets for list of names with option 'None'. 
        ps_selection is a Column to which to add selectors.
    '''
    for name in names:
        ps_selection.append(
            pn.widgets.MultiChoice(
                name=name,
                sizing_mode='stretch_width',
            )
        )

def plot_starter(callback):
    ''' Create a row with a Plot button and spinner with a button callback to start spinner. '''
    plot_button = pn.widgets.Button(
        name='Plot',
        button_style='outline',
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
