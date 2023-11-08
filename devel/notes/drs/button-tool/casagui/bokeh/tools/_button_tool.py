from bokeh.models.tools import PlotActionTool

class ButtonTool(PlotActionTool):
    ''' *toolbar icon*: |reset_icon|

    The reset tool is an action. When activated in the toolbar, the tool resets
    the data bounds of the plot to their values when the plot was initially
    created.

    .. |reset_icon| image:: /_images/icons/Reset.png
        :height: 24px
        :alt: Icon of two arrows on a circular arc forming a circle representing the reset tool in the toolbar.

    '''

    # explicit __init__ to support Init signatures
    def __init__(self, *args, **kwargs) -> None:
        #if len(args) > 0:
        #    raise ValueError('positional arguments are not supported for ButtonTool')
        #if "icon" not in kwargs:
        #    # all tools have an icon property
        #    kwargs['icon'] = '.bk-tool-icon-unknown'
        super().__init__(*args, **kwargs)
