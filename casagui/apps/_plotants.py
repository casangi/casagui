########################################################################
#
# Copyright (C) 2022
# Associated Universities, Inc. Washington DC, USA.
#
# This script is free software; you can redistribute it and/or modify it
# under the terms of the GNU Library General Public License as published by
# the Free Software Foundation; either version 2 of the License, or (at your
# option) any later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Library General Public
# License for more details.
#
# You should have received a copy of the GNU Library General Public License
# along with this library; if not, write to the Free Software Foundation,
# Inc., 675 Massachusetts Ave, Cambridge, MA 02139, USA.
#
# Correspondence concerning AIPS++ should be adressed as follows:
#        Internet email: aips2-request@nrao.edu.
#        Postal address: AIPS++ Project Office
#                        National Radio Astronomy Observatory
#                        520 Edgemont Road
#                        Charlottesville, VA 22903-2475 USA
#
########################################################################
"""
plotants module
"""

import os

import numpy as np
from bokeh.io import export_png, export_svgs
from bokeh.models import ColumnDataSource, LabelSet
from bokeh.plotting import figure, show

try:
    from cairosvg import svg2pdf
    _have_svg2pdf = True
except ImportError:
    _have_svg2pdf = False

try:
    import casatools as ct
    from casatools import table, msmetadata, quanta, ms, measures
except:
    ct = None
    from casagui.utils import warn_import
    warn_import('casatools')

_FIGURE_PLOT_WIDTH = 450
_FIGURE_PLOT_HEIGHT = 450


def __get_observatory_info(msname):
    """Extract the observatory information from `msname`.

    Parameters
    ----------
    msname: string
        Path to a CASA measurement set.

    Returns
    -------
    ( string, list )
        string is the telescope name and the list is the array position
    """
    metadata = ct.msmetadata()
    metadata.open(msname)
    telescope = metadata.observatorynames()[0]
    positions = metadata.observatoryposition()
    metadata.close()
    return telescope, positions


def __get_antenna_info(msname, log, exclude, checkbaselines):
    """Return the antenna position info.

    Parameters
    ----------
    msname: string
        Path to the CASA measurement set.
    log: boolean
        whether to plot logarithmic positions
    exclude: [ int ]
        list antenna name/id selection to exclude from plot
    checkbaselines: boolean
        whether to check baselines in the main table
    """
    if ct is None:
        raise RuntimeError('casatools is not available')

    me = ct.measures()
    qa = ct.quanta()
    tb = ct.table()

    telescope, positions = __get_observatory_info(msname)
    positions_wgs84 = me.measure(positions, "WGS84")
    array_lon, array_lat, = [positions_wgs84[i]["value"] for i in ["m0", "m1", "m2"]]

    # Open the ANTENNA subtable to get the names of the antennas in this MS and
    # their positions.  Note that the entries in the ANTENNA subtable are pretty
    # much in random order, so antenna_names translates between their index and name
    # (e.g., index 11 = STD155).  We'll need these indices for later, since the
    # main data table refers to the antennas by their indices, not names.

    anttabname = msname + "/ANTENNA"
    tb.open(anttabname)
    # Get antenna names from antenna table
    antenna_names = np.array(tb.getcol("NAME")).tolist()
    station_names = np.array(tb.getcol("STATION")).tolist()
    if telescope == "VLBA":  # names = ant@station
        antenna_names = ["@".join(antsta) for antsta in zip(antenna_names, station_names)]
    # Get antenna positions from antenna table
    antenna_positions = np.array(
        [
            me.position("ITRF", qa.quantity(x, "m"), qa.quantity(y, "m"), qa.quantity(z, "m"))
            for (x, y, z) in tb.getcol("POSITION").transpose()
        ]
    )
    tb.close()

    all_ant_ids = range(len(antenna_names))
    if checkbaselines:
        # Get antenna ids from main table; this will add to runtime
        tb.open(msname)
        ants1 = tb.getcol("ANTENNA1")
        ants2 = tb.getcol("ANTENNA2")
        tb.close()
        ant_ids_used = list(set(np.append(ants1, ants2)))
    else:
        # use them all!
        ant_ids_used = all_ant_ids

    # handle exclude -- remove from ant_ids_used
    for ant_id in exclude:
        try:
            ant_name_id = antenna_names[ant_id] + " (id " + str(ant_id) + ")"
            ant_ids_used.remove(ant_id)
            casalog.post("Exclude antenna " + ant_name_id)
        except ValueError:
            casalog.post("Cannot exclude antenna " + ant_name_id + ": not in main table", "WARN")

    # apply ant_ids_used mask
    antenna_names = [antenna_names[i] for i in ant_ids_used]
    antenna_positions = [antenna_positions[i] for i in ant_ids_used]
    station_names = [station_names[i] for i in ant_ids_used]

    n_ants = len(ant_ids_used)
    # casalog.post("Number of points being plotted: " + str(n_ants))
    if n_ants == 0:  # excluded all antennas
        return telescope, antenna_names, [], [], [], []

    # Get the names, indices, and lat/lon/alt coords of "good" antennas.
    ant_wgs84s = np.array([me.measure(pos, "WGS84") for pos in antenna_positions])

    # Convert from lat, lon, alt to X, Y, Z (unless VLBA)
    # where X is east, Y is north, Z is up,
    # and 0, 0, 0 is the center
    # Note: this conversion is NOT exact, since it doesn't take into account
    # Earth's ellipticity!  But it's close enough.
    if telescope == "VLBA" and not log:
        ant_lons, ant_lats = [[pos[i] for pos in ant_wgs84s] for i in ["m0", "m1"]]
        ant_xs = [qa.convert(lon, "deg")["value"] for lon in ant_lons]
        ant_ys = [qa.convert(lat, "deg")["value"] for lat in ant_lats]
    else:
        ant_lons, ant_lats = [np.array([pos[i]["value"] for pos in ant_wgs84s]) for i in ["m0", "m1"]]
        rade = 6370000.0 # radE
        ant_xs = (ant_lons - array_lon) * rade * np.cos(array_lat)
        ant_ys = (ant_lats - array_lat) * rade
    return telescope, antenna_names, ant_ids_used, ant_xs, ant_ys, station_names


