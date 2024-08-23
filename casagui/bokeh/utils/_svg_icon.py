########################################################################
#
# Copyright (C) 2023
# Associated Universities, Inc. Washington DC, USA.
#
# This script is free software; you can redistribute it and/or modify it
# under the terms of the GNU Library General Public License as published by
# the Free Software Foundation; either version 2 of the License, or (at your
# option) any later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Library General Public
# License for more details.
#
# You should have received a copy of the GNU Library General Public License
# along with this library; if not, write to the Free Software Foundation,
# Inc., 675 Massachusetts Ave, Cambridge, MA 02139, USA.
#
# Correspondence concerning AIPS++ should be adressed as follows:
#        Internet email: casa-feedback@nrao.edu.
#        Postal address: AIPS++ Project Office
#                        National Radio Astronomy Observatory
#                        520 Edgemont Road
#                        Charlottesville, VA 22903-2475 USA
#
########################################################################
from os import listdir
from os.path import dirname, join, isfile, getsize
from bokeh.core import properties
from bokeh.models.ui.icons import SVGIcon
from ...utils import static_vars

@static_vars( values = { 'calendar': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 19 20"><path d="M11,3 C11.6,3 12,2.5 12,2 L12,1 C12,0.4 11.6,0 11,0 C10.4,0 10,0.4 10,1 L10,2 C10,2.5 10.4,3 11,3 Z M14,1 L13,1 L13,2 C13,3.1 12.1,4 11,4 C9.9,4 9,3.1 9,2 L9,1 L6,1 L6,2 C6,3.1 5.1,4 4,4 C2.9,4 2,3.1 2,2 L2,1 L1,1 C0.4,1 0,1.5 0,2 L0,14 C0,14.6 0.4,15 1,15 L14,15 C14.6,15 15,14.6 15,14 L15,2 C15,1.4 14.5,1 14,1 Z M5,13 L2,13 L2,10 L5,10 L5,13 Z M5,9 L2,9 L2,6 L5,6 L5,9 Z M9,13 L6,13 L6,10 L9,10 L9,13 Z M9,9 L6,9 L6,6 L9,6 L9,9 Z M13,13 L10,13 L10,10 L13,10 L13,13 Z M13,9 L10,9 L10,6 L13,6 L13,9 Z M4,3 C4.6,3 5,2.5 5,2 L5,1 C5,0.4 4.6,0 4,0 C3.4,0 3,0.4 3,1 L3,2 C3,2.5 3.4,3 4,3 Z" id="Shape" fill="#000000" fill-rule="nonzero"></path></svg>',
                      'play': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 19 20"><path fill-rule="evenodd" clip-rule="evenodd" d="M12,8c0-0.35-0.19-0.64-0.46-0.82l0.01-0.02l-6-4L5.54,3.18C5.39,3.08,5.21,3,5,3C4.45,3,4,3.45,4,4v8c0,0.55,0.45,1,1,1c0.21,0,0.39-0.08,0.54-0.18l0.01,0.02l6-4l-0.01-0.02C11.81,8.64,12,8.35,12,8z"/></svg>',
                      'pause': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 19 20"><path fill-rule="evenodd" clip-rule="evenodd" d="M6,3H4C3.45,3,3,3.45,3,4v8c0,0.55,0.45,1,1,1h2c0.55,0,1-0.45,1-1V4C7,3.45,6.55,3,6,3z M12,3h-2C9.45,3,9,3.45,9,4v8c0,0.55,0.45,1,1,1h2c0.55,0,1-0.45,1-1V4C13,3.45,12.55,3,12,3z"/></svg>',
                      'stop': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 19 20"><path fill-rule="evenodd" clip-rule="evenodd" d="M12,3H4C3.45,3,3,3.45,3,4v8c0,0.55,0.45,1,1,1h8c0.55,0,1-0.45,1-1V4C13,3.45,12.55,3,12,3z"/></svg>',
                      'step-forward': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 19 20"><path fill-rule="evenodd" clip-rule="evenodd" d="M12,3h-1c-0.55,0-1,0.45-1,1v2.72l-4.38-3.5L5.62,3.23C5.44,3.09,5.24,3,5,3C4.45,3,4,3.45,4,4v8c0,0.55,0.45,1,1,1c0.24,0,0.44-0.09,0.62-0.23l0.01,0.01L10,9.28V12c0,0.55,0.45,1,1,1h1c0.55,0,1-0.45,1-1V4C13,3.45,12.55,3,12,3z"/></svg>',
                      'step-backward': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 19 20"><path fill-rule="evenodd" clip-rule="evenodd" d="M12,3c-0.24,0-0.44,0.09-0.62,0.23l-0.01-0.01L7,6.72V4c0-0.55-0.45-1-1-1H5C4.45,3,4,3.45,4,4v8c0,0.55,0.45,1,1,1h1c0.55,0,1-0.45,1-1V9.28l4.38,3.5l0.01-0.01C11.56,12.91,11.76,13,12,13c0.55,0,1-0.45,1-1V4C13,3.45,12.55,3,12,3z"/></svg>',
                      'cube-add': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 19 20"><path d="M14,2 L15,2 C15.5522847,2 16,2.44771525 16,3 C16,3.55228475 15.5522847,4 15,4 L14,4 L14,5 C14,5.55228475 13.5522847,6 13,6 C12.4477153,6 12,5.55228475 12,5 L12,4 L11,4 C10.4477153,4 10,3.55228475 10,3 C10,2.44771525 10.4477153,2 11,2 L12,2 L12,1 C12,0.44771525 12.4477153,1.01453063e-16 13,0 C13.5522847,-1.01453063e-16 14,0.44771525 14,1 L14,2 Z M9.13604922,0.649170982 C8.44387329,1.19872806 8,2.04752795 8,3 C8,4.3537679 8.89669129,5.49810232 10.1285353,5.8714647 C10.1461766,5.92966908 10.1655391,5.98712523 10.1865637,6.0437739 L8,7.41037618 L1.80625275,3.53928415 L7.50386106,0.283507965 C7.81129373,0.107832154 8.18870627,0.107832154 8.49613894,0.283507965 L9.13604922,0.649170982 Z M15,7.23610651 L15,11.4196775 C15,11.7785343 14.8077139,12.1098778 14.4961389,12.2879206 L8.5,15.7142857 L8.5,8.27712382 L10.68679,6.91038005 C11.2370488,7.57591314 12.068999,8 13,8 C13.7683544,8 14.4692435,7.71114643 15,7.23610651 Z M1.05620201,4.24975008 L7.5,8.27712382 L7.5,15.7142857 L1.50386106,12.2879206 C1.19228606,12.1098778 1,11.7785343 1,11.4196775 L1,4.58032254 C1,4.46598225 1.01952108,4.35443515 1.05620201,4.24975008 Z" id="Combined-Shape" fill="#000000" fill-rule="nonzero"></path></svg>',
                      'cube-remove': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 19 20"><path d="M10.3645067,5.93255949 L8,7.41037618 L1.80625275,3.53928415 L7.50386106,0.283507965 C7.81129373,0.107832154 8.18870627,0.107832154 8.49613894,0.283507965 L9.13604922,0.649170982 C8.44387329,1.19872806 8,2.04752795 8,3 C8,4.43880783 9.01288495,5.64104371 10.3645067,5.93255949 Z M15,6 L15,11.4196775 C15,11.7785343 14.8077139,12.1098778 14.4961389,12.2879206 L8.5,15.7142857 L8.5,8.27712382 L12.1433981,6 L15,6 Z M1.05620201,4.24975008 L7.5,8.27712382 L7.5,15.7142857 L1.50386106,12.2879206 C1.19228606,12.1098778 1,11.7785343 1,11.4196775 L1,4.58032254 C1,4.46598225 1.01952108,4.35443515 1.05620201,4.24975008 Z M11,2 L15,2 C15.5522847,2 16,2.44771525 16,3 C16,3.55228475 15.5522847,4 15,4 L11,4 C10.4477153,4 10,3.55228475 10,3 C10,2.44771525 10.4477153,2 11,2 Z" id="Combined-Shape" fill="#000000" fill-rule="nonzero"></path></svg>',
                      'iclean-continue': '''<svg version="1.1" id="Layer_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px"
         viewBox="0 0 20 20" enable-background="new 0 0 20 20" xml:space="preserve"><g id="repeat">
        <g>
                <path fill-rule="evenodd" clip-rule="evenodd" d="M14,6c0,0.55,0.45,1,1,1h4c0.55,0,1-0.45,1-1V2c0-0.55-0.45-1-1-1s-1,0.45-1,1
                        v2.05C16.18,1.6,13.29,0,10,0C4.48,0,0,4.48,0,10c0,5.52,4.48,10,10,10s10-4.48,10-10c0-0.55-0.45-1-1-1s-1,0.45-1,1
                        c0,4.42-3.58,8-8,8s-8-3.58-8-8s3.58-8,8-8c2.53,0,4.77,1.17,6.24,3H15C14.45,5,14,5.45,14,6z"/>
        </g>
</g>
</svg>''',
                      'iclean-finish': '''<svg version="1.1" id="Layer_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px"
         viewBox="0 0 20 20" enable-background="new 0 0 20 20" xml:space="preserve">
<g id="refresh_1_">
        <g>
                <path fill-rule="evenodd" clip-rule="evenodd" d="M19,1c-0.55,0-1,0.45-1,1v2.06C16.18,1.61,13.29,0,10,0C4.48,0,0,4.48,0,10
                        c0,0.55,0.45,1,1,1s1-0.45,1-1c0-4.42,3.58-8,8-8c2.52,0,4.76,1.18,6.22,3H15c-0.55,0-1,0.45-1,1c0,0.55,0.45,1,1,1h4
                        c0.55,0,1-0.45,1-1V2C20,1.45,19.55,1,19,1z M19,9c-0.55,0-1,0.45-1,1c0,4.42-3.58,8-8,8c-2.52,0-4.76-1.18-6.22-3H5
                        c0.55,0,1-0.45,1-1c0-0.55-0.45-1-1-1H1c-0.55,0-1,0.45-1,1v4c0,0.55,0.45,1,1,1s1-0.45,1-1v-2.06C3.82,18.39,6.71,20,10,20
                        c5.52,0,10-4.48,10-10C20,9.45,19.55,9,19,9z"/>
        </g>
</g>
</svg>''',
                      'iclean-stop': '''<svg version="1.1" fill="white" id="Capa_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px"
	 width="454.354px" height="454.354px" viewBox="0 0 454.354 454.354" style="enable-background:new 0 0 454.354 454.354;"
	 xml:space="preserve">
<g>
	<path d="M451.518,216.585L348.522,38.184c-3.783-6.555-10.781-10.592-18.348-10.592H124.179c-7.566,0-14.561,4.037-18.344,10.592
		L2.837,216.585c-3.783,6.558-3.783,14.632,0,21.181L105.835,416.17c3.783,6.556,10.778,10.593,18.344,10.593h205.996
		c7.566,0,14.564-4.037,18.348-10.593l102.995-178.404C455.3,231.217,455.3,223.143,451.518,216.585z M317.945,384.395H136.411
		L45.646,227.174l90.766-157.215h181.534l90.767,157.215L317.945,384.395z M138.362,245.196c0,14.748-11.349,27.272-35.5,27.272
		c-10.054,0-19.96-2.618-24.932-5.349l4.052-16.444c5.355,2.743,13.568,5.485,22.053,5.485c9.129,0,13.976-3.783,13.976-9.528
		c0-5.491-4.182-8.618-14.756-12.412c-14.617-5.096-24.143-13.182-24.143-25.969c0-15.004,12.534-26.492,33.284-26.492
		c9.918,0,17.23,2.092,22.449,4.436l-4.441,16.057c-3.517-1.699-9.789-4.182-18.4-4.182c-8.615,0-12.797,3.916-12.797,8.485
		c0,5.612,4.962,8.08,16.311,12.404C131.062,224.704,138.362,232.79,138.362,245.196z M145.183,183.192h67.613v16.701h-24.018
		v71.264h-19.973v-71.264h-23.622V183.192z M258.383,181.759c-25.966,0-42.803,19.712-42.803,46.077
		c0,25.05,15.271,44.756,41.372,44.756c25.706,0,43.202-17.483,43.202-46.328C300.154,201.992,285.401,181.759,258.383,181.759z
		 M257.993,256.805c-13.306,0-21.403-12.135-21.403-29.359c0-17.108,7.832-29.891,21.272-29.891
		c13.714,0,21.285,13.577,21.285,29.371C279.142,244.02,271.434,256.805,257.993,256.805z M313.247,271.163h19.706v-31.457
		c1.826,0.271,4.179,0.39,6.798,0.39c11.744,0,21.799-2.872,28.572-9.263c5.236-4.959,8.104-12.255,8.104-20.873
		c0-8.615-3.783-15.927-9.41-20.363c-5.863-4.696-14.611-7.052-26.87-7.052c-12.146,0-20.765,0.792-26.894,1.835v86.782H313.247z
		 M332.953,198.33c1.437-0.387,4.179-0.78,8.222-0.78c9.918,0,15.527,4.835,15.527,12.918c0,9.011-6.525,14.354-17.094,14.354
		c-2.878,0-4.953-0.13-6.661-0.515V198.33H332.953z"/>
</g>
</svg>''',
                      'iclean-disabled': '<svg version="1.1" viewBox="0.0 0.0 960.0 720.0" fill="none" stroke="none" stroke-linecap="square" stroke-miterlimit="10" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns="http://www.w3.org/2000/svg"><clipPath id="p.0"><path d="m0 0l960.0 0l0 720.0l-960.0 0l0 -720.0z" clip-rule="nonzero"/></clipPath><g clip-path="url(#p.0)"><path fill="#000000" fill-opacity="0.0" d="m0 0l960.0 0l0 720.0l-960.0 0z" fill-rule="evenodd"/><path fill="#cfe2f3" d="m59.695522 625.0209l766.39374 -619.0551l72.81891 90.14173l-766.39374 619.0551z" fill-rule="evenodd"/><path stroke="#000000" stroke-width="1.0" stroke-linejoin="round" stroke-linecap="butt" d="m59.695522 625.0209l766.39374 -619.0551l72.81891 90.14173l-766.39374 619.0551z" fill-rule="evenodd"/><path fill="#cfe2f3" d="m116.456696 360.0l0 0c0 -194.57819 162.76389 -352.31497 363.5433 -352.31497l0 0c96.41766 0 188.88635 37.11879 257.06396 103.19066c68.17755 66.07187 106.47937 155.68457 106.47937 249.1243l0 0c0 194.57819 -162.76392 352.31494 -363.54333 352.31494l0 0c-200.77942 0 -363.5433 -157.73676 -363.5433 -352.31494zm176.15747 0c0 97.28909 83.89551 176.15747 187.38583 176.15747c103.49036 0 187.3858 -78.86838 187.3858 -176.15747l0 0c0 -97.28909 -83.89545 -176.15749 -187.3858 -176.15749l0 0c-103.490326 0 -187.38583 78.86839 -187.38583 176.15749z" fill-rule="evenodd"/><path stroke="#000000" stroke-width="1.0" stroke-linejoin="round" stroke-linecap="butt" d="m116.456696 360.0l0 0c0 -194.57819 162.76389 -352.31497 363.5433 -352.31497l0 0c96.41766 0 188.88635 37.11879 257.06396 103.19066c68.17755 66.07187 106.47937 155.68457 106.47937 249.1243l0 0c0 194.57819 -162.76392 352.31494 -363.54333 352.31494l0 0c-200.77942 0 -363.5433 -157.73676 -363.5433 -352.31494zm176.15747 0c0 97.28909 83.89551 176.15747 187.38583 176.15747c103.49036 0 187.3858 -78.86838 187.3858 -176.15747l0 0c0 -97.28909 -83.89545 -176.15749 -187.3858 -176.15749l0 0c-103.490326 0 -187.38583 78.86839 -187.38583 176.15749z" fill-rule="evenodd"/></g></svg>',
                      'iclean-dead': '<svg version="1.1" viewBox="0.0 0.0 960.0 720.0" fill="none" stroke="none" stroke-linecap="square" stroke-miterlimit="10" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns="http://www.w3.org/2000/svg"><clipPath id="p.0"><path d="m0 0l960.0 0l0 720.0l-960.0 0l0 -720.0z" clip-rule="nonzero"/></clipPath><g clip-path="url(#p.0)"><path fill="#000000" fill-opacity="0.0" d="m0 0l960.0 0l0 720.0l-960.0 0z" fill-rule="evenodd"/><path fill="#cfe2f3" d="m805.43304 717.3858l-650.8661 0l0 -389.33856l325.43307 -325.43307l325.43304 0z" fill-rule="evenodd"/><path fill="#a5b4c2" d="m480.0 2.6141732l-65.08661 260.34647l-260.34647 65.08661z" fill-rule="evenodd"/><path fill="#000000" fill-opacity="0.0" d="m480.0 2.6141732l-65.08661 260.34647l-260.34647 65.08661l325.43307 -325.43307l325.43304 0l0 714.7716l-650.8661 0l0 -389.33856" fill-rule="evenodd"/><path stroke="#000000" stroke-width="8.0" stroke-linejoin="round" stroke-linecap="butt" d="m480.0 2.6141732l-65.08661 260.34647l-260.34647 65.08661l325.43307 -325.43307l325.43304 0l0 714.7716l-650.8661 0l0 -389.33856" fill-rule="evenodd"/><path fill="#000000" d="m695.853 109.348366l23.055115 23.055107l-98.677124 98.67717l-23.055115 -23.055115z" fill-rule="evenodd"/><path stroke="#000000" stroke-width="1.0" stroke-linejoin="round" stroke-linecap="butt" d="m695.853 109.348366l23.055115 23.055107l-98.677124 98.67717l-23.055115 -23.055115z" fill-rule="evenodd"/><path fill="#000000" d="m718.9089 208.02626l-23.055115 23.05513l-98.677185 -98.67717l23.055115 -23.055122z" fill-rule="evenodd"/><path stroke="#000000" stroke-width="1.0" stroke-linejoin="round" stroke-linecap="butt" d="m718.9089 208.02626l-23.055115 23.05513l-98.677185 -98.67717l23.055115 -23.055122z" fill-rule="evenodd"/><path fill="#000000" d="m288.9134 461.73752l382.17322 0l0 40.44095l-382.17322 0z" fill-rule="evenodd"/><path stroke="#000000" stroke-width="1.0" stroke-linejoin="round" stroke-linecap="butt" d="m288.9134 461.73752l382.17322 0l0 40.44095l-382.17322 0z" fill-rule="evenodd"/><path fill="#000000" d="m471.08923 502.17847l0 73.700806l0 0c0 40.703796 -27.250702 73.700806 -60.86615 73.700806c-33.615417 0 -60.86612 -32.99701 -60.86612 -73.700806l0 -73.700806z" fill-rule="evenodd"/><path stroke="#000000" stroke-width="1.0" stroke-linejoin="round" stroke-linecap="butt" d="m471.08923 502.17847l0 73.700806l0 0c0 40.703796 -27.250702 73.700806 -60.86615 73.700806c-33.615417 0 -60.86612 -32.99701 -60.86612 -73.700806l0 -73.700806z" fill-rule="evenodd"/></g></svg>',
                      'makemask-done': '<svg version="1.1" id="Layer_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px" viewBox="0 0 20 20" enable-background="new 0 0 20 20" xml:space="preserve"><g id="tick_circle_2_"><path id="Combined-Shape_5_" d="M10,20C4.48,20,0,15.52,0,10S4.48,0,10,0s10,4.48,10,10S15.52,20,10,20z M15,6c-0.28,0-0.53,0.11-0.71,0.29L8,12.59l-2.29-2.3C5.53,10.11,5.28,10,5,10c-0.55,0-1,0.45-1,1c0,0.28,0.11,0.53,0.29,0.71l3,3C7.47,14.89,7.72,15,8,15c0.28,0,0.53-0.11,0.71-0.29l7-7C15.89,7.53,16,7.28,16,7C16,6.45,15.55,6,15,6z"/></g></svg>',
                      'help': '<svg version="1.1" id="Layer_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px" viewBox="0 0 20 20" enable-background="new 0 0 20 20" xml:space="preserve"><path id="help_1_" d="M10,0C4.48,0,0,4.48,0,10c0,5.52,4.48,10,10,10s10-4.48,10-10C20,4.48,15.52,0,10,0z M7.41,4.62C8.06,4.08,8.92,3.8,9.97,3.8c0.54,0,1.03,0.08,1.48,0.25c0.44,0.17,0.83,0.39,1.14,0.68c0.32,0.29,0.56,0.63,0.74,1.02c0.17,0.39,0.26,0.82,0.26,1.27s-0.08,0.87-0.24,1.23c-0.16,0.37-0.4,0.73-0.71,1.11l-1.21,1.58c-0.14,0.17-0.28,0.33-0.32,0.48c-0.05,0.15-0.11,0.35-0.11,0.6v0.43c0,0.12,0,0.54,0,0.54H9v-2c0,0,0.06-0.58,0.24-0.81l1.21-1.64c0.25-0.3,0.41-0.56,0.51-0.77s0.14-0.44,0.14-0.67c0-0.35-0.11-0.63-0.32-0.85s-0.5-0.33-0.88-0.33c-0.37,0-0.67,0.11-0.89,0.33C8.79,6.48,8.64,6.79,8.55,7.19C8.52,7.31,8.44,7.36,8.32,7.35L6.37,7.06C6.25,7.05,6.21,6.98,6.23,6.84C6.36,5.91,6.75,5.17,7.41,4.62z M9,14h2.02L11,16H9V14z"/></svg>',
                         'iclean-log': '<?xml version="1.0" encoding="UTF-8" standalone="no"?><svg xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:cc="http://creativecommons.org/ns#" xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:svg="http://www.w3.org/2000/svg" xmlns="http://www.w3.org/2000/svg" xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" version="1.1" id="Capa_1" viewBox="0 0 504.895 270.75801" xml:space="preserve" width="512" height="274.56818" sodipodi:docname="log.svg" inkscape:version="1.0.2 (e86c8708, 2021-01-15)"><metadata id="metadata856"><rdf:RDF><cc:Work rdf:about=""><dc:format>image/svg+xml</dc:format><dc:type rdf:resource="http://purl.org/dc/dcmitype/StillImage" /><dc:title></dc:title></cc:Work></rdf:RDF></metadata><defs id="defs854" /><sodipodi:namedview pagecolor="#ffffff" bordercolor="#666666" borderopacity="1" objecttolerance="10" gridtolerance="10" guidetolerance="10" inkscape:pageopacity="0" inkscape:pageshadow="2" inkscape:window-width="1286" inkscape:window-height="648" id="namedview852" showgrid="false" fit-margin-top="0" fit-margin-left="0" fit-margin-right="0" fit-margin-bottom="0" inkscape:zoom="1.2773438" inkscape:cx="256" inkscape:cy="137.28459" inkscape:window-x="0" inkscape:window-y="23" inkscape:window-maximized="0" inkscape:current-layer="Capa_1" /> <g id="g849" transform="translate(0,-117.068)"> <path style="fill:#faba45" d="M 392.139,169.814 H 287.295 l -30.847,-45.246 h -33.27 l 0.103,45.246 H 112.756 C 54.624,169.814 7.5,216.938 7.5,275.07 c 0,58.131 47.124,105.256 105.256,105.256 h 279.383 c 58.132,0 105.256,-47.125 105.256,-105.256 0,-58.132 -47.124,-105.256 -105.256,-105.256 z" id="path833" /> <circle style="fill:#e95b2d" cx="112.756" cy="275.07001" r="105.256" id="circle835" /> <path style="fill:#0f2639" d="m 392.139,162.314 h -100.88 l -30.847,-45.246 h -44.75 l 0.103,45.246 H 112.756 C 50.582,162.314 0,212.897 0,275.07 0,337.243 50.582,387.826 112.756,387.826 h 279.383 c 62.174,0 112.756,-50.582 112.756,-112.756 0,-62.174 -50.582,-112.756 -112.756,-112.756 z M 15,275.07 c 0,-53.903 43.853,-97.756 97.756,-97.756 53.902,0 97.755,43.853 97.755,97.756 0,53.903 -43.853,97.756 -97.755,97.756 C 58.853,372.826 15,328.973 15,275.07 Z m 377.139,97.756 H 168.903 c 9.713,-5.601 18.514,-12.612 26.131,-20.745 h 113.134 v -15 H 206.879 c 11.768,-17.803 18.632,-39.119 18.632,-62.011 0,-7.313 -0.708,-14.461 -2.044,-21.39 h 108.346 v -15 H 219.484 c -2.588,-7.569 -5.962,-14.777 -10.021,-21.528 h 200.148 v -15 H 198.686 c -8.404,-9.889 -18.475,-18.318 -29.782,-24.838 h 61.895 l -0.103,-45.246 h 21.789 l 30.847,45.246 H 392.14 c 53.903,0 97.756,43.853 97.756,97.756 -0.001,53.903 -43.854,97.756 -97.757,97.756 z" id="path837" /> <path style="fill:#0f2639" d="m 147.473,345.395 -6.659,-13.441 c -8.772,4.346 -18.212,6.55 -28.058,6.55 -34.978,0 -63.434,-28.456 -63.434,-63.433 0,-34.978 28.456,-63.434 63.434,-63.434 34.977,0 63.433,28.456 63.433,63.434 0.001,16.417 -6.276,32.001 -17.673,43.881 l 10.824,10.385 c 14.09,-14.686 21.849,-33.958 21.849,-54.266 0,-43.249 -35.185,-78.434 -78.433,-78.434 -43.248,0 -78.434,35.185 -78.434,78.434 0,43.248 35.185,78.433 78.434,78.433 12.176,-0.001 23.856,-2.729 34.717,-8.109 z" id="path839" /> <path style="fill:#0f2639" d="m 68.645,275.07 c 0,24.323 19.788,44.11 44.111,44.11 24.323,0 44.11,-19.788 44.11,-44.11 0,-24.323 -19.788,-44.111 -44.11,-44.111 -24.323,0 -44.111,19.788 -44.111,44.111 z m 73.221,0 c 0,16.051 -13.059,29.11 -29.11,29.11 -16.052,0 -29.111,-13.059 -29.111,-29.11 0,-16.052 13.059,-29.111 29.111,-29.111 16.051,0 29.11,13.059 29.11,29.111 z" id="path841" /> <rect x="354.69699" y="238.681" style="fill:#0f2639" width="105.826" height="15" id="rect843" /> <path style="fill:#0f2639" d="m 368.614,302.482 c -16.644,0 -30.185,13.541 -30.185,30.186 h 15 c 0,-8.374 6.812,-15.186 15.185,-15.186 8.373,0 15.185,6.812 15.185,15.186 h 15 c 0,-16.646 -13.541,-30.186 -30.185,-30.186 z" id="path845" /><path style="fill:#0f2639" d="m 368.614,272.73 c -16.357,0 -31.903,6.662 -43.186,18.394 h -86 v 15 h 92.774 l 2.246,-2.627 c 8.564,-10.02 21.018,-15.767 34.166,-15.767 13.148,0 25.602,5.747 34.165,15.767 l 2.245,2.627 h 55.498 v -15 H 411.8 C 400.518,279.392 384.971,272.73 368.614,272.73 Z" id="path847" /></g></svg>',
                         ### bp = https://blueprintjs.com/docs/#icons/icons-list
                         'bp-application-lg': '''<svg version="1.1" id="Layer_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px"
	 viewBox="0 0 20 20" enable-background="new 0 0 20 20" xml:space="preserve">
<g id="application">
	<g>
		<path fill-rule="evenodd" clip-rule="evenodd" d="M3.5,9h9C12.78,9,13,8.78,13,8.5C13,8.22,12.78,8,12.5,8h-9C3.22,8,3,8.22,3,8.5
			C3,8.78,3.22,9,3.5,9z M3.5,11h5C8.78,11,9,10.78,9,10.5C9,10.22,8.78,10,8.5,10h-5C3.22,10,3,10.22,3,10.5
			C3,10.78,3.22,11,3.5,11z M19,1H1C0.45,1,0,1.45,0,2v16c0,0.55,0.45,1,1,1h18c0.55,0,1-0.45,1-1V2C20,1.45,19.55,1,19,1z M18,17H2
			V6h16V17z M3.5,13h7c0.28,0,0.5-0.22,0.5-0.5c0-0.28-0.22-0.5-0.5-0.5h-7C3.22,12,3,12.22,3,12.5C3,12.78,3.22,13,3.5,13z"/>
	</g>
</g>
</svg>''',
                         'bp-application-sm': '''<svg version="1.1" id="Layer_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px"
	 viewBox="0 0 16 16" enable-background="new 0 0 16 16" xml:space="preserve">
<g id="application_1_">
	<g>
		<path fill-rule="evenodd" clip-rule="evenodd" d="M3.5,7h7C10.78,7,11,6.78,11,6.5C11,6.22,10.78,6,10.5,6h-7C3.22,6,3,6.22,3,6.5
			C3,6.78,3.22,7,3.5,7z M15,1H1C0.45,1,0,1.45,0,2v12c0,0.55,0.45,1,1,1h14c0.55,0,1-0.45,1-1V2C16,1.45,15.55,1,15,1z M14,13H2V5
			h12V13z M3.5,9h4C7.78,9,8,8.78,8,8.5C8,8.22,7.78,8,7.5,8h-4C3.22,8,3,8.22,3,8.5C3,8.78,3.22,9,3.5,9z M3.5,11h5
			C8.78,11,9,10.78,9,10.5C9,10.22,8.78,10,8.5,10h-5C3.22,10,3,10.22,3,10.5C3,10.78,3.22,11,3.5,11z"/>
	</g>
</g>
</svg>'''

} )
def svg_icon( icon_name, **kwargs ):
    if type(icon_name) == str and icon_name in svg_icon.values:
        return SVGIcon( **kwargs, svg=svg_icon.values[icon_name] )

    elif type(icon_name) == str or type(icon_name) == list and len(icon_name) > 0:
        if type(icon_name) == str: _icon_name = [ icon_name ]
        else: _icon_name = icon_name
        if type(_icon_name) == list:
            icon_dir = join( dirname(dirname(dirname(__file__))),'__icons__', *_icon_name[:-1] )
            icons = [f for f in listdir(icon_dir) if isfile(join(icon_dir, f)) and f.startswith(_icon_name[-1]) and f.endswith('.svg')]
            if len(icons) > 1:
                raise RuntimeError( f'''multiple icon files {icons} found in {icon_dir}''' )
            elif len(icons) > 0:
                path = join( icon_dir, icons[0] )
                if isfile(path):
                    if getsize(path) > 2 * 1024 * 1024:
                        raise RuntimeError( f'''{path} seems too large to be an SVG file...''' )
                    with open( path, "r" ) as f:
                        svg_string = f.read( )
                    return SVGIcon( **kwargs, svg=svg_string )

    raise RuntimeError( f'''icon_name={icon_name} is not a known icon''' )
