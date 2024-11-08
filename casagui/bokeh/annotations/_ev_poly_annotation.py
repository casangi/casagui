from bokeh.models import PolyAnnotation

class EvPolyAnnotation(PolyAnnotation):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