def __plot_antennas_log(telescope, names, ids, xpos, ypos, antindex, stations, title):
    raise NotImplementedError("This is a placeholder for another type of plot. It is not implemented yet.")


def __plot_antennas(telescope, names, ids, xpos, ypos, antindex, stations, title):
    if telescope == "VLBA":
        labelx = "Longitude (deg)"
        labely = "Latitude (deg)"
    else:
        # use m or km units
        units = " (m)"
        if np.median(xpos) > 1e6 or np.median(ypos) > 1e6:
            xpos /= 1e3
            ypos /= 1e3
            units = " (km)"
        labelx = "X" + units
        labely = "Y" + units
    if antindex:
        names = [f"{name} ({idx})" for name, idx in zip(names, ids)]
    source = ColumnDataSource(data=dict(x=[], y=[], labels=[]))
    source.data = dict(x=xpos, y=ypos, labels=names)
    labels = LabelSet(x="x", y="y", text="labels", x_offset=5, y_offset=5, source=source, text_font_size="10pt")
    plot = figure(plot_height=_FIGURE_PLOT_HEIGHT, plot_width=_FIGURE_PLOT_WIDTH)
    plot.scatter("x", "y", source=source, size=5, line_color="red", fill_color="red", fill_alpha=0.5)
    plot.title.text = title
    plot.xaxis[0].axis_label = labelx
    plot.yaxis[0].axis_label = labely
    plot.add_layout(labels)
    return plot


def plotants(vis, figfile="", antindex=False, logpos=False, exclude=[], checkbaselines=False, title="", showgui=True):
    """Plot the antenna distribution in the local reference frame:
    The location of the antennas in the MS will be plotted with
    X-toward local east; Y-toward local north.  The name of each
    antenna is shown next to its respective location.

    Parameters
    ----------
    vis: string
    Path to the input visibility file

    antindex: boolean, default: False
        Label antennas with name and antenna ID

    logpos: boolean, default: False
        Produce a logarithmic position plot.

    exclude: list, default: []
        antenna IDs or names to exclude from plotting, for example:
        exclude=[2,3,4], exclude=['DV15']

    checkbaselines: boolean, default: False
        Only plot antennas in the MAIN table. This can be useful after a split.
        WARNING:  Setting checkbaselines to True will add to runtime in proportion
        to the number of rows in the dataset.

    title: string, default: ''
        Title written along top of plot
    """
    if os.path.exists(vis) is False:
        raise Exception(f"Visibility file {vis} does not exist")  # could be a print + return
    # remove trailing / for title basename
    if vis.endswith("/"):
        vis = vis[:-1]

    myms = ct.ms()
    try:
        exclude = myms.msseltoindex(vis, baseline=exclude)["antenna1"].tolist()
    except RuntimeError as rterr:  # MSSelection failed
        errmsg = str(rterr)
        errmsg = errmsg.replace("specificion", "specification")
        errmsg = errmsg.replace("Antenna Expression: ", "")
        raise RuntimeError("Exclude selection error: " + errmsg) from rterr

    # Get the antenna positions
    telescope, names, ids, xpos, ypos, stations = __get_antenna_info(vis, logpos, exclude, checkbaselines)
    if not names:
        raise ValueError("No antennas selected. Exiting plotants.")

    if title == "":
        msname = os.path.basename(vis)
        title = "Antenna Positions for "
        if len(msname) > 55:
            title += "\n"
        title += msname

    if logpos:
        fig = __plot_antennas_log(telescope, names, ids, xpos, ypos, antindex, stations, title)
    else:
        fig = __plot_antennas(telescope, names, ids, xpos, ypos, antindex, stations, title)

    if showgui is not False:
        show(fig)

    if figfile != "":
        if figfile.endswith(".png"):
            export_png(fig, filename=figfile)
        elif figfile.endswith(".svg"):
            fig.output_backend = "svg"
            export_svgs(fig, filename=figfile)
        elif figfile.endswith(".pdf"):
            if _have_svg2pdf == True:
                fig.output_backend = "svg"
                export_svgs(fig, filename=figfile.replace(".pdf", ".svg"))
                svg2pdf(url=figfile.replace(".pdf", ".svg"), write_to=figfile)
                os.system("rm " + figfile.replace(".pdf", ".svg"))
            else:
                raise RuntimeError("cairosvg is required for generating PDF output, but it is not available")
        else:
            raise ValueError("Invalid output file type.  Must be .png or .svg or .pdf")
