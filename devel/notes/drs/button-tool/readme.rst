CustomAction
============

It can be difficult to discover the widgets available within Bokeh. I had to create a
`Tip <https://github.com/casangi/casagui/blob/main/casagui/bokeh/models/_tip.py>`_ widget.
I did this after I had already created a `TipButton <https://github.com/casangi/casagui/blob/main/casagui/bokeh/models/_tip_button.py>`_.
It could probably be argued that the :code:`TipButton` is now redundant, but it is not
clear whether it is best to have an intermediate widget just for wrapping :code:`Tooltips`
so I left both.

I was in the process of creating a `ButtonTool <https://github.com/casangi/casagui/blob/main/devel/notes/drs/button-tool/casagui/bokeh/tools/_button_tool.py>`_
when I discovered the `CustomAction <https://github.com/bokeh/bokeh/blob/branch-3.4/tests/integration/tools/test_custom_action.py>`_.
This **does** make a :code:`ButtonTool` redundant, but I preserved the implementation
here for future reference.
