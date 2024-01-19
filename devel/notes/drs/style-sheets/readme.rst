Cascading Style Sheets
==========================

Bokeh allows for customizing the layout of widgets using style sheets. To make this work, you must discover the style sheets that a given widget uses, e.g. :code:`.bk-btn` for buttons or :code:`.bk-input` for most input widgets (:code:`ColorPicker`, :code:`TextInput`, etc.). The place to find these include:

* looking at the HTML files produced from simple displays like :code:`try-css.py` in this directory
* looking at :code:`bokehjs/src/less/buttons.less` in the Bokeh source tree
* looking at :code:`bokehjs/src/less/widgets/inputs.less` in the Bokeh source tree
