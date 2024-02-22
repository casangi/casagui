from bokeh.models import TextInput

class EvTextInput(TextInput):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
