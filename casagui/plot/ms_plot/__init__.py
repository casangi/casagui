''' This module contains classes and utilities to support MS plotting '''

from ._ms_plot import MsPlot

from ._ms_plot_constants import (
    SPECTRUM_AXIS_OPTIONS,
    UVW_AXIS_OPTIONS,
    VIS_AXIS_OPTIONS,
    WEIGHT_AXIS_OPTIONS,
    PS_SELECTION_OPTIONS,
    MS_SELECTION_OPTIONS,
    AGGREGATOR_OPTIONS,
    DEFAULT_UNFLAGGED_CMAP,
    DEFAULT_FLAGGED_CMAP,
)

from ._ms_plot_selectors import (
    file_selector,
    title_selector,
    style_selector,
    axis_selector,
    aggregation_selector,
    iteration_selector,
    selection_selector,
    plot_starter,
)

from ._raster_plot_inputs import check_inputs
from ._raster_plot import RasterPlot
