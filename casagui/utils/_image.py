from os.path import isfile
from io import BytesIO
from pathlib import Path
import PIL.Image
import base64

def image_as_mime( path ):

    value = path
    if isinstance( value, str ) and isfile(value):
        value = Path(value)

    if isinstance( value, Path ):
        value = PIL.Image.open(value)

    if isinstance( value, PIL.Image.Image ):
        out = BytesIO()
        fmt = value.format or "PNG"
        value.save(out, fmt)
        encoded = base64.b64encode( out.getvalue() ).decode( 'ascii' )
        return f"data:image/{fmt.lower()};base64,{encoded}"

    raise RuntimeError( f'''could not load {path}''' )
