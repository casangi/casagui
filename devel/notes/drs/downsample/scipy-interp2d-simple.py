'''
   DeprecationWarning:         `interp2d` is deprecated!
   `interp2d` is deprecated in SciPy 1.10 and will be removed in SciPy 1.13.0.

   For legacy code, nearly bug-for-bug compatible replacements are
   `RectBivariateSpline` on regular grids, and `bisplrep`/`bisplev` for
   scattered 2D data.

   In new code, for regular grids use `RegularGridInterpolator` instead.
   For scattered data, prefer `LinearNDInterpolator` or
   `CloughTocher2DInterpolator`.

   For more details see
   `https://scipy.github.io/devdocs/notebooks/interp_transition_guide.html`
'''
import warnings
import numpy as np
from scipy.interpolate import interp2d
from scipy import misc
from bokeh.plotting import figure, show, ColumnDataSource
from bokeh.layouts import row, column

arr = misc.face(gray=True)
arr = arr.transpose()
for x in range(50):
    for y in range(50):
        arr[0+x][0+y] = -1
for x in range(50):
    for y in range(50):
        arr[arr.shape[0]-1-x][arr.shape[1]-1-y] = 1

print( f'original: {arr.shape}' )

x = np.linspace(0, 1, arr.shape[0])
y = np.linspace(0, 1, arr.shape[1])
f = interp2d(y, x, arr, kind='cubic')

x2 = np.linspace(0, 1, 1000)
y2 = np.linspace(0, 1, 1600)
arr2 = f(y2, x2)
print( f'     big: {arr2.shape}' )

x3 = np.linspace(0, 1, 1000)
y3 = np.linspace(0, 1, 150)
arr3 = f( y3, x3 )
print( f'     odd: {arr3.shape}' )

x4 = np.linspace(0, 1, 100)
y4 = np.linspace(0, 1, 150)
arr4 = f( y4, x4 )
print( f'   small: {arr4.shape}' )

s_1 = ColumnDataSource( data=dict( img=[ arr ] ) )
p_1 = figure( )
i_1 = p_1.image( image='img', x=0, y=0, dw=arr.shape[0], dh=arr.shape[1], source=s_1, palette= 'Cividis256' )

s_2 = ColumnDataSource( data=dict( img=[ arr2 ] ) )
p_2 = figure( )
i_2 = p_2.image( image='img', x=0, y=0, dw=arr2.shape[0], dh=arr2.shape[1], source=s_2, palette= 'Cividis256' )

s_3 = ColumnDataSource( data=dict( img=[ arr3 ] ) )
p_3 = figure( )
i_3 = p_3.image( image='img', x=0, y=0, dw=arr3.shape[0], dh=arr3.shape[1], source=s_3, palette= 'Cividis256' )

s_4 = ColumnDataSource( data=dict( img=[ arr4 ] ) )
p_4 = figure( )
i_4 = p_4.image( image='img', x=0, y=0, dw=arr4.shape[0], dh=arr4.shape[1], source=s_4, palette= 'Cividis256' )

c = column( row( p_1, p_2 ),
            row( p_3, p_4 ) )
show(c)
