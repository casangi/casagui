'''
Class to create a raster plot of visibility/spectrum data using plot parameters.
'''

import holoviews as hv

# hvPlot extensions used to plot xarray DataArray and pandas DataFrame
# pylint: disable=unused-import
import hvplot.xarray
import hvplot.pandas
# pylint: enable=unused-import

from casagui.bokeh.format import get_time_formatter
from casagui.data.measurement_set.processing_set._ps_coords import set_index_coordinates
from casagui.plot.ms_plot._xds_plot_axes import get_axis_labels, get_vis_axis_labels, get_coordinate_labels

class RasterPlot:
    '''
        Class to create a raster plot from MS data.
        Implemented with xArray Dataset and hvPlot, but could change data and plotting backends using same interface.
    '''

    def __init__(self):
        self._plot_params = {'data': {}, 'plot': {'params': False}, 'style': {}}
        self._spw_color_limits = {}
        self.set_style_params() # use defaults unless set externally

    def set_style_params(self, unflagged_cmap='Viridis', flagged_cmap='Reds',  show_colorbar=True, show_flagged_colorbar=True):
        '''
            Set styling parameters for the plot.  Currently only colorbar settings.
            Placeholder for future styling such as fonts.

            Args:
                unflagged_cmap (str): colormap to use for unflagged data.
                flagged_cmap (str): colormap to use for flagged data.
                show_colorbar (bool): Whether to show colorbar with plot.  Default True.

            Colormap options: Bokeh palettes
            https://docs.bokeh.org/en/latest/docs/reference/palettes.html
        '''
        style_params = self._plot_params['style']
        style_params['unflagged_cmap'] = unflagged_cmap
        style_params['flagged_cmap'] = flagged_cmap
        style_params['show_colorbar'] = show_colorbar
        style_params['show_flagged_colorbar'] = show_flagged_colorbar

    def get_plot_params(self):
        ''' Return dict of plot params (default only if data params not set) '''
        return self._plot_params

    def set_plot_params(self, data, plot_inputs, ms_name):
        '''
        Set parameters needed for raster plot from data and plot inputs.
            data (xarray Dataset): selected dataset of MSv4 data to plot
            plot_inputs (dict): user inputs to plot.
        '''
        self._plot_params['data']['correlated_data'] = plot_inputs['correlated_data']
        self._plot_params['data']['aggregator'] = plot_inputs['aggregator']

        color_mode = plot_inputs['color_mode']
        if color_mode == 'manual':
            self._plot_params['plot']['color_limits'] = plot_inputs['color_range']
        elif color_mode == 'auto':
            self._plot_params['plot']['color_limits'] = plot_inputs['auto_color_range']
        else:
            self._plot_params['plot']['color_limits'] = None

        # Set title from user inputs or auto (ms name and iterator value)
        if plot_inputs['title']:
            title = plot_inputs['title']
            if title in ['ms', "'ms'"]:
                self._plot_params['plot']['title'] = self._get_plot_title(data, plot_inputs, ms_name)
            else:
                self._plot_params['plot']['title'] = title
        else:
            self._plot_params['plot']['title'] = ''

        # Set x, y, c axis labels and ticks
        self._set_axis_labels(data, plot_inputs)

        self._plot_params['plot']['params'] = True

    def reset_plot_params(self):
        ''' Remove and invalidate data plot params '''
        self._plot_params['plot'] = {'params': False}

    def raster_plot(self, data, logger, is_gui=False):
        ''' Create raster plot (hvPlot) for input data (xarray Dataset) using plot params.
            Returns Overlay of unflagged and flagged plots.
            Optionally add the unflagged data min/max to plot params for interactive gui colorbar range.
        '''
        if not self._plot_params['plot']['params']:
            logger.error('Parameters have not been set from plot data. Cannot plot.')
            return None

        data_params = self._plot_params['data']
        plot_params = self._plot_params['plot']

        x_axis = plot_params['axis_labels']['x']['axis']
        y_axis = plot_params['axis_labels']['y']['axis']
        c_axis = plot_params['axis_labels']['c']['axis']

        # Set plot axes to numeric coordinates if needed
        xds = set_index_coordinates(data, (x_axis, y_axis))

        # Prefix c_axis name with aggregator
        xda_name = c_axis
        if data_params['aggregator']:
            xda_name = "_".join([data_params['aggregator'], xda_name])

        # Plot unflagged and flagged data
        xda = xds[data_params['correlated_data']].where(xds.FLAG == 0.0).rename(xda_name)
        unflagged_plot = self._plot_xda(xda)
        flagged_xda = xds[data_params['correlated_data']].where(xds.FLAG == 1.0).rename("flagged_" + xda_name)
        flagged_plot = self._plot_xda(flagged_xda, True)

        if is_gui: # update data range for colorbar
            self._plot_params['data']['data_range'] = (xda.min().values.item(), xda.max().values.item())

        # Make Overlay plot with hover tools
        return (flagged_plot * unflagged_plot).opts(
            hv.opts.QuadMesh(tools=['hover'])
        )

    def _get_plot_title(self, data, plot_inputs, ms_name, include_selections=False):
        ''' Form string containing ms name and selected values using data (xArray Dataset) '''
        title = f"{ms_name}\n"

        if include_selections:
            # TBD: include complete selection?
            title = self._add_title_selections(data, title, plot_inputs)
        else:
            # Add iter_axis selection only
            iter_axis = plot_inputs['iter_axis']
            if iter_axis:
                iter_label = get_coordinate_labels(data, iter_axis)
                title += f"{iter_axis} {iter_label}"
        return title

    def _add_title_selections(self, data, title, plot_inputs):
        ''' Add ProcessingSet and data dimension selections to title '''
        selection = plot_inputs['selection'] if 'selection' in plot_inputs else None
        dim_selection = plot_inputs['dim_selection'] if 'dim_selection' in plot_inputs else None
        data_dims = plot_inputs['data_dims'] if 'data_dims' in plot_inputs else None

        ps_selections = []
        dim_selections = []

        for key in selection:
            # Add processing set selection: spw, field, source, and intent
            # TBD: add data group?
            if key == 'spw_name':
                spw_selection = f"spw: {selection[key]}"
                if 'frequency' in data:
                    spw_selection += f" ({data.frequency.spectral_window_id})"
                ps_selections.append(spw_selection)
            elif key == 'field_name':
                ps_selections.append(f"field: {selection[key]}")
            elif key == 'source_name':
                ps_selections.append(f"source: {selection[key]}")
            elif key == 'intents':
                ps_selections.append(f"intents: {selection[key]}")
            elif key in data_dims:
                # Add user-selected dimensions to title: name (index)
                label = get_coordinate_labels(data, key)
                index = selection[key] if isinstance(selection[key], int) else None
                selected_dim = f"{key}: {label}"
                if index is not None:
                    index_label = f" (ch {index}) " if key == 'frequency' else f" ({index}) "
                    selected_dim += index_label
                dim_selections.append(selected_dim)

        for key in dim_selection:
            # Add auto- or iter-selected dimensions to title: name (index)
            label = get_coordinate_labels(data, key)
            index = dim_selection[key] if isinstance(dim_selection[key], int) else None
            selected_dim = f"{key}: {label}"
            if index is not None:
                index_label = f" (ch {index}) " if key == 'frequency' else f" ({index}) "
                selected_dim += index_label
            dim_selections.append(selected_dim)

        title += '\n'.join(ps_selections) + '\n'
        title += '  '.join(dim_selections)
        return title

    def _set_axis_labels(self, data, plot_inputs):
        ''' Set axis, label, and ticks for x, y, and vis axis '''
        x_axis_labels = get_axis_labels(data, plot_inputs['x_axis'])
        y_axis_labels = get_axis_labels(data, plot_inputs['y_axis'])
        c_axis_labels = self._get_c_axis_labels(data, plot_inputs)

        self._set_axis_label_params('x', x_axis_labels)
        self._set_axis_label_params('y', y_axis_labels)
        self._set_axis_label_params('c', c_axis_labels)

    def _get_c_axis_labels(self, data, plot_inputs):
        ''' Set axis and label for c axis using input data xArray Dataset. '''
        data_group = plot_inputs['selection']['data_group_name']
        correlated_data = plot_inputs['correlated_data']
        vis_axis = plot_inputs['vis_axis']
        aggregator = plot_inputs['aggregator']

        axis, label = get_vis_axis_labels(data, data_group, correlated_data, vis_axis)
        if aggregator:
            label = " ".join([aggregator.capitalize(), label])
        return (axis, label, None)

    def _set_axis_label_params(self, axis, axis_labels):
        # Axis labels are (axis, label, ticks).
        if 'axis_labels' not in self._plot_params['plot']:
            self._plot_params['plot']['axis_labels'] = {}
        self._plot_params['plot']['axis_labels'][axis] = {}
        self._plot_params['plot']['axis_labels'][axis]['axis'] = axis_labels[0]
        self._plot_params['plot']['axis_labels'][axis]['label'] = axis_labels[1]
        self._plot_params['plot']['axis_labels'][axis]['ticks'] = axis_labels[2]

    def _plot_xda(self, xda, is_flagged=False):
        # Returns Quadmesh plot if raster 2D data, Scatter plot if raster 1D data, or None if no data
        plot_params = self._plot_params['plot']
        style_params = self._plot_params['style']

        x_axis = plot_params['axis_labels']['x']['axis']
        y_axis = plot_params['axis_labels']['y']['axis']
        c_label = plot_params['axis_labels']['c']['label']
        c_lim = plot_params['color_limits']

        x_formatter = get_time_formatter() if x_axis == 'time' else None
        y_formatter = get_time_formatter() if y_axis == 'time' else None

        # Hide flagged colorbar if unflagged colorbar is shown
        if xda.count().values > 0:
            if is_flagged:
                show_colorbar = style_params['show_flagged_colorbar']
            else :
                show_colorbar = style_params['show_colorbar']
        else:
            show_colorbar = False

        if is_flagged:
            c_label = "Flagged " + c_label
            colormap = style_params['flagged_cmap']
            plot_params['flagged_colorbar'] = show_colorbar
        else:
            colormap = style_params['unflagged_cmap']
            plot_params['unflagged_colorbar'] = show_colorbar

        if xda[x_axis].size > 1 and xda[y_axis].size > 1:
            # Raster 2D data
            plot = xda.hvplot.quadmesh(
                x_axis,
                y_axis,
                clim=c_lim,
                cmap=colormap,
                clabel=c_label,
                title=plot_params['title'],
                xlabel=plot_params['axis_labels']['x']['label'],
                ylabel=plot_params['axis_labels']['y']['label'],
                xformatter=x_formatter,
                yformatter=y_formatter,
                xticks=plot_params['axis_labels']['x']['ticks'],
                yticks=plot_params['axis_labels']['y']['ticks'],
                rot=45, # angle for x axis labels
                colorbar=show_colorbar,
                responsive=True, # resize to fill browser window if True
            )
        else:
            # Cannot raster 1D data, use scatter from pandas dataframe
            df = xda.to_dataframe().reset_index() # convert x and y axis from index to column
            plot = df.hvplot.scatter(
                x=x_axis,
                y=y_axis,
                c=xda.name,
                clim=plot_params['color_limits'],
                cmap=colormap,
                clabel=c_label,
                title=plot_params['title'],
                xlabel=plot_params['axis_labels']['x']['label'],
                ylabel=plot_params['axis_labels']['y']['label'],
                xformatter=x_formatter,
                yformatter=y_formatter,
                xticks=plot_params['axis_labels']['x']['ticks'],
                yticks=plot_params['axis_labels']['y']['ticks'],
                rot=45,
                marker='s', # square
                hover=True,
                responsive=True,
            )

        if show_colorbar and not is_flagged:
            plot = plot.opts(colorbar_position='left')
        return plot
