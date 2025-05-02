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
from casagui.plot._xds_plot_axes import get_axis_labels, get_vis_axis_labels, get_coordinate_labels

class RasterPlot:
    '''
        Class to create a raster plot from MS data.
        Implemented with xArray Dataset and hvPlot, but could change data and plotting backends using same interface.
    '''

    def __init__(self):
        self._plot_params = {'data': {'params': False}}
        self._spw_color_limits = {}
        self.set_style_params() # use defaults unless set externally

    def set_style_params(self, unflagged_cmap='Viridis', flagged_cmap='Reds',  show_colorbar=True):
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
        self._plot_params['unflagged_cmap'] = unflagged_cmap
        self._plot_params['flagged_cmap'] = flagged_cmap
        self._plot_params['colorbar'] = {'show': show_colorbar}

    def get_plot_params(self):
        ''' Return dict of plot params (default only if data params not set) '''
        return self._plot_params

    def set_data_params(self, data, plot_inputs):
        '''
        Set parameters needed for raster plot from data and plot inputs.
            data (xarray Dataset): selected dataset of MSv4 data to plot
            plot_inputs (dict): user inputs to plot.
        '''
        # Set plot params from inputs
        self._plot_params['data']['correlated_data'] = plot_inputs['correlated_data']
        self._plot_params['data']['aggregator'] = plot_inputs['aggregator']
        self._plot_params['data']['color_limits'] = plot_inputs['color_limits']

        # Set title from user inputs or auto (ms name and iterator value)
        if plot_inputs['title']:
            self._plot_params['data']['title'] = plot_inputs['title']
        else:
            self._plot_params['data']['title'] = self._get_plot_title(plot_inputs, data)

        # Set x, y, c axis labels and ticks
        self._set_axis_labels(data, plot_inputs)

        self._plot_params['data']['params'] = True

    def reset_data_params(self):
        ''' Remove and invalidate data plot params '''
        self._plot_params['data'] = {'params': False}

    def raster_plot(self, data, logger, get_data_range=False):
        ''' Create raster plot (hvPlot) for input data (xarray Dataset) using plot params.
            Returns Overlay of unflagged and flagged plots and optionally plot info for interactive plot.
            Plot info includes plot parameters for colorbar title and the unflagged data min/max for colorbar range.
        '''
        if not self._plot_params['data']['params']:
            logger.error('Parameters have not been set from plot data. Cannot plot.')
            return None

        data_params = self._plot_params['data']
        x_axis = data_params['axis_labels']['x']['axis']
        y_axis = data_params['axis_labels']['y']['axis']
        c_axis = data_params['axis_labels']['c']['axis']

        # Set plot axes to numeric coordinates if needed
        xds = set_index_coordinates(data, (x_axis, y_axis))

        # Unflagged and flagged data.  Use same name, for histogram dimension.
        # c axis labels are (axis, label)
        xda_name = c_axis
        if data_params['aggregator']:
            xda_name = "_".join([data_params['aggregator'], xda_name])
        xda = xds[data_params['correlated_data']].where(xds.FLAG == 0.0).rename(xda_name)
        flagged_xda = xds[data_params['correlated_data']].where(xds.FLAG == 1.0).rename("flagged_" + xda_name)

        # Plot data and make Overlay plot with hover tools
        unflagged_plot = self._plot_xda(xda)
        flagged_plot = self._plot_xda(flagged_xda, True)
        plot = (flagged_plot * unflagged_plot).opts(
            hv.opts.QuadMesh(tools=['hover'])
        )

        # Return data range in plot params if requested
        if get_data_range:
            self._add_data_range(xda)

        return plot, self._plot_params

    def _get_plot_title(self, plot_inputs, data, include_selections=False):
        ''' Form string containing ms name and selected values using data (xArray Dataset) '''
        title = f"{plot_inputs['ms_name']}\n"

        if include_selections:
            # TBD: include complete selection?
            title = self._add_title_selections(data, title, plot_inputs)
        else:
            # Add iter_axis selection only
            iter_axis = plot_inputs['iter_axis']
            if iter_axis and 'dim_selection' in plot_inputs and iter_axis in plot_inputs['dim_selection']:
                title += f"{iter_axis} {plot_inputs['dim_selection'][iter_axis]}"
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
        data_group = plot_inputs['selection']['data_group']
        correlated_data = plot_inputs['correlated_data']
        vis_axis = plot_inputs['vis_axis']
        aggregator = plot_inputs['aggregator']

        axis, label = get_vis_axis_labels(data, data_group, correlated_data, vis_axis)
        if aggregator:
            label = " ".join([aggregator.capitalize(), label])
        return (axis, label, None)

    def _set_axis_label_params(self, axis, axis_labels):
        # Axis labels are (axis, label, ticks).
        if 'axis_labels' not in self._plot_params['data']:
            self._plot_params['data']['axis_labels'] = {}
        self._plot_params['data']['axis_labels'][axis] = {}
        self._plot_params['data']['axis_labels'][axis]['axis'] = axis_labels[0]
        self._plot_params['data']['axis_labels'][axis]['label'] = axis_labels[1]
        self._plot_params['data']['axis_labels'][axis]['ticks'] = axis_labels[2]

    def _plot_xda(self, xda, is_flagged=False):
        # Returns Quadmesh plot if raster 2D data, Scatter plot if raster 1D data, or None if no data
        data_params = self._plot_params['data']
        x_axis = data_params['axis_labels']['x']['axis']
        y_axis = data_params['axis_labels']['y']['axis']
        c_label = data_params['axis_labels']['c']['label']

        x_formatter = get_time_formatter() if x_axis == 'time' else None
        y_formatter = get_time_formatter() if y_axis == 'time' else None
        # Hide flagged colorbar if unflagged colorbar is shown
        if is_flagged and self._plot_params['colorbar']['unflagged']:
            show_colorbar = False
        else:
            show_colorbar = self._plot_params['colorbar']['show'] and (xda.count().values > 0)

        if is_flagged:
            c_label = "Flagged " + c_label
            colormap = self._plot_params['flagged_cmap']
            self._plot_params['colorbar']['flagged'] = show_colorbar # return value for interactive plot

        else:
            colormap = self._plot_params['unflagged_cmap']
            self._plot_params['colorbar']['unflagged'] = show_colorbar # return value for interactive plot

        if xda[x_axis].size > 1 and xda[y_axis].size > 1:
            # Raster 2D data
            return xda.hvplot.quadmesh(
                x_axis,
                y_axis,
                clim=data_params['color_limits'],
                cmap=colormap,
                clabel=c_label,
                title=data_params['title'],
                xlabel=data_params['axis_labels']['x']['label'],
                ylabel=data_params['axis_labels']['y']['label'],
                xformatter=x_formatter,
                yformatter=y_formatter,
                xticks=data_params['axis_labels']['x']['ticks'],
                yticks=data_params['axis_labels']['y']['ticks'],
                rot=45, # angle for x axis labels
                colorbar=show_colorbar,
            )

        # Cannot raster 1D data, use scatter from pandas dataframe
        df = xda.to_dataframe().reset_index() # convert x and y axis from index to column
        return df.hvplot.scatter(
            x=x_axis,
            y=y_axis,
            c=data_params['axis_labels']['c']['axis'],
            clim=data_params['color_limits'],
            cmap=colormap,
            clabel=c_label,
            title=data_params['title'],
            xlabel=data_params['axis_labels']['x']['label'],
            ylabel=data_params['axis_labels']['y']['label'],
            xformatter=x_formatter,
            yformatter=y_formatter,
            xticks=data_params['axis_labels']['x']['ticks'],
            yticks=data_params['axis_labels']['y']['ticks'],
            rot=45,
            marker='s', # square
            hover=True,
        )

    def _add_data_range(self, xda):
        ''' Add data min/max to plot params and set color limits to this range '''
        data_min = xda.min().values.item()
        data_max = xda.max().values.item()
        self._plot_params['data']['data_min'] = data_min
        self._plot_params['data']['data_max'] = data_max
        if not self._plot_params['data']['color_limits']:
            self._plot_params['data']['color_limits'] = (data_min, data_max)
