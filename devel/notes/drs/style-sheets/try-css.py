from bokeh.layouts import column, row
from bokeh.plotting import show
from bokeh.models.ui.tooltips import Tooltip
from bokeh.models import InlineStyleSheet, Slider, TextInput, ColorPicker, Button
from bokeh.models.ui.icons import SVGIcon

stylesheet = InlineStyleSheet(css=".bk-slider-title { background-color: lightgray; }")
slider = Slider(value=10, start=0, end=100, step=0.5, stylesheets=[stylesheet])

stylesheet = InlineStyleSheet(css=".bk-slider-title { background-color: lightgray; }")
slider = Slider(value=10, start=0, end=100, step=0.5, stylesheets=[stylesheet])

ti = TextInput( title='input', value="", width=400, width_policy='min',
                stylesheets=[ InlineStyleSheet( css='''.bk-input { border: 0px solid #ccc; border-bottom: 5px solid black; }''' ) ] )
#               stylesheets=[ InlineStyleSheet( css='''.bk-input { background-color: red; }''' ) ] )            # works
#               stylesheets=[ InlineStyleSheet( css='''.bk-input { border: 0px solid #ccc; }''' ) ] )           # works

cp = ColorPicker( width_policy='fixed', width=40, color='#00FF00', margin=(-1, 0, 0, 0),
                  stylesheets=[ InlineStyleSheet( css='''.bk-input { border: 0px solid #ccc;  padding: 0 var(--padding-vertical); }''' ) ] )

tp = Button( label='', icon=SVGIcon( svg='''<svg version="1.1" id="Layer_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px"
	 viewBox="0 0 16 16" enable-background="new 0 0 16 16" xml:space="preserve">
<g id="application_1_">
	<g>
		<path fill-rule="evenodd" clip-rule="evenodd" d="M3.5,7h7C10.78,7,11,6.78,11,6.5C11,6.22,10.78,6,10.5,6h-7C3.22,6,3,6.22,3,6.5
			C3,6.78,3.22,7,3.5,7z M15,1H1C0.45,1,0,1.45,0,2v12c0,0.55,0.45,1,1,1h14c0.55,0,1-0.45,1-1V2C16,1.45,15.55,1,15,1z M14,13H2V5
			h12V13z M3.5,9h4C7.78,9,8,8.78,8,8.5C8,8.22,7.78,8,7.5,8h-4C3.22,8,3,8.22,3,8.5C3,8.78,3.22,9,3.5,9z M3.5,11h5
			C8.78,11,9,10.78,9,10.5C9,10.22,8.78,10,8.5,10h-5C3.22,10,3,10.22,3,10.5C3,10.78,3.22,11,3.5,11z"/>
	</g>
</g>
</svg>''' ), stylesheets=[ InlineStyleSheet( css='''.bk-btn { border: 0px solid #ccc;  padding: 0 var(--padding-vertical) var(--padding-horizontal); }''' ) ] )

show( column( slider,
              ti,
              row( ti, slider ),
              cp,
              tp ) )
