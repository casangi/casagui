#!/usr/bin/env python3
import os
import numpy as np
import plotly.express as px

from bokeh.io import export_png, export_svgs
from bokeh.models import ColumnDataSource, LabelSet, CustomJSTransform
from bokeh.models.expressions import PolarTransform
from bokeh.plotting import figure, show
from bokeh.transform import transform

from casatools import table, msmetadata, quanta, ms, measures


def __getPlotantsObservatoryInfo(msname):
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
    metadata = msmetadata()
    metadata.open(msname)
    telescope = metadata.observatorynames()[0]
    arrayPos = metadata.observatoryposition()
    metadata.close()
    return telescope, arrayPos


def __getPlotantsAntennaInfo(msname, log, exclude, checkbaselines):
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
    tb = table()
    me = measures()
    qa = quanta()

    telescope, arrayPos = __getPlotantsObservatoryInfo(msname)
    arrayWgs84 = me.measure(arrayPos, "WGS84")
    arrayLon, arrayLat, arrayAlt = [arrayWgs84[i]["value"] for i in ["m0", "m1", "m2"]]

    # Open the ANTENNA subtable to get the names of the antennas in this MS and
    # their positions.  Note that the entries in the ANTENNA subtable are pretty
    # much in random order, so antNames translates between their index and name
    # (e.g., index 11 = STD155).  We'll need these indices for later, since the
    # main data table refers to the antennas by their indices, not names.

    anttabname = msname + "/ANTENNA"
    tb.open(anttabname)
    # Get antenna names from antenna table
    antNames = np.array(tb.getcol("NAME")).tolist()
    stationNames = np.array(tb.getcol("STATION")).tolist()
    if telescope == "VLBA":  # names = ant@station
        antNames = ["@".join(antsta) for antsta in zip(antNames, stationNames)]
    # Get antenna positions from antenna table
    antPositions = np.array(
        [
            me.position("ITRF", qa.quantity(x, "m"), qa.quantity(y, "m"), qa.quantity(z, "m"))
            for (x, y, z) in tb.getcol("POSITION").transpose()
        ]
    )
    tb.close()

    allAntIds = range(len(antNames))
    if checkbaselines:
        # Get antenna ids from main table; this will add to runtime
        tb.open(msname)
        ants1 = tb.getcol("ANTENNA1")
        ants2 = tb.getcol("ANTENNA2")
        tb.close()
        antIdsUsed = list(set(np.append(ants1, ants2)))
    else:
        # use them all!
        antIdsUsed = allAntIds

    # handle exclude -- remove from antIdsUsed
    for antId in exclude:
        try:
            antNameId = antNames[antId] + " (id " + str(antId) + ")"
            antIdsUsed.remove(antId)
            casalog.post("Exclude antenna " + antNameId)
        except ValueError:
            casalog.post("Cannot exclude antenna " + antNameId + ": not in main table", "WARN")

    # apply antIdsUsed mask
    antNames = [antNames[i] for i in antIdsUsed]
    antPositions = [antPositions[i] for i in antIdsUsed]
    stationNames = [stationNames[i] for i in antIdsUsed]

    nAnts = len(antIdsUsed)
    # casalog.post("Number of points being plotted: " + str(nAnts))
    if nAnts == 0:  # excluded all antennas
        return telescope, antNames, [], [], []

    # Get the names, indices, and lat/lon/alt coords of "good" antennas.
    antWgs84s = np.array([me.measure(pos, "WGS84") for pos in antPositions])

    # Convert from lat, lon, alt to X, Y, Z (unless VLBA)
    # where X is east, Y is north, Z is up,
    # and 0, 0, 0 is the center
    # Note: this conversion is NOT exact, since it doesn't take into account
    # Earth's ellipticity!  But it's close enough.
    if telescope == "VLBA" and not log:
        antLons, antLats = [[pos[i] for pos in antWgs84s] for i in ["m0", "m1"]]
        antXs = [qa.convert(lon, "deg")["value"] for lon in antLons]
        antYs = [qa.convert(lat, "deg")["value"] for lat in antLats]
    else:
        antLons, antLats = [np.array([pos[i]["value"] for pos in antWgs84s]) for i in ["m0", "m1"]]
        radE = 6370000.0
        antXs = (antLons - arrayLon) * radE * np.cos(arrayLat)
        antYs = (antLats - arrayLat) * radE
    return telescope, antNames, antIdsUsed, antXs, antYs, stationNames


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
    source = ColumnDataSource(data=dict(x=[], y=[], labels=[]))
    source.data = dict(x=xpos, y=ypos, labels=names)
    labels = LabelSet(x="x", y="y", text="labels", x_offset=5, y_offset=5, source=source)
    plot = figure(plot_height=400, plot_width=400)
    plot.scatter("x", "y", source=source, size=5, line_color="red", fill_color="red", fill_alpha=0.5)
    plot.title.text = telescope
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
        raise Exception("Visibility file %s does not exist" % vis)  # could be a print + return
    # remove trailing / for title basename
    if vis.endswith("/"):
        vis = vis[:-1]

    myms = ms()
    try:
        exclude = myms.msseltoindex(vis, baseline=exclude)["antenna1"].tolist()
    except RuntimeError as rterr:  # MSSelection failed
        errmsg = str(rterr)
        errmsg = errmsg.replace("specificion", "specification")
        errmsg = errmsg.replace("Antenna Expression: ", "")
        raise RuntimeError("Exclude selection error: " + errmsg)

    # Get the antenna positions
    telescope, names, ids, xpos, ypos, stations = __getPlotantsAntennaInfo(vis, logpos, exclude, checkbaselines)
    if not names:
        raise ValueError("No antennas selected. Exiting plotants.")

    if title != "":
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
            from cairosvg import svg2pdf

            fig.output_backend = "svg"
            export_svgs(fig, filename=figfile.replace(".pdf", ".svg"))
            svg2pdf(url=figfile.replace(".pdf", ".svg"), write_to=figfile)
            os.system("rm " + figfile.replace(".pdf", ".svg"))
        else:
            raise ValueError("Invalid output file type.  Must be .png or .svg or .pdf")
