
Background
----------

It seemed like a good idea to have a tooltip that was context sensitive.
In this case, it was for the **Stop** button in interactive clean. The idea
was that when the button was red (*meaning that clicking it would cause
interactive clean to exit back to Python*) the tooltip would be
emphatic. When the button was orange (*meaning stop after the current major
cycle*), it would be a plain tooltip. The hook for the change was a
:code:`predisplay` callback function. This function would change the tooltip
based upon the :code:`button_type` of the **Stop** button.

The Rub
-------

This seemed like a good plan, but it turns out that the implementation of the
:code:`HelpButton` and by extension my :code:`TipButton` (which is a
:code:`HelpButton` that can also have a :code:`js_on_click` callback to do
something useful) have the displayed :code:`tooltip` member as part of the
:code:`TipButtonView` instead of in the :code:`TipButton` model (where it
also is found). So the :code:`predisplay` callback might look like::

  stop.predisplay = CustomJS( code='''console.log('>>>>>---enter---->>', cb_obj.tooltip)
                                      cb_obj.tooltip.content.innerHTML = '<b>nothing</b> good will come of this'
                                   ''' )

this **does work** but it leaves the model and the view with skewed state.
Both could possibly be patched up, but this seems like a bad path, and
I don't know how to rebuild the whole :code:`TipButton` model/view ensamble.

Creating A Tooltip
------------------

This code does not compile because a :code:`Tooltip` does **not** have a
:code:`model` member. That's a :code:`TooltipView`::

   export function tooltip_from_html( tooltip: Tooltip, new_html: string ) {
      const { target, position, attachment, show_arrow, closable, interactive } = tooltip
      let result = new Tooltip( { content: new HTML( { html: new_html } ),
                                  target, position, attachment, show_arrow, closable, interactive } )
      result.model = tooltip.model
      return result
   }

So this could conceivably work for creating one :code:`TooltipView`
from another. However, this was where I realized that changing a tooltip
was a bigger problem than it was worth for the interactive clean stop button.
