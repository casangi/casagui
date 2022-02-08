"""
part of plotants module
"""

from bokeh.models import ColumnDataSource
from bokeh.models.expressions import PolarTransform


def plotants_logpos():
    """
    Makes a logpos plot for plotants
    Returns:

    """
    # code from pipeline summary.py
    # PlotAntsChart draw_polarlog_ant_map_in_subplot
    if "VLA" in telescope:
        # For (E)VLA, set a fixed local center position that has been
        # tuned to work well for its array configurations (CAS-7479).
        xcenter, ycenter = -32, 0
        rmin_min, rmin_max = 12.5, 350
    else:
        # For non-(E)VLA, take the median of antenna offsets as the
        # center for the plot.
        xcenter = np.median(xpos)
        ycenter = np.median(ypos)
        rmin_min, rmin_max = 3, 350

    # Derive radial offset w.r.t. center position.
    r = ((xpos - xcenter) ** 2 + (ypos - ycenter) ** 2) ** 0.5
    # Set rmin, clamp between a min and max value, ignore station
    # at r=0 if one is there.
    rmin = min(rmin_max, max(rmin_min, 0.8 * np.min(r[r > 0])))
    # Update r to move any points below rmin to r=rmin.
    r[r <= rmin] = rmin
    rmin = np.log(rmin)
    # Set rmax.
    rmax = np.log(1.5 * np.max(r))
    # Derive angle of offset w.r.t. center position.
    theta = np.arctan2(xpos - xcenter, ypos - ycenter)
    source = ColumnDataSource(data=dict(r=[], theta=[], labels=[]))
    source.data = dict(r=r, theta=theta, labels=names)
    # https://github.com/bokeh/bokeh/issues/657
    # https://stackoverflow.com/questions/56343933/bokeh-second-legend-showing-scatter-radius
    plot = figure(plot_height=400, plot_width=400, x_axis_type=None, y_axis_type=None)
    # polarx = CustomJSTransform(
    #     args=dict(source=source),
    #     v_func="""
    #     const new_xs = new Array(source.data.r.length)
    #     for(var i = 0; i < new_xs.length; i++) {
    #         new_xs[i] = source.data.r[i] * Math.sin(source.data.theta[i] )
    #     }
    #     return new_xs
    #     """)
    # polary = CustomJSTransform(
    #     args=dict(source=source),
    #     v_func="""
    #     const new_ys = new Array(source.data.r.length)
    #     for(var i = 0; i < new_ys.length; i++) {
    #         new_ys[i] = source.data.r[i] * Math.cos(source.data.theta[i] )
    #     }
    #     return new_ys
    #     """)
    # plot.scatter(
    #     x=transform("r", polarx),
    #     y=transform("r", polary),
    #     source=source,
    #     size=5,
    #     line_color="red",
    #     fill_color="red",
    #     fill_alpha=0.5,
    # )
    # # draw circles
    # show_circle = True
    # circles = [1e5, 3e5, 1e6, 3e6, 1e7] if telescope == "VLBA" else [30, 100, 300, 10000]
    # circles_inner_list = []
    # circles_outer_list = []
    # for circle in circles:
    #     if circle > np.min(r) and show_circle:
    #         if circle < 1000:
    #             circles_inner_list.append(circle)
    #         else:
    #             circles_outer_list.append(circle)
    #     if np.log(circle) > rmax:
    #         show_circle = False
    #
    # plot.circle(0, 0, radius=circles_inner_list, fill_color=None, line_color="black")
    # plot.circle(0, 0, radius=circles_outer_list, fill_color=None, line_color="black")
    # circles_inner_list_labels = [str(r) + "m" for r in circles_inner_list[:-1]]
    # circles_outer_list_labels = [str(r) + "m" for r in circles_outer_list[:-1]]
    # plot.text(0, circles_inner_list[:-1], circles_inner_list_labels, text_font_size="11px", text_align="center", text_baseline="middle")
    # plot.text(0, circles_inner_list[:-1], circles_outer_list_labels, text_font_size="11px", text_align="center", text_baseline="middle")

    t = PolarTransform()
    plot.scatter(
        x=t.x,
        y=t.y,
        source=source,
        size=5,
        line_color="red",
        fill_color="red",
        fill_alpha=0.5,
    )

    # labels = LabelSet(x=transform("r", polarx), y=transform("r", polary), text="labels", x_offset=5, y_offset=5, source=source)
    # labels = LabelSet(x=t.x, y=t.y, text="labels", x_offset=5, y_offset=5, source=source)
    plot.title.text = telescope
    # plot.add_layout(labels)
    return plot
