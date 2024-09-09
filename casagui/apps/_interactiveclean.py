########################################################################
#
# Copyright (C) 2022,2023,2024
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
'''implementation of the ``InteractiveClean`` application for interactive control
of tclean'''

###
### Useful for debugging
###
###from casagui.bokeh.state import initialize_bokeh
###initialize_bokeh( bokehjs_subst=".../bokeh-3.2.2.js" )
###
import os
import copy
import asyncio
import shutil
import websockets
from os.path import basename, abspath, exists
from uuid import uuid4
from html import escape as html_escape
from contextlib import asynccontextmanager
from bokeh.models import Button, TextInput, Checkbox, Div, LinearAxis, CustomJS, Spacer, Span, HoverTool, DataRange1d, Step, InlineStyleSheet
from bokeh.events import ModelEvent, MouseEnter
from bokeh.models import TabPanel, Tabs
from bokeh.plotting import ColumnDataSource, figure, show
from bokeh.layouts import column, row, layout
from bokeh.io import reset_output as reset_bokeh_output, output_notebook
from bokeh.models.dom import HTML

from bokeh.models.ui.tooltips import Tooltip
from ..bokeh.models import TipButton, Tip, EvTextInput
from ..utils import resource_manager, reset_resource_manager, is_notebook
from ..utils import ContextMgrChain as CMC

# pylint: disable=no-name-in-module
from casatasks.private.imagerhelpers.imager_return_dict import ImagingDict
try:
    from casagui.private._gclean import gclean as _gclean
except:
    from casatasks.private.imagerhelpers._gclean import gclean as _gclean
from casatasks.private.imagerhelpers.input_parameters import ImagerParameters
# pylint: enable=no-name-in-module

from casagui.utils import find_ws_address, convert_masks
from casagui.toolbox import CubeMask, AppContext
from casagui.bokeh.utils import svg_icon
from casagui.bokeh.sources import DataPipe
from ..utils import DocEnum

from ._interactiveclean_wrappers import SharedWidgets

class InteractiveClean:
    '''InteractiveClean(...) implements interactive clean using Bokeh
        tclean ---- Radio Interferometric Image Reconstruction

    Form images from visibilities and reconstruct a sky model.
    This task handles continuum images and spectral line cubes,
    supports outlier fields, contains standard clean based algorithms
    along with algorithms for multi-scale and wideband image
    reconstruction, widefield imaging correcting for the w-term,
    full primary-beam imaging and joint mosaic imaging (with
    heterogeneous array support for ALMA).

    --------- parameter descriptions ---------------------------------------------

    vis                  Name(s) of input visibility file(s)
                         default: none;
                         example: vis='ngc5921.ms'
                                  vis=['ngc5921a.ms','ngc5921b.ms']; multiple MSes
    selectdata           Enable data selection parameters.
    field                to image or mosaic.  Use field id(s) or name(s).
                            ['go listobs' to obtain the list id's or names]
                         default: ''= all fields
                           If field string is a non-negative integer, it is assumed to
                           be a field index otherwise, it is assumed to be a
                           field name
                           field='0~2'; field ids 0,1,2
                           field='0,4,5~7'; field ids 0,4,5,6,7
                           field='3C286,3C295'; field named 3C286 and 3C295
                           field = '3,4C\*'; field id 3, all names starting with 4C
                           For multiple MS input, a list of field strings can be used:
                           field = ['0~2','0~4']; field ids 0-2 for the first MS and 0-4
                                   for the second
                           field = '0~2'; field ids 0-2 for all input MSes
    spw                  l window/channels
                         NOTE: channels de-selected here will contain all zeros if
                                   selected by the parameter mode subparameters.
                         default: ''=all spectral windows and channels
                           spw='0~2,4'; spectral windows 0,1,2,4 (all channels)
                           spw='0:5~61'; spw 0, channels 5 to 61
                           spw='<2';   spectral windows less than 2 (i.e. 0,1)
                           spw='0,10,3:3~45'; spw 0,10 all channels, spw 3,
                                              channels 3 to 45.
                           spw='0~2:2~6'; spw 0,1,2 with channels 2 through 6 in each.
                           For multiple MS input, a list of spw strings can be used:
                           spw=['0','0~3']; spw ids 0 for the first MS and 0-3 for the second
                           spw='0~3' spw ids 0-3 for all input MS
                           spw='3:10~20;50~60' for multiple channel ranges within spw id 3
                           spw='3:10~20;50~60,4:0~30' for different channel ranges for spw ids 3 and 4
                           spw='0:0~10,1:20~30,2:1;2;3'; spw 0, channels 0-10,
                                spw 1, channels 20-30, and spw 2, channels, 1,2 and 3
                           spw='1~4;6:15~48' for channels 15 through 48 for spw ids 1,2,3,4 and 6
    timerange            Range of time to select from data

                         default: '' (all); examples,
                         timerange = 'YYYY/MM/DD/hh:mm:ss~YYYY/MM/DD/hh:mm:ss'
                         Note: if YYYY/MM/DD is missing date defaults to first
                               day in data set
                         timerange='09:14:0~09:54:0' picks 40 min on first day
                         timerange='25:00:00~27:30:00' picks 1 hr to 3 hr
                                   30min on NEXT day
                         timerange='09:44:00' pick data within one integration
                                   of time
                         timerange='> 10:24:00' data after this time
                         For multiple MS input, a list of timerange strings can be
                         used:
                         timerange=['09:14:0~09:54:0','> 10:24:00']
                         timerange='09:14:0~09:54:0''; apply the same timerange for
                                                       all input MSes
    uvrange              Select data within uvrange (default unit is meters)
                         default: '' (all); example:
                         uvrange='0~1000klambda'; uvrange from 0-1000 kilo-lambda
                         uvrange='> 4klambda';uvranges greater than 4 kilo lambda
                         For multiple MS input, a list of uvrange strings can be
                         used:
                         uvrange=['0~1000klambda','100~1000klamda']
                         uvrange='0~1000klambda'; apply 0-1000 kilo-lambda for all
                                                  input MSes
    antenna              Select data based on antenna/baseline

                         default: '' (all)
                         If antenna string is a non-negative integer, it is
                         assumed to be an antenna index, otherwise, it is
                         considered an antenna name.
                         antenna='5\&6'; baseline between antenna index 5 and
                                       index 6.
                         antenna='VA05\&VA06'; baseline between VLA antenna 5
                                             and 6.
                         antenna='5\&6;7\&8'; baselines 5-6 and 7-8
                         antenna='5'; all baselines with antenna index 5
                         antenna='05'; all baselines with antenna number 05
                                      (VLA old name)
                         antenna='5,6,9'; all baselines with antennas 5,6,9
                                         index number
                         For multiple MS input, a list of antenna strings can be
                         used:
                         antenna=['5','5\&6'];
                         antenna='5'; antenna index 5 for all input MSes
                         antenna='!DV14'; use all antennas except DV14
    scan                 Scan number range

                         default: '' (all)
                         example: scan='1~5'
                         For multiple MS input, a list of scan strings can be used:
                         scan=['0~100','10~200']
                         scan='0~100; scan ids 0-100 for all input MSes
    observation          Observation ID range
                         default: '' (all)
                         example: observation='1~5'
    intent               Scan Intent(s)

                         default: '' (all)
                         example: intent='TARGET_SOURCE'
                         example: intent='TARGET_SOURCE1,TARGET_SOURCE2'
                         example: intent='TARGET_POINTING\*'
    datacolumn           Data column to image (data or observed, corrected)
                         default:'corrected'
                         ( If 'corrected' does not exist, it will use 'data' instead )
    imagename            Pre-name of output images

                         example : imagename='try'

                         Output images will be (a subset of) :

                         try.psf              - Point spread function
                         try.residual      - Residual image
                         try.image         - Restored image
                         try.model         - Model image (contains only flux components)
                         try.sumwt        - Single pixel image containing sum-of-weights.
                                                   (for natural weighting, sensitivity=1/sqrt(sumwt))
                         try.pb              - Primary beam model (values depend on the gridder used)

                         Widefield projection algorithms (gridder=mosaic,awproject) will
                         compute the following images too.
                         try.weight        - FT of gridded weights or the
                                                   un-normalized sum of PB-square (for all pointings)
                                                   Here, PB = sqrt(weight) normalized to a maximum of 1.0

                         For multi-term wideband imaging, all relevant images above will
                         have additional .tt0,.tt1, etc suffixes to indicate Taylor terms,
                         plus the following extra output images.
                         try.alpha            - spectral index
                         try.alpha.error   - estimate of error on spectral index
                         try.beta              - spectral curvature (if nterms \> 2)

                         Tip : Include a directory name in 'imagename' for all
                                 output images to be sent there instead of the
                                 current working directory : imagename='mydir/try'

                         Tip : Restarting an imaging run without changing 'imagename'
                                 implies continuation from the existing model image on disk.
                                  - If 'startmodel' was initially specified it needs to be set to ""
                                    for the restart run (or tclean will exit with an error message).
                                  - By default, the residual image and psf will be recomputed
                                    but if no changes were made to relevant parameters between
                                    the runs, set calcres=False, calcpsf=False to resume directly from
                                    the minor cycle without the (unnecessary) first major cycle.
                                  To automatically change 'imagename' with a numerical
                                  increment, set restart=False (see tclean docs for 'restart').

                          Note : All imaging runs will by default produce restored images.
                                    For a niter=0 run, this will be redundant and can optionally
                                    be turned off via the 'restoration=T/F' parameter.
    imsize               Number of pixels
                         example:

                         imsize = [350,250]
                         imsize = 500 is equivalent to [500,500]

                         To take proper advantage of internal optimized FFT routines, the
                         number of pixels must be even and factorizable by 2,3,5 only.
                         To find the nearest optimal imsize to that desired by the user, please use the following tool method:

                         from casatools import synthesisutils
                         su = synthesisutils()
                         su.getOptimumSize(345)
                         Output :  360
    cell                 Cell size
                         example: cell=['0.5arcsec,'0.5arcsec'] or
                         cell=['1arcmin', '1arcmin']
                         cell = '1arcsec' is equivalent to ['1arcsec','1arcsec']
    phasecenter          Phase center of the image (string or field id); if the phasecenter is the name known major solar system object ('MERCURY', 'VENUS', 'MARS', 'JUPITER', 'SATURN', 'URANUS', 'NEPTUNE', 'PLUTO', 'SUN', 'MOON') or is an ephemerides table then that source is tracked and the background sources get smeared. There is a special case, when phasecenter='TRACKFIELD', which will use the ephemerides or polynomial phasecenter in the FIELD table of the MS's as the source center to track.
                         example: phasecenter=6
                                  phasecenter='J2000 19h30m00 -40d00m00'
                                  phasecenter='J2000 292.5deg  -40.0deg'
                                  phasecenter='J2000 5.105rad  -0.698rad'
                                  phasecenter='ICRS 13:05:27.2780 -049.28.04.458'
                                  phasecenter='myComet_ephem.tab'
                                  phasecenter='MOON'
                                  phasecenter='TRACKFIELD'
    stokes               Stokes Planes to make
                         default='I'; example: stokes='IQUV';
                           Options: 'I','Q','U','V','IV','QU','IQ','UV','IQUV','RR','LL','XX','YY','RRLL','XXYY','pseudoI'

                                       Note : Due to current internal code constraints, if any correlation pair
                                                  is flagged, by default, no data for that row in the MS will be used.
                                                  So, in an MS with XX,YY, if only YY is flagged, neither a
                                                  Stokes I image nor an XX image can be made from those data points.
                                                  In such a situation, please split out only the unflagged correlation into
                                                  a separate MS.

                                       Note : The 'pseudoI' option is a partial solution, allowing Stokes I imaging
                                              when either of the parallel-hand correlations are unflagged.

                                       The remaining constraints shall be removed (where logical) in a future release.
    projection           Coordinate projection
                         Examples : SIN,   NCP
                         A list of supported (but untested) projections can be found here :
                         http://casa.nrao.edu/active/docs/doxygen/html/classcasa_1_1Projection.html#a3d5f9ec787e4eabdce57ab5edaf7c0cd
    startmodel           Name of starting model image

                         The contents of the supplied starting model image will be
                         copied to the imagename.model before the run begins.

                         example : startmodel = 'singledish.im'

                         For deconvolver='mtmfs', one image per Taylor term must be provided.
                         example : startmodel = ['try.model.tt0', 'try.model.tt1']
                                         startmodel = ['try.model.tt0']  will use a starting model only
                                                              for the zeroth order term.
                                         startmodel = ['','try.model.tt1']  will use a starting model only
                                                              for the first order term.

                          This starting model can be of a different image shape and size from
                          what is currently being imaged. If so, an image regrid is first triggered
                          to resample the input image onto the target coordinate system.

                          A common usage is to set this parameter equal to a single dish image

                          Negative components in the model image will be included as is.

                         [ Note : If an error occurs during image resampling/regridding,
                                      please try using task imregrid to resample the starting model
                                      image onto a CASA image with the target shape and
                                      coordinate system before supplying it via startmodel ]
    specmode             Spectral definition mode (mfs,cube,cubedata, cubesource)

                         mode='mfs' : Continuum imaging with only one output image channel.
                                               (mode='cont' can also be used here)

                         mode='cube' : Spectral line imaging with one or more channels
                                                 Parameters start, width,and nchan define the spectral
                                                 coordinate system and can be specified either in terms
                                                 of channel numbers, frequency or velocity in whatever
                                                 spectral frame is specified in 'outframe'.
                                                 All internal and output images are made with outframe as the
                                                 base spectral frame. However imaging code internally uses the fixed
                                                 spectral frame, LSRK for automatic internal software
                                                 Doppler tracking so that a spectral line observed over an
                                                 extended time range will line up appropriately.
                                                 Therefore the output images have additional spectral frame conversion
                                                 layer in LSRK on the top the base frame.


                                                 (Note : Even if the input parameters are specified in a frame
                                                             other than LSRK, the viewer still displays spectral
                                                             axis in LSRK by default because of the conversion frame
                                                             layer mentioned above. The viewer can be used to relabel
                                                             the spectral axis in any desired frame - via the spectral
                                                             reference option under axis label properties in the
                                                             data display options window.)




                          mode='cubedata' : Spectral line imaging with one or more channels
                                                          There is no internal software Doppler tracking so
                                                          a spectral line observed over an extended time range
                                                          may be smeared out in frequency. There is strictly
                                                          no valid spectral frame with which to associate with the
                                                          output images, thus the image spectral  frame will
                                                          be labelled  "Undefined".


                          mode='cubesource': Spectral line imaging while
                                                          tracking moving source (near field or solar system
                                                          objects). The velocity of the source is accounted
                                                          and the frequency reported is in the source frame.
                                                          As there is no "SOURCE" frame defined in CASA,
                                                          the frame in the image will be labelled "REST" (but do note the
                                                          velocity of a given line reported may be different from the rest frame
                                                          velocity if the emission region is moving w.r.t the systemic
                                                          velocity frame of the source)
    reffreq              Reference frequency of the output image coordinate system

                         Example :  reffreq='1.5GHz'    as a string with units.

                         By default, it is calculated as the middle of the selected frequency range.

                         For deconvolver='mtmfs' the Taylor expansion is also done about
                         this specified reference frequency.
    nchan                Number of channels in the output image
                         For default (=-1), the number of channels will be automatically determined
                         based on data selected by 'spw' with 'start' and 'width'.
                         It is often easiest to leave nchan at the default value.
                         example: nchan=100
    start                First channel (e.g. start=3,start=\'1.1GHz\',start=\'15343km/s\')
                         of output cube images specified by data channel number (integer),
                         velocity (string with a unit),  or frequency (string with a unit).
                         Default:''; The first channel is automatically determined based on
                         the 'spw' channel selection and 'width'.
                         channels in 'spw'.
                         Since the integer number in 'start' represents the data channel number,
                         when the channel number is used along with the spectral window id selection
                         in 'spw', 'start' specified as an integer should be carefully set otherwise
                         it may result in the blank image channels if the 'start' channel (i.e. absolute
                         channel number) is outside of the channel range specified in 'spw'.
                         In such a case, 'start' can be left as a default (='') to ensure
                         matching with the data spectral channel selection.
                         For specmode='cube', when velocity or frequency is used it is
                         interpreted with the frame defined in outframe. [The parameters of
                         the desired output cube can be estimated by using the 'transform'
                         functionality of 'plotms']
                         examples: start='5.0km/s'; 1st channel, 5.0km/s in outframe
                                   start='22.3GHz'; 1st channel, 22.3GHz in outframe
    width                Channel width (e.g. width=2,width=\'0.1MHz\',width=\'10km/s\') of output cube images
                         specified by data channel number (integer), velocity (string with a unit), or
                         or frequency (string with a unit).
                         Default:''; data channel width
                         The sign of width defines the direction of the channels to be incremented.
                         For width specified in velocity or frequency with '-' in front  gives image channels in
                         decreasing velocity or frequency, respectively.
                         For specmode='cube', when velocity or frequency is used it is interpreted with
                         the reference frame defined in outframe.
                         examples: width='2.0km/s'; results in channels with increasing velocity
                                   width='-2.0km/s';  results in channels with decreasing velocity
                                   width='40kHz'; results in channels with increasing frequency
                                   width=-2; results in channels averaged of 2 data channels incremented from
                                             high to low channel numbers
    outframe             Spectral reference frame in which to interpret \'start\' and \'width\'
                          Options: '','LSRK','LSRD','BARY','GEO','TOPO','GALACTO','LGROUP','CMB'
                          example: outframe='bary' for Barycentric frame

                          REST -- Rest frequency
                          LSRD -- Local Standard of Rest (J2000)
                                   -- as the dynamical definition (IAU, [9,12,7] km/s in galactic coordinates)
                          LSRK -- LSR as a kinematical (radio) definition
                                   -- 20.0 km/s in direction ra,dec = [270,+30] deg (B1900.0)
                          BARY -- Barycentric (J2000)
                          GEO --- Geocentric
                          TOPO -- Topocentric
                          GALACTO -- Galacto centric (with rotation of 220 km/s in direction l,b = [90,0] deg.
                          LGROUP -- Local group velocity -- 308km/s towards l,b = [105,-7] deg (F. Ghigo)
                         CMB -- CMB velocity -- 369.5km/s towards l,b = [264.4, 48.4] deg (F. Ghigo)
                         DEFAULT = LSRK
    veltype              Velocity type (radio, z, ratio, beta, gamma, optical)
                         For start and/or width specified in velocity, specifies the velocity definition
                         Options: 'radio','optical','z','beta','gamma','optical'
                         NOTE: the viewer always defaults to displaying the 'radio' frame,
                           but that can be changed in the position tracking pull down.

                          The different types (with F = f/f0, the frequency ratio), are:

                          Z = (-1 + 1/F)
                         RATIO = (F) \*
                         RADIO = (1 - F)
                         OPTICAL == Z
                         BETA = ((1 - F2)/(1 + F2))
                         GAMMA = ((1 + F2)/2F) \*
                         RELATIVISTIC == BETA (== v/c)
                         DEFAULT == RADIO
                         Note that the ones with an '\*' have no real interpretation
                         (although the calculation will proceed) if given as a velocity.
    restfreq             List of rest frequencies or a rest frequency in a string.
                         Specify rest frequency to use for output image.
                         \*Currently it uses the first rest frequency in the list for translation of
                         velocities. The list will be stored in the output images.
                         Default: []; look for the rest frequency stored in the MS, if not available,
                         use center frequency of the selected channels
                         examples: restfreq=['1.42GHz']
                                   restfreq='1.42GHz'
    interpolation        Spectral interpolation (nearest,linear,cubic)

                          Interpolation rules to use when binning data channels onto image channels
                          and evaluating visibility values at the centers of image channels.

                         Note : 'linear' and 'cubic' interpolation requires data points on both sides of
                           each image frequency. Errors  are therefore possible at edge  channels, or near
                           flagged data channels. When image channel width is much larger than the data
                           channel width there is nothing much to be gained using linear or cubic thus
                           not worth the extra computation involved.
    perchanweightdensity When calculating weight density for Briggs
                         style weighting in a cube, this parameter
                         determines whether to calculate the weight
                         density for each channel independently
                         (the default, True)
                         or a common weight density for all of the selected
                         data. This parameter has no
                         meaning for continuum (specmode='mfs') imaging
                         or for natural and radial weighting schemes.
                         For cube imaging
                         perchanweightdensity=True is a recommended
                         option that provides more uniform
                         sensitivity per channel for cubes, but with
                         generally larger psfs than the
                         perchanweightdensity=False (prior behavior)
                         option. When using Briggs style weight with
                         perchanweightdensity=True, the imaging weight
                         density calculations use only the weights of
                         data that contribute specifically to that
                         channel. On the other hand, when
                         perchanweightdensity=False, the imaging
                         weight density calculations sum all of the
                         weights from all of the data channels
                         selected whose (u,v) falls in a given uv cell
                         on the weight density grid. Since the
                         aggregated weights, in any given uv cell,
                         will change depending on the number of
                         channels included when imaging, the psf
                         calculated for a given frequency channel will
                         also necessarily change, resulting in
                         variability in the psf for a given frequency
                         channel when perchanweightdensity=False. In
                         general, perchanweightdensity=False results
                         in smaller psfs for the same value of
                         robustness compared to
                         perchanweightdensity=True, but the rms noise
                         as a function of channel varies and increases
                         toward the edge channels;
                         perchanweightdensity=True provides more
                         uniform sensitivity per channel for
                         cubes. This may make it harder to find
                         estimates of continuum when
                         perchanweightdensity=False. If you intend to
                         image a large cube in many smaller subcubes
                         and subsequently concatenate, it is advisable
                         to use perchanweightdensity=True to avoid
                         surprisingly varying sensitivity and psfs
                         across the concatenated cube.
    gridder              Gridding options (standard, wproject, widefield, mosaic, awproject)

                                The following options choose different gridding convolution
                                functions for the process of convolutional resampling of the measured
                                visibilities onto a regular uv-grid prior to an inverse FFT.
                                Model prediction (degridding) also uses these same functions.
                                Several wide-field effects can be accounted for via careful choices of
                                convolution functions. Gridding (degridding) runtime will rise in
                                proportion to the support size of these convolution functions (in uv-pixels).

                                standard : Prolate Spheroid with 7x7 uv pixel support size

                                                 [ This mode can also be invoked using 'ft' or 'gridft' ]

                                wproject : W-Projection algorithm to correct for the widefield
                                                    non-coplanar baseline effect. [Cornwell et.al 2008]

                                                    wprojplanes is the number of distinct w-values at
                                                    which to compute and use different gridding convolution
                                                    functions (see help for wprojplanes).
                                                   Convolution function support size can range
                                                    from 5x5 to few 100 x few 100.

                                                 [ This mode can also be invoked using 'wprojectft' ]

                                widefield : Facetted imaging with or without W-Projection per facet.

                                                 A set of facets x facets subregions of the specified image
                                                 are gridded separately using their respective phase centers
                                                 (to minimize max W). Deconvolution is done on the joint
                                                 full size image, using a PSF from the first subregion.

                                                 wprojplanes=1 : standard prolate spheroid gridder per facet.
                                                 wprojplanes > 1 : W-Projection gridder per facet.
                                                 nfacets=1, wprojplanes > 1 : Pure W-Projection and no facetting
                                                 nfacets=1, wprojplanes=1 : Same as standard,ft,gridft

                                                 A combination of facetting and W-Projection is relevant only for
                                                 very large fields of view. (In our current version of tclean, this
                         					combination runs only with parallel=False.

                                mosaic : A-Projection with azimuthally symmetric beams without
                                                 sidelobes, beam rotation or squint correction.
                                                 Gridding convolution functions per visibility are computed
                                                 from FTs of PB models per antenna.
                                                 This gridder can be run on single fields as well as mosaics.

                                                VLA : PB polynomial fit model (Napier and Rots, 1982)
                                                EVLA : PB polynomial fit model (Perley, 2015)
                                                ALMA : Airy disks for a 10.7m dish (for 12m dishes) and
                                                            6.25m dish (for 7m dishes) each with 0.75m
                                                            blockages (Hunter/Brogan 2011). Joint mosaic
                                                            imaging supports heterogeneous arrays for ALMA.

                                                Typical gridding convolution function support sizes are
                                                between 7 and 50 depending on the desired
                                                accuracy (given by the uv cell size or image field of view).

                                                 [ This mode can also be invoked using 'mosaicft' or 'ftmosaic' ]

                                awproject : A-Projection with azimuthally asymmetric beams and
                                                     including beam rotation, squint correction,
                                                     conjugate frequency beams and W-projection.
                                                     [Bhatnagar et.al, 2008]

                                                     Gridding convolution functions are computed from
                                                     aperture illumination models per antenna and optionally
                                                     combined with W-Projection kernels and a prolate spheroid.
                                                     This gridder can be run on single fields as well as mosaics.

                                                 VLA : Uses ray traced model (VLA and EVLA) including feed
                                                          leg and subreflector shadows, off-axis feed location
                                                          (for beam squint and other polarization effects), and
                                                          a Gaussian fit for the feed beams (Ref: Brisken 2009)
                                                 ALMA : Similar ray-traced model as above (but the correctness
                                                             of its polarization properties remains un-verified).

                                                Typical gridding convolution function support sizes are
                                                between 7 and 50 depending on the desired
                                                accuracy (given by the uv cell size or image field of view).
                                                When combined with W-Projection they can be significantly larger.

                                                [ This mode can also be invoked using 'awprojectft' ]

                                imagemosaic : (untested implementation)
                                                        Grid and iFT each pointing separately and combine the
                                                        images as a linear mosaic (weighted by a PB model) in
                                                        the image domain before a joint minor cycle.

                                                        VLA/ALMA PB models are same as for gridder='mosaicft'

                           ------ Notes on PB models :

                                (1) Several different sources of PB models are used in the modes
                                     listed above. This is partly for reasons of algorithmic flexibility
                                     and partly due to the current  lack of a common beam model
                                     repository or consensus on what beam models are most appropriate.

                                (2) For ALMA and gridder='mosaic', ray-traced (TICRA) beams
                                     are also available via the vpmanager tool.
                                     For example, call the following before the tclean run.
                                    vp.setpbimage(telescope="ALMA",
                                    compleximage='/home/casa/data/trunk/alma/responses/ALMA_0_DV__0_0_360_0_45_90_348.5_373_373_GHz_ticra2007_VP.im',
                                    antnames=['DV'+'%02d'%k for k in range(25)])
                                    vp.saveastable('mypb.tab')
                                    Then, supply vptable='mypb.tab' to tclean.
                                    ( Currently this will work only for non-parallel runs )


                         ------ Note on PB masks :

                                  In tclean, A-Projection gridders (mosaic and awproject) produce a
                                  .pb image and use the 'pblimit' subparameter to decide normalization
                                  cutoffs and construct an internal T/F mask in the .pb and .image images.
                                  However, this T/F mask cannot directly be used during deconvolution
                                  (which needs a 1/0 mask). There are two options for making a pb based
                                  deconvolution mask.
                                     -- Run tclean with niter=0 to produce the .pb, construct a 1/0 image
                                  with the desired threshold (using ia.open('newmask.im');
                                  ia.calc('iif("xxx.pb">0.3,1.0,0.0)');ia.close() for example),
                                  and supply it via the 'mask' parameter in a subsequent run
                                  (with calcres=F and calcpsf=F to restart directly from the minor cycle).
                                     -- Run tclean with usemask='pb' for it to automatically construct
                                  a 1/0 mask from the internal T/F mask from .pb at a fixed 0.2 threshold.

                         ----- Making PBs for gridders other than mosaic,awproject

                               After the PSF generation, a PB is constructed using the same
                               models used in gridder='mosaic' but just evaluated in the image
                               domain without consideration to weights.
    facets               Number of facets on a side

                         A set of (facets x facets) subregions of the specified image
                         are gridded separately using their respective phase centers
                         (to minimize max W). Deconvolution is done on the joint
                         full size image, using a PSF from the first subregion/facet.

                         		       In our current version of tclean, facets>1 may be used only
                         		       with parallel=False.
    psfphasecenter       For mosaic use psf centered on this
                         optional direction. You may need to use
                         this if for example the mosaic does not
                         have any pointing in the center of the
                         image. Another reason; as the psf is
                         approximate for a mosaic, this may help
                         to deconvolve a non central bright source
                         well and quickly.

                         example:

                            psfphasecenter=6 #center psf on field 6
                            psfphasecenter='J2000 19h30m00 -40d00m00'
                            psfphasecenter='J2000 292.5deg -40.0deg'
                            psfphasecenter='J2000 5.105rad -0.698rad'
                            psfphasecenter='ICRS 13:05:27.2780 -049.28.04.458'
    wprojplanes          Number of distinct w-values at which to compute and use different
                         gridding convolution functions for W-Projection

                         An appropriate value of wprojplanes depends on the presence/absence
                         of a bright source far from the phase center, the desired dynamic
                         range of an image in the presence of a bright far out source,
                         the maximum w-value in the measurements, and the desired trade off
                         between accuracy and computing cost.

                         As a (rough) guide, VLA L-Band D-config may require a
                         value of 128 for a source 30arcmin away from the phase
                         center. A-config may require 1024 or more. To converge to an
                         appropriate value, try starting with 128 and then increasing
                         it if artifacts persist. W-term artifacts (for the VLA) typically look
                         like arc-shaped smears in a synthesis image or a shift in source
                         position between images made at different times. These artifacts
                         are more pronounced the further the source is from the phase center.

                         There is no harm in simply always choosing a large value (say, 1024)
                         but there will be a significant performance cost to doing so, especially
                         for gridder='awproject' where it is combined with A-Projection.

                         wprojplanes=-1 is an option for gridder='widefield' or 'wproject'
                         in which the number of planes is automatically computed.
    vptable              vpmanager

                         vptable="" : Choose default beams for different telescopes
                                             ALMA : Airy disks
                                             EVLA : old VLA models.

                         Other primary beam models can be chosen via the vpmanager tool.

                         Step 1 :  Set up the vpmanager tool and save its state in a table

                                       vp.setpbpoly(telescope='EVLA', coeff=[1.0, -1.529e-3, 8.69e-7, -1.88e-10])
                                       vp.saveastable('myvp.tab')

                         Step 2 : Supply the name of that table in tclean.

                                      tclean(....., vptable='myvp.tab',....)

                         Please see the documentation for the vpmanager for more details on how to
                         choose different beam models. Work is in progress to update the defaults
                         for EVLA and ALMA.

                         Note : AWProjection currently does not use this mechanism to choose
                                   beam models. It instead uses ray-traced beams computed from
                                   parameterized aperture illumination functions, which are not
                                   available via the vpmanager. So, gridder='awproject' does not allow
                                   the user to set this parameter.
    mosweight            When doing Brigg's style weighting (including uniform) to perform the weight density calculation for each field indepedently if True. If False the weight density is calculated from the average uv distribution of all the fields.
    aterm                Use aperture illumination functions during gridding

                         This parameter turns on the A-term of the AW-Projection gridder.
                         Gridding convolution functions are constructed from aperture illumination
                         function models of each antenna.
    psterm               Include the Prolate Spheroidal (PS) funtion as the anti-aliasing
                         operator in the gridding convolution functions used for gridding.

                         Setting this parameter to true is necessary when aterm is set to
                         false.  It can be set to false when aterm is set to true, though
                         with this setting effects of aliasing may be there in the image,
                         particularly near the edges.

                         When set to true, the .pb images will contain the fourier transform
                         of the of the PS funtion. The table below enumarates the functional
                         effects of the psterm, aterm and wprojplanes settings. PB referes to
                         the Primary Beam and FT() refers to the Fourier transform operation.

                         Operation       aterm   psterm  wprojplanes  Contents of the .pb image
                         ----------------------------------------------------------------------
                         AW-Projection    True    True      >1                FT(PS) x PB
                                                  False                       PB

                         A-Projection     True    True       1                FT(PS) x PB
                                                  False                       PB

                         W-Projection     False   True      >1                FT(PS)

                         Standard         False   True       1                FT(PS)
    wbawp                Use frequency dependent A-terms
                         Scale aperture illumination functions appropriately with frequency
                         when gridding and combining data from multiple channels.
    conjbeams            Use conjugate frequency for wideband A-terms

                         While gridding data from one frequency channel, choose a convolution
                         function from a 'conjugate' frequency such that the resulting baseline
                         primary beam is approximately constant across frequency. For a system in
                         which the primary beam scales with frequency, this step will eliminate
                         instrumental spectral structure from the measured data and leave only the
                         sky spectrum for the minor cycle to model and reconstruct [Bhatnagar et al., ApJ, 2013].

                         As a rough guideline for when this is relevant, a source at the half power
                         point of the PB at the center frequency will see an artificial spectral
                         index of -1.4 due to the frequency dependence of the PB [Sault and Wieringa, 1994].
                         If left uncorrected during gridding, this spectral structure must be modeled
                         in the minor cycle (using the mtmfs algorithm) to avoid dynamic range limits
                         (of a few hundred for a 2:1 bandwidth).
                         This works for specmode='mfs' and its value is ignored for cubes
    cfcache              Convolution function cache directory name

                         Name of a directory in which to store gridding convolution functions.
                         This cache is filled at the beginning of an imaging run. This step can be time
                         consuming but the cache can be reused across multiple imaging runs that
                         use the same image parameters (cell size, image size , spectral data
                         selections, wprojplanes, wbawp, psterm, aterm).  The effect of the wbawp,
                         psterm and aterm settings is frozen-in in the cfcache. Using an existing cfcache
                         made with a different setting of these parameters will not reflect the current
                         settings.

                         In a parallel execution, the construction of the cfcache is also parallelized
                         and the time to compute scales close to linearly with the number of compute
                         cores used.   With the re-computation of Convolution Functions (CF) due to PA
                         rotation turned-off (the computepastep parameter), the total number of in the
                         cfcache can be computed as [No. of wprojplanes x No. of selected spectral windows x 4]

                         By default, cfcache = imagename + '.cf'
    usepointing          The usepointing flag informs the gridder that it should utilize the pointing table
                         to use the correct direction in which the antenna is pointing with respect to the pointing phasecenter.
    computepastep        Parallactic angle interval after the AIFs are recomputed (deg)

                         This parameter controls the accuracy of the aperture illumination function
                         used with AProjection for alt-az mount dishes where the AIF rotates on the
                         sky as the synthesis image is built up.  Once the PA in the data changes by
                         the given interval, AIFs are re-computed at the new PA.

                         A value of 360.0 deg (the default) implies no re-computation due to PA rotation.
                         AIFs are computed for the PA value of the first valid data received and used for
                         all of the data.
    rotatepastep         Parallactic angle interval after which the nearest AIF is rotated (deg)

                         Instead of recomputing the AIF for every timestep's parallactic angle,
                         the nearest existing AIF is used and rotated
                         after the PA changed by rotatepastep value.

                         A value of 360.0 deg (the default) disables rotation of the AIF.

                         For example, computepastep=360.0 and rotatepastep=5.0 will compute
                         the AIFs at only the starting parallactic angle and all other timesteps will
                         use a rotated version of that AIF at the nearest 5.0 degree point.
    pointingoffsetsigdev Corrections for heterogenous and time-dependent pointing
                          offsets via AWProjection are controlled by this parameter.
                          It is a vector of 2 ints or doubles each of which is interpreted
                          in units of arcsec. Based on the first threshold, a clustering
                          algorithm is applied to entries from the POINTING subtable
                          of the MS to determine how distinct antenna groups for which
                          the pointing offset must be computed separately.  The second
                          number controls how much a pointing change across time can
                          be ignored and after which an antenna rebinning is required.


                         Note : The default value of this parameter is [], due a programmatic constraint.
                                    If run with this value, it will internally pick [600,600] and exercise the
                                    option of using large tolerances (10arcmin) on both axes. Please choose
                                    a setting explicitly for runs that need to use this parameter.

                         	                Note : This option is available only for gridder='awproject' and usepointing=True and
                                    and has been validated primarily with VLASS on-the-fly mosaic data
                                    where POINTING subtables have been modified after the data are recorded.


                         		        Examples of parameter usage :

                         [100.0,100.0] : Pointing offsets of 100 arcsec or less are considered
                                                 small enough to be ignored.  Using large values for both
                                                 indicates a homogeneous array.


                         [10.0, 100.0] : Based on entries in the POINTING subtable, antennas
                                                are grouped into clusters based on a 10arcsec bin size.
                                                All antennas in a bin are given a pointing offset calculated
                                                as the average of the offsets of all antennas in the bin.
                                                On the time axis, offset changes upto 100 arcsec will be ignored.

                         [10.0,10.0] : Calculate separate pointing offsets for each antenna group
                                              (with a 10 arcsec bin size). As a function of time, recalculate
                                              the antenna binning if the POINTING table entries change by
                                              more than 10 arcsec w.r.to the previously computed binning.

                         [1.0, 1.0] :  Tight tolerances will imply a fully heterogenous situation where
                                            each antenna gets its own pointing offset. Also, time-dependent
                                            offset changes greater than 1 arcsec will trigger recomputes of
                                            the phase gradients. This is the most general situation and is also
                                            the most expensive option as it constructs and uses separate
                                            phase gradients for all baselines and timesteps.

                         For VLASS 1.1 data with two kinds of pointing offsets, the recommended
                         setting is [ 30.0, 30.0 ].

                         For VLASS 1.2 data with only the time-dependent pointing offsets, the
                         recommended setting is [ 300.0, 30.0 ] to turn off the antenna grouping
                         but to retain the time dependent corrections required from one timestep
                         to the next.
    pblimit              PB gain level at which to cut off normalizations

                          Divisions by .pb during normalizations have a cut off at a .pb gain
                          level given by pblimit. Outside this limit, image values are set to zero.
                          Additionally, by default, an internal T/F mask is applied to the .pb, .image and
                          .residual images to mask out (T) all invalid pixels outside the pblimit area.

                         Note : This internal T/F mask cannot be used as a deconvolution mask.
                                    To do so, please follow the steps listed above in the Notes for the
                                    'gridder' parameter.

                         Note : To prevent the internal T/F mask from appearing in anything other
                                    than the .pb and .image.pbcor images, 'pblimit' can be set to a
                                    negative number.
                                    The absolute value will still be used as a valid 'pblimit' for normalization
                                    purposes. So, for example, pick pblimit=-0.1 (and not pblimit=-1).
                                    A tclean restart using existing output images on disk that already
                                    have this T/F mask in the .residual and .image but only pblimit set
                                    to a negative value, will remove this mask after the next major cycle.

                         Note : An existing internal T/F mask may be removed from an image as
                                    follows (without needing to re-run tclean itself).
                                          ia.open('test.image');
                                          ia.maskhandler(op='set', name='');
                                          ia.done()
    normtype             Normalization type (flatnoise, flatsky, pbsquare)

                          Gridded (and FT'd) images represent the PB-weighted sky image.
                          Qualitatively it can be approximated as two instances of the PB
                          applied to the sky image (one naturally present in the data
                          and one introduced during gridding via the convolution functions).

                          xxx.weight : Weight image approximately equal to sum ( square ( pb ) )
                          xxx.pb : Primary beam calculated as  sqrt ( xxx.weight )

                          normtype='flatnoise' : Divide the raw image by sqrt(.weight) so that
                                                              the input to the minor cycle represents the
                                                              product of the sky and PB. The noise is 'flat'
                                                              across the region covered by each PB.

                         normtype='flatsky' : Divide the raw image by .weight so that the input
                                                          to the minor cycle represents only the sky.
                                                          The noise is higher in the outer regions of the
                                                          primary beam where the sensitivity is low.

                         normtype='pbsquare' : No normalization after gridding and FFT.
                                                               The minor cycle sees the sky times pb square
    deconvolver          Name of minor cycle algorithm (hogbom,clark,multiscale,mtmfs,mem,clarkstokes,asp)

                         Each of the following algorithms operate on residual images and psfs
                         from the gridder and produce output model and restored images.
                         Minor cycles stop and a major cycle is triggered when cyclethreshold
                         or cycleniter are reached. For all methods, components are picked from
                         the entire extent of the image or (if specified) within a mask.

                         hogbom : An adapted version of Hogbom Clean [Hogbom, 1974]
                                         - Find the location of the peak residual
                                         - Add this delta function component to the model image
                                         - Subtract a scaled and shifted PSF of the same size as the image
                                           from regions of the residual image where the two overlap.
                                         - Repeat

                         clark : An adapted version of Clark Clean [Clark, 1980]
                                         - Find the location of max(I^2+Q^2+U^2+V^2)
                                         - Add delta functions to each stokes plane of the model image
                                         - Subtract a scaled and shifted PSF within a small patch size
                                           from regions of the residual image where the two overlap.
                                         - After several iterations trigger a Clark major cycle to subtract
                                           components from the visibility domain, but without de-gridding.
                                         - Repeat

                                        ( Note : 'clark' maps to imagermode='' in the old clean task.
                                                     'clark_exp' is another implementation that maps to
                                                      imagermode='mosaic' or 'csclean' in the old clean task
                                                      but the behavior is not identical. For now, please
                                                      use deconvolver='hogbom' if you encounter problems. )

                         clarkstokes : Clark Clean operating separately per Stokes plane

                                    (Note : 'clarkstokes_exp' is an alternate version. See above.)

                         multiscale : MultiScale Clean [Cornwell, 2008]
                                         - Smooth the residual image to multiple scale sizes
                                         - Find the location and scale at which the peak occurs
                                         - Add this multiscale component to the model image
                                         - Subtract a scaled,smoothed,shifted PSF (within a small
                                           patch size per scale) from all residual images
                                         - Repeat from step 2

                         mtmfs : Multi-term (Multi Scale) Multi-Frequency Synthesis [Rau and Cornwell, 2011]
                                         - Smooth each Taylor residual image to multiple scale sizes
                                         - Solve a NTxNT system of equations per scale size to compute
                                           Taylor coefficients for components at all locations
                                         - Compute gradient chi-square and pick the Taylor coefficients
                                            and scale size at the location with maximum reduction in
                                            chi-square
                                         - Add multi-scale components to each Taylor-coefficient
                                           model image
                                         - Subtract scaled,smoothed,shifted PSF (within a small patch size
                                           per scale) from all smoothed Taylor residual images
                                         - Repeat from step 2


                         mem : Maximum Entropy Method [Cornwell and Evans, 1985]
                                         - Iteratively solve for values at all individual pixels via the
                                           MEM method. It minimizes an objective function of
                                            chi-square plus entropy (here, a measure of difference
                                           between the current model and a flat prior model).

                                           (Note : This MEM implementation is not very robust.
                                                        Improvements will be made in the future.)

                         asp : Adaptive Scale Pixel algorithm [Bhatnagar and Cornwell, 2004]
                                         - Define a set of initial scales defined as 0, W, 2W 4W and 8W
                                           where W is a 2D Gaussian fitting width to the PSF
                                         - Smooth the residual image by a Gaussian beam at initial scales
                                         - Search for the global peak (F) among these smoothed residual images
                                         - form an active Aspen set: amplitude(F), amplitude location(x,y)
                                         - Optimize the Aspen set by minimizing the objective function RI-Aspen*PSF,
                                           where RI is the residual image and * is the convulition operation.
                                         - Compute the model image and update the residual image
                                         - Repeat from step 2

                         				       (Note : This is an experimental version of the ASP algorithm.)
    scales               List of scale sizes (in pixels) for multi-scale and mtmfs algorithms.
                         -->  scales=[0,6,20]
                         This set of scale sizes should represent the sizes
                         (diameters in units of number of pixels)
                         of dominant features in the image being reconstructed.

                         The smallest scale size is recommended to be 0 (point source),
                         the second the size of the synthesized beam and the third 3-5
                         times the synthesized beam, etc. For example, if the synthesized
                         beam is 10" FWHM and cell=2",try scales = [0,5,15].

                         For numerical stability, the largest scale must be
                         smaller than the image (or mask) size and smaller than or
                         comparable to the scale corresponding to the lowest measured
                         spatial frequency (as a scale size much larger than what the
                         instrument is sensitive to is unconstrained by the data making
                         it harder to recovery from errors during the minor cycle).
    nterms               Number of Taylor coefficients in the spectral model

                         - nterms=1 : Assume flat spectrum source
                         - nterms=2 : Spectrum is a straight line with a slope
                         - nterms=N : A polynomial of order N-1

                         From a Taylor expansion of the expression of a power law, the
                         spectral index is derived as alpha = taylorcoeff_1 / taylorcoeff_0

                         Spectral curvature is similarly derived when possible.

                         The optimal number of Taylor terms depends on the available
                         signal to noise ratio, bandwidth ratio, and spectral shape of the
                         source as seen by the telescope (sky spectrum x PB spectrum).

                         nterms=2 is a good starting point for wideband EVLA imaging
                         and the lower frequency bands of ALMA (when fractional bandwidth
                         is greater than 10%) and if there is at least one bright source for
                         which a dynamic range of greater than few 100 is desired.

                         Spectral artifacts for the VLA often look like spokes radiating out from
                         a bright source (i.e. in the image made with standard mfs imaging).
                         If increasing the number of terms does not eliminate these artifacts,
                         check the data for inadequate bandpass calibration. If the source is away
                         from the pointing center, consider including wide-field corrections too.

                         (Note : In addition to output Taylor coefficient images .tt0,.tt1,etc
                                     images of spectral index (.alpha), an estimate of error on
                                     spectral index (.alpha.error) and spectral curvature (.beta,
                                     if nterms is greater than 2) are produced.
                                     - These alpha, alpha.error and beta images contain
                                       internal T/F masks based on a threshold computed
                                       as peakresidual/10. Additional masking based on
                                      .alpha/.alpha.error may be desirable.
                                     - .alpha.error is a purely empirical estimate derived
                                       from the propagation of error during the division of
                                       two noisy numbers (alpha = xx.tt1/xx.tt0) where the
                                       'error' on tt1 and tt0 are simply the values picked from
                                       the corresponding residual images. The absolute value
                                       of the error is not always accurate and it is best to interpret
                                       the errors across the image only in a relative sense.)
    smallscalebias       A numerical control to bias the scales when using multi-scale or mtmfs algorithms.
                         The peak from each scale's smoothed residual is
                         multiplied by ( 1 - smallscalebias \* scale/maxscale )
                         to increase or decrease the amplitude relative to other scales,
                         before the scale with the largest peak is chosen.
                         Smallscalebias can be varied between -1.0 and 1.0.
                         A score of 0.0 gives all scales equal weight (default).
                         		      A score larger than 0.0 will bias the solution towards smaller scales.
                         		      A score smaller than 0.0 will bias the solution towards larger scales.
                         		      The effect of smallscalebias is more pronounced when using multi-scale relative to mtmfs.
    fusedthreshold       ring Hogbom Clean (number in units of Jy)

                         fusedthreshold = 0.0001  : 0.1 mJy

                         This is a subparameter of the Asp Clean deconvolver. When peak residual
                         is lower than the threshold, Asp Clean is "switched to Hogbom Clean" (i.e. only use the 0 scale for cleaning) for
                         the following number of iterations until it switches back to Asp Clean.

                         NumberIterationsInHogbom = 50 + 2 * (exp(0.05 * NthHogbom) - 1)

                         , where NthHogbom is the number of times Hogbom Clean has been triggered.

                         When the Asp Clean detects it is approaching convergence, it uses only the 0 scale for the following number of iterations for better computational efficiency.

                         NumberIterationsInHogbom = 500 + 2 * (exp(0.05 * NthHogbom) - 1)

                         Set 'fusedthreshold = -1' to make the Asp Clean deconvolver never "switch" to Hogbom Clean.
    largestscale         xels) allowed for the initial guess for the Asp Clean deconvolver.

                         largestscale = 100

                         The default initial scale sizes used by Asp Clean is [0, w, 2w, 4w, 8w],
                         		     where `w` is the PSF width. The default `largestscale` is -1 which indicates
                         		     users accept these initial scales. If `largestscale` is set, the initial scales
                         		     would be [0, w, ... up to the `largestscale`]. This is only an initial guess,
                         		     and actual fitted scale sizes may evolve from these initial values.

                         		     It is recommended not to set `largestscale` unless Asp Clean picks a large
                         		     scale that has no constraints from the data (the UV hole issue).
    restoration          e.

                         Construct a restored image : imagename.image by convolving the model
                         image with a clean beam and adding the residual image to the result.
                         If a restoringbeam is specified, the residual image is also
                         smoothed to that target resolution before adding it in.

                         If a .model does not exist, it will make an empty one and create
                         the restored image from the residuals ( with additional smoothing if needed ).
                         With algorithm='mtmfs', this will construct Taylor coefficient maps from
                         the residuals and compute .alpha and .alpha.error.
    restoringbeam        ize to use.

                         - restoringbeam='' or ['']
                           A Gaussian fitted to the PSF main lobe (separately per image plane).

                         - restoringbeam='10.0arcsec'
                           Use a circular Gaussian of this width for all planes

                         - restoringbeam=['8.0arcsec','10.0arcsec','45deg']
                           Use this elliptical Gaussian for all planes

                         - restoringbeam='common'
                           Automatically estimate a common beam shape/size appropriate for
                           all planes.

                         Note : For any restoring beam different from the native resolution
                                    the model image is convolved with the beam and added to
                                    residuals that have been convolved to the same target resolution.
    pbcor                the output restored image

                         A new image with extension .image.pbcor will be created from
                         the evaluation of   .image / .pb  for all pixels above the specified pblimit.

                         Note : Stand-alone PB-correction can be triggered by re-running
                                   tclean with the appropriate imagename and with
                                   niter=0, calcpsf=False, calcres=False, pbcor=True, vptable='vp.tab'
                                   ( where vp.tab is the name of the vpmanager file.
                                      See the inline help for the 'vptable' parameter )

                         Note : Multi-term PB correction that includes a correction for the
                                   spectral index of the PB has not been enabled for the 4.7 release.
                                   Please use the widebandpbcor task instead.
                                   ( Wideband PB corrections are required when the amplitude of the
                                      brightest source is known accurately enough to be sensitive
                                      to the difference in the PB gain between the upper and lower
                                      end of the band at its location. As a guideline, the artificial spectral
                                      index due to the PB is -1.4 at the 0.5 gain level and less than -0.2
                                      at the 0.9 gain level at the middle frequency )
    outlierfile          Name of outlier-field image definitions

                         A text file containing sets of parameter=value pairs,
                         one set per outlier field.

                         Example :   outlierfile='outs.txt'

                                            Contents of outs.txt :

                                                      imagename=tst1
                                                      nchan=1
                                                      imsize=[80,80]
                                                      cell=[8.0arcsec,8.0arcsec]
                                                      phasecenter=J2000 19:58:40.895 +40.55.58.543
                                                      mask=circle[[40pix,40pix],10pix]

                                                      imagename=tst2
                                                      nchan=1
                                                      imsize=[100,100]
                                                      cell=[8.0arcsec,8.0arcsec]
                                                      phasecenter=J2000 19:58:40.895 +40.56.00.000
                                                      mask=circle[[60pix,60pix],20pix]

                            The following parameters are currently allowed to be different between
                            the main field and the outlier fields (i.e. they will be recognized if found
                            in the outlier text file). If a parameter is not listed, the value is picked from
                            what is defined in the main task input.

                                imagename, imsize, cell, phasecenter, startmodel, mask
                                specmode, nchan, start, width, nterms, reffreq,
                                gridder, deconvolver, wprojplanes

                            Note : 'specmode' is an option, so combinations of mfs and cube
                                       for different image fields, for example, are supported.
                                      'deconvolver' and 'gridder' are also options that allow different
                                       imaging or deconvolution algorithm per image field.

                                       For example, multiscale with wprojection and 16 w-term planes
                                       on the main field and mtmfs with nterms=3 and wprojection
                                       with 64 planes on a bright outlier source for which the frequency
                                       dependence of the primary beam produces a strong effect that
                                       must be modeled.   The traditional alternative to this approach is
                                       to first image the outlier, subtract it out of the data (uvsub) and
                                       then image the main field.

                            Note : If you encounter a use-case where some other parameter needs
                                      to be allowed in the outlier file (and it is logical to do so), please
                                      send us feedback. The above is an initial list.
    weighting            Weighting scheme (natural,uniform,briggs,superuniform,radial, briggsabs, briggsbwtaper)

                                 During gridding of the dirty or residual image, each visibility value is
                                 multiplied by a weight before it is accumulated on the uv-grid.
                                 The PSF's uv-grid is generated by gridding only the weights (weightgrid).

                                 weighting='natural' : Gridding weights are identical to the data weights
                                                                   from the MS. For visibilities with similar data weights,
                                                                   the weightgrid will follow the sample density
                                                                   pattern on the uv-plane. This weighting scheme
                                                                   provides the maximum imaging sensitivity at the
                                                                   expense of a possibly fat PSF with high sidelobes.
                                                                   It is most appropriate for detection experiments
                                                                   where sensitivity is most important.

                                 weighting='uniform' : Gridding weights per visibility data point are the
                                                                    original data weights divided by the total weight of
                                                                    all data points that map to the same uv grid cell :
                                                                    ' data_weight / total_wt_per_cell '.

                                                                    The weightgrid is as close to flat as possible resulting
                                                                    in a PSF with a narrow main lobe and suppressed
                                                                    sidelobes. However, since heavily sampled areas of
                                                                    the uv-plane get down-weighted, the imaging
                                                                    sensitivity is not as high as with natural weighting.
                                                                    It is most appropriate for imaging experiments where
                                                                    a well behaved PSF can help the reconstruction.

                                 weighting='briggs' :  Gridding weights per visibility data point are given by
                                                                   'data_weight / ( A \* total_wt_per_cell + B ) ' where
                                                                   A and B vary according to the 'robust' parameter.

                                                                   robust = -2.0 maps to A=1,B=0 or uniform weighting.
                                                                   robust = +2.0 maps to natural weighting.
                                                                   (robust=0.5 is equivalent to robust=0.0 in AIPS IMAGR.)

                                                                   Robust/Briggs weighting generates a PSF that can
                                                                   vary smoothly between 'natural' and 'uniform' and
                                                                   allow customized trade-offs between PSF shape and
                                                                   imaging sensitivity.
                                  weighting='briggsabs' : Experimental option.
                                                                   Same as Briggs except the formula is different A=
                                                                   robust\*robust and B is dependent on the
                                                                   noise per visibility estimated. Giving noise='0Jy'
                                                                   is a not a reasonable option.
                                                                   In this mode (or formula)  robust values
                                                                   from -2.0 to 0.0 only make sense (2.0 and
                                                                   -2.0 will get the same weighting)

                                 weighting='superuniform' : This is similar to uniform weighting except that
                                                                              the total_wt_per_cell is replaced by the
                                                                              total_wt_within_NxN_cells around the uv cell of
                                                                              interest. N=7 is the default (when the
                         								    parameter 'npixels' is set to 0 with 'superuniform')

                                                                             This method tends to give a PSF with inner
                                                                             sidelobes that are suppressed as in uniform
                                                                             weighting but with far-out sidelobes closer to
                                                                             natural weighting. The peak sensitivity is also
                                                                             closer to natural weighting.

                                 weighting='radial' : Gridding weights are given by ' data_weight \* uvdistance '
                                                                This method approximately minimizes rms sidelobes
                                                                for an east-west synthesis array.

                                 weighting='briggsbwtaper' : A modified version of Briggs weighting for cubes where an inverse uv taper,
                                                                   which is proportional to the fractional bandwidth of the entire cube,
                                                                   is applied per channel. The objective is to modify cube (perchanweightdensity = True)
                                                                   imaging weights to have a similar density to that of the continuum imaging weights.
                                                                   This is currently an experimental weighting scheme being developed for ALMA.

                         For more details on weighting please see Chapter3
                         of Dan Briggs' thesis (http://www.aoc.nrao.edu/dissertations/dbriggs)
    robust               Robustness parameter for Briggs weighting.

                         robust = -2.0 maps to uniform weighting.
                         robust = +2.0 maps to natural weighting.
                         (robust=0.5 is equivalent to robust=0.0 in AIPS IMAGR.)
    noise                noise parameter for briggs abs mode weighting
    npixels              Number of pixels to determine uv-cell size for super-uniform weighting
                          (0 defaults to -/+ 3 pixels)

                         npixels -- uv-box used for weight calculation
                                        a box going from -npixel/2 to +npixel/2 on each side
                                       around a point is used to calculate weight density.

                         npixels=2 goes from -1 to +1 and covers 3 pixels on a side.

                         npixels=0 implies a single pixel, which does not make sense for
                                         superuniform weighting. Therefore, for 'superuniform'
                         				     weighting, if npixels=0 it will be forced to 6 (or a box
                         				     of -3pixels to +3pixels) to cover 7 pixels on a side.
    uvtaper              uv-taper on outer baselines in uv-plane

                                          Apply a Gaussian taper in addition to the weighting scheme specified
                                          via the 'weighting' parameter. Higher spatial frequencies are weighted
                                          down relative to lower spatial frequencies to suppress artifacts
                                          arising from poorly sampled areas of the uv-plane. It is equivalent to
                                          smoothing the PSF obtained by other weighting schemes and can be
                                          specified either as the HWHM of a Gaussian in uv-space (eg. units of lambda)
                                          or as the FWHM of a Gaussian in the image domain (eg. angular units like arcsec).

                                          uvtaper = [bmaj, bmin, bpa]

                         		   Note : FWHM_uv_lambda = (4 log2) / ( pi * FWHM_lm_radians )

                         		   A FWHM_lm of 100.000 arcsec maps to a HWHM_uv of 910.18 lambda
                                          A FWHM_lm of 1 arcsec maps to a HWHM_uv of 91 klambda

                                          default: uvtaper=[]; no Gaussian taper applied
                                          example: uvtaper=['5klambda']  circular taper of  HWHM=5 kilo-lambda
                                                   uvtaper=['5klambda','3klambda','45.0deg'] uv-domain HWHM
                         			    uvtaper=['50arcsec','30arcsec','30.0deg'] : image domain FWHM
                                                   uvtaper=['10arcsec'] : image domain FWHM
                                                   uvtaper=['300.0'] default units are lambda in aperture plane
    niter                Maximum number of iterations

                         A stopping criterion based on total iteration count.
                         Currently the parameter type is defined as an integer therefore the integer value
                         larger than 2147483647 will not be set properly as it causes an overflow.

                         Iterations are typically defined as the selecting one flux component
                         and partially subtracting it out from the residual image.

                         niter=0 : Do only the initial major cycle (make dirty image, psf, pb, etc)

                         niter larger than zero : Run major and minor cycles.

                         Note : Global stopping criteria vs major-cycle triggers

                                    In addition to global stopping criteria, the following rules are
                                    used to determine when to terminate a set of minor cycle iterations
                                    and trigger major cycles [derived from Cotton-Schwab Clean, 1984]

                                    'cycleniter' : controls the maximum number of iterations per image
                                                        plane before triggering a major cycle.
                                    'cyclethreshold' : Automatically computed threshold related to the
                                                                max sidelobe level of the PSF and peak residual.
                                     Divergence, detected as an increase of 10% in peak residual from the
                                     minimum so far (during minor cycle iterations)

                                     The first criterion to be satisfied takes precedence.

                         Note :  Iteration counts for cubes or multi-field images :
                                     For images with multiple planes (or image fields) on which the
                                     deconvolver operates in sequence, iterations are counted across
                                     all planes (or image fields). The iteration count is compared with
                                     'niter' only after all channels/planes/fields have completed their
                                     minor cycles and exited either due to 'cycleniter' or 'cyclethreshold'.
                                     Therefore, the actual number of iterations reported in the logger
                                     can sometimes be larger than the user specified value in 'niter'.
                                     For example, with niter=100, cycleniter=20,nchan=10,threshold=0,
                                     a total of 200 iterations will be done in the first set of minor cycles
                                     before the total is compared with niter=100 and it exits.

                          Note : Additional global stopping criteria include
                                    - no change in peak residual across two major cycles
                                    - a 50% or more increase in peak residual across one major cycle
    gain                 Loop gain

                         Fraction of the source flux to subtract out of the residual image
                         for the CLEAN algorithm and its variants.

                         A low value (0.2 or less) is recommended when the sky brightness
                         distribution is not well represented by the basis functions used by
                         the chosen deconvolution algorithm. A higher value can be tried when
                         there is a good match between the true sky brightness structure and
                         the basis function shapes.  For example, for extended emission,
                         multiscale clean with an appropriate set of scale sizes will tolerate
                         a higher loop gain than Clark clean (for example).
    threshold            Stopping threshold (number in units of Jy, or string)

                         A global stopping threshold that the peak residual (within clean mask)
                         across all image planes is compared to.

                         threshold = 0.005  : 5mJy
                         threshold = '5.0mJy'

                         Note : A 'cyclethreshold' is internally computed and used as a major cycle
                                    trigger. It is related what fraction of the PSF can be reliably
                                    used during minor cycle updates of the residual image. By default
                                    the minor cycle iterations terminate once the peak residual reaches
                                    the first sidelobe level of the brightest source.

                                    'cyclethreshold' is computed as follows using the settings in
                                     parameters 'cyclefactor','minpsffraction','maxpsffraction','threshold' :

                                   psf_fraction = max_psf_sidelobe_level \* 'cyclefactor'
                                   psf_fraction = max(psf_fraction, 'minpsffraction');
                                   psf_fraction = min(psf_fraction, 'maxpsffraction');
                                   cyclethreshold = peak_residual \* psf_fraction
                                   cyclethreshold = max( cyclethreshold, 'threshold' )

                                   If nsigma is set (>0.0), the N-sigma threshold is calculated (see
                                   the description under nsigma), then cyclethreshold is further modified as,

                                   cyclethreshold = max( cyclethreshold, nsgima_threshold )


                                   'cyclethreshold' is made visible and editable only in the
                                   interactive GUI when tclean is run with interactive=True.
    nsigma               Multiplicative factor for rms-based threshold stopping

                         N-sigma threshold is calculated as nsigma \* rms value per image plane determined
                         from a robust statistics. For nsigma > 0.0, in a minor cycle, a maximum of the two values,
                         the N-sigma threshold and cyclethreshold, is used to trigger a major cycle
                         (see also the descreption under 'threshold').
                         Set nsigma=0.0 to preserve the previous tclean behavior without this feature.
                         The top level parameter, fastnoise is relevant for the rms noise calculation which is used
                         to determine the threshold.

                         		       The parameter 'nsigma' may be an int, float, or a double.
    cycleniter           Maximum number of minor-cycle iterations (per plane) before triggering
                         a major cycle

                         For example, for a single plane image, if niter=100 and cycleniter=20,
                         there will be 5 major cycles after the initial one (assuming there is no
                         threshold based stopping criterion). At each major cycle boundary, if
                         the number of iterations left over (to reach niter) is less than cycleniter,
                         it is set to the difference.

                         Note : cycleniter applies per image plane, even if cycleniter x nplanes
                                    gives a total number of iterations greater than 'niter'. This is to
                                    preserve consistency across image planes within one set of minor
                                    cycle iterations.
    cyclefactor          Scaling on PSF sidelobe level to compute the minor-cycle stopping threshold.

                         Please refer to the Note under the documentation for 'threshold' that
                         discussed the calculation of 'cyclethreshold'

                         cyclefactor=1.0 results in a cyclethreshold at the first sidelobe level of
                         the brightest source in the residual image before the minor cycle starts.

                         cyclefactor=0.5 allows the minor cycle to go deeper.
                         cyclefactor=2.0 triggers a major cycle sooner.
    minpsffraction       PSF fraction that marks the max depth of cleaning in the minor cycle

                         Please refer to the Note under the documentation for 'threshold' that
                         discussed the calculation of 'cyclethreshold'

                         For example, minpsffraction=0.5 will stop cleaning at half the height of
                         the peak residual and trigger a major cycle earlier.
    maxpsffraction       PSF fraction that marks the minimum depth of cleaning in the minor cycle

                         Please refer to the Note under the documentation for 'threshold' that
                         discussed the calculation of 'cyclethreshold'

                         For example, maxpsffraction=0.8 will ensure that at least the top 20
                         percent of the source will be subtracted out in the minor cycle even if
                         the first PSF sidelobe is at the 0.9 level (an extreme example), or if the
                         cyclefactor is set too high for anything to get cleaned.
    nmajor               The nmajor parameter limits the number of minor and major cycle sets
                         that tclean executes. It is defined as the number of major cycles after the
                         initial set of minor cycle iterations. In other words, the count of nmajor does
                         not include the initial residual calculation that occurs when calcres=True.

                         A setting of nmajor=-1 implies no limit (default -1).
                         A setting of nmajor=0 implies nothing other than the initial residual calculation
                         A setting of nmajor>0 imples that nmajor sets of minor and major cycles will
                         be done in addition to the initial residual calculation.

                         If the major cycle limit is reached, stopcode 9 will be returned. Other stopping
                         criteria (such as threshold) could cause tclean to stop in fewer than this
                         number of major cycles. If tclean reaches another stopping criteria, first
                         or at the same time as nmajor, then that stopcode will be returned instead.

                         Note however that major cycle ids in the log messages as well as in the return
                         dictionary do begin with 1 for the initial residual calculation, when it exists.

                         Example 1 : A tclean run with 'nmajor=5' and 'calcres=True' will iterate for
                         5 major cycles (not counting the initial residual calculation). But, the return
                         dictionary will show 'nmajordone:6'.  If 'calcres=False', then the return
                         dictionary will show 'nmajordone:5'.

                         Example 2 : For both the following cases, there will be a printout in the logs
                         "Running Major Cycle 1" and the return value will include "nmajordone: 1",
                         however there is a difference in the purpose of the major cycle and the
                         number of minor cycles executed:
                             Case 1; nmajor=0, calcres=True:  The major cycle done is for the creation
                                         of the residual, and no minor cycles are executed.
                             Case 2; nmajor=1, calcres=False: The major cycle is done as part of the
                                         major/minor cycle loop, and 1 minor cycle will be executed.
    usemask              Type of mask(s) to be used for deconvolution

                          user: (default) mask image(s) or user specified region file(s) or string CRTF expression(s)
                            subparameters: mask, pbmask
                          pb: primary beam mask
                            subparameter: pbmask

                              Example: usemask="pb", pbmask=0.2
                                                Construct a mask at the 0.2 pb gain level.
                                                (Currently, this option will work only with
                                                gridders that produce .pb (i.e. mosaic and awproject)
                                                or if an externally produced .pb image exists on disk)

                          auto-multithresh : auto-masking by multiple thresholds for deconvolution
                             subparameters : sidelobethreshold, noisethreshold, lownoisethreshold, negativethrehsold,  smoothfactor,
                                             minbeamfrac, cutthreshold, pbmask, growiterations, dogrowprune, minpercentchange, verbose
                             Additional top level parameter relevant to auto-multithresh: fastnoise

                             if pbmask is >0.0, the region outside the specified pb gain level is excluded from
                             image statistics in determination of the threshold.




                          Note: By default the intermediate mask generated by automask at each deconvolution cycle
                                is over-written in the next cycle but one can save them by setting
                                the environment variable, SAVE_ALL_AUTOMASKS="true".
                                (e.g. in the CASA prompt, os.environ['SAVE_ALL_AUTOMASKS']="true" )
                                The saved CASA mask image name will be imagename.mask.autothresh#, where
                                # is the iteration cycle number.
    mask                 Mask (a list of image name(s) or region file(s) or region string(s)


                                            The name of a CASA image or region file or region string that specifies
                                            a 1/0 mask to be used for deconvolution. Only locations with value 1 will
                                            be considered for the centers of flux components in the minor cycle.
                                            If regions specified fall completely outside of the image, tclean will throw an error.

                                            Manual mask options/examples :

                                            mask='xxx.mask'  : Use this CASA image named xxx.mask and containing
                                                                            ones and zeros as the mask.
                                                                            If the mask is only different in spatial coordinates from what is being made
                                                                            it will be resampled to the target coordinate system before being used.
                                                                            The mask has to have the same shape in velocity and Stokes planes
                                                                            as the output image. Exceptions are single velocity and/or single
                                                                            Stokes plane masks. They will be expanded to cover all velocity and/or
                                                                            Stokes planes of the output cube.

                                                                            [ Note : If an error occurs during image resampling or
                                                                                        if the expected mask does not appear, please try
                                                                                        using tasks 'imregrid' or 'makemask' to resample
                                                                                        the mask image onto a CASA image with the target
                                                                                        shape and coordinates and supply it via the 'mask'
                                                                                        parameter. ]


                                            mask='xxx.crtf' : A text file with region strings and the following on the first line
                                                                       ( #CRTFv0 CASA Region Text Format version 0 )
                                                                       This is the format of a file created via the viewer's region
                                                                       tool when saved in CASA region file format.

                                            mask='circle[[40pix,40pix],10pix]'  : A CASA region string.

                                            mask=['xxx.mask','xxx.crtf', 'circle[[40pix,40pix],10pix]']  : a list of masks





                                            Note : Mask images for deconvolution must contain 1 or 0 in each pixel.
                                                       Such a mask is different from an internal T/F mask that can be
                                                       held within each CASA image. These two types of masks are not
                                                       automatically interchangeable, so please use the makemask task
                                                       to copy between them if you need to construct a 1/0 based mask
                                                       from a T/F one.

                                            Note : Work is in progress to generate more flexible masking options and
                                                       enable more controls.
    pbmask               Sub-parameter for usemask: primary beam mask

                         Examples : pbmask=0.0 (default, no pb mask)
                                    pbmask=0.2 (construct a mask at the 0.2 pb gain level)
    sidelobethreshold    Sub-parameter for "auto-multithresh":  mask threshold based on sidelobe levels:  sidelobethreshold \* max_sidelobe_level \* peak residual
    noisethreshold       Sub-parameter for "auto-multithresh":  mask threshold based on the noise level: noisethreshold \* rms + location (=median)

                         The rms is calculated from MAD with rms = 1.4826\*MAD.
    lownoisethreshold    Sub-parameter for "auto-multithresh":  mask threshold to grow previously masked regions via binary dilation:   lownoisethreshold \* rms in residual image + location (=median)

                         The rms is calculated from MAD with rms = 1.4826\*MAD.
    negativethreshold    Sub-parameter for "auto-multithresh": mask threshold  for negative features: -1.0* negativethreshold \* rms + location(=median)

                         The rms is calculated from MAD with rms = 1.4826\*MAD.
    smoothfactor         Sub-parameter for "auto-multithresh":  smoothing factor in a unit of the beam
    minbeamfrac          Sub-parameter for "auto-multithresh":  minimum beam fraction in size to prune masks smaller than mimbeamfrac \* beam
                         <=0.0 : No pruning
    cutthreshold         Sub-parameter for "auto-multithresh": threshold to cut the smoothed mask to create a final mask: cutthreshold \* peak of the smoothed mask
    growiterations       Sub-parameter for "auto-multithresh": Maximum number of iterations to perform using binary dilation for growing the mask
    dogrowprune          Experimental sub-parameter for "auto-multithresh": Do pruning on the grow mask
    minpercentchange     If the change in the mask size in a particular channel is less than minpercentchange, stop masking that channel in subsequent cycles. This check is only applied when noise based threshold is used and when the previous clean major cycle had a cyclethreshold value equal to the clean threshold. Values equal to -1.0 (or any value less than 0.0) will turn off this check (the default). Automask will still stop masking if the current channel mask is an empty mask and the noise threshold was used to determine the mask.
    verbose              he summary of automasking at the end of each automasking process
                         is printed in the logger.  Following information per channel will be listed in the summary.

                         chan: channel number
                         masking?: F - stop updating automask for the subsequent iteration cycles
                         RMS: robust rms noise
                         peak: peak in residual image
                         thresh_type: type of threshold used (noise or sidelobe)
                         thresh_value: the value of threshold used
                         N_reg: number of the automask regions
                         N_pruned: number of the automask regions removed by pruning
                         N_grow: number of the grow mask regions
                         N_grow_pruned: number of the grow mask regions removed by pruning
                         N_neg_pix: number of pixels for negative mask regions

                         Note that for a large cube, extra logging may slow down the process.
    fastnoise            Only relevant when automask (user='multi-autothresh') and/or n-sigma stopping threshold (nsigma>0.0) are/is used. If it is set to True,  a simpler but faster noise calucation is used.
                                                In this case, the threshold values are determined based on classic statistics (using all
                                                unmasked pixels for the calculations).

                                                If it is set to False,  the new noise calculation
                                                method is used based on pre-existing mask.

                                                Case 1: no exiting mask
                                                Calculate image statistics using Chauvenet algorithm

                                                Case 2: there is an existing mask
                                                Calculate image statistics by classical method on the region
                                                outside the mask and inside the primary beam mask.

                                                In all cases above RMS noise is calculated from MAD.
    restart              images (and start from an existing model image)
                         or automatically increment the image name and make a new image set.

                         True : Re-use existing images. If imagename.model exists the subsequent
                                   run will start from this model (i.e. predicting it using current gridder
                                   settings and starting from the residual image).  Care must be taken
                                   when combining this option with startmodel. Currently, only one or
                                   the other can be used.

                                   startmodel='', imagename.model exists :
                                             - Start from imagename.model
                                   startmodel='xxx', imagename.model does not exist :
                                             - Start from startmodel
                                   startmodel='xxx', imagename.model exists :
                                             - Exit with an error message requesting the user to pick
                                               only one model.  This situation can arise when doing one
                                               run with startmodel='xxx' to produce an output
                                               imagename.model that includes the content of startmodel,
                                               and wanting to restart a second run to continue deconvolution.
                                               Startmodel should be set to '' before continuing.

                                    If any change in the shape or coordinate system of the image is
                                    desired during the restart, please change the image name and
                                    use the startmodel (and mask) parameter(s) so that the old model
                                    (and mask) can be regridded to the new coordinate system before starting.

                          False : A convenience feature to increment imagename with '_1', '_2',
                                     etc as suffixes so that all runs of tclean are fresh starts (without
                                     having to change the imagename parameter or delete images).

                                     This mode will search the current directory for all existing
                                     imagename extensions, pick the maximum, and adds 1.
                                     For imagename='try' it will make try.psf, try_2.psf, try_3.psf, etc.

                                     This also works if you specify a directory name in the path :
                                     imagename='outdir/try'.  If './outdir' does not exist, it will create it.
                                     Then it will search for existing filenames inside that directory.

                                     If outlier fields are specified, the incrementing happens for each
                                     of them (since each has its own 'imagename').  The counters are
                                     synchronized across imagefields, to make it easier to match up sets
                                     of output images.  It adds 1 to the 'max id' from all outlier names
                                     on disk.  So, if you do two runs with only the main field
                                    (imagename='try'), and in the third run you add an outlier with
                                    imagename='outtry', you will get the following image names
                                    for the third run :  'try_3' and 'outtry_3' even though
                                    'outry' and 'outtry_2' have not been used.
    savemodel            Options to save model visibilities (none, virtual, modelcolumn)

                         Often, model visibilities must be created and saved in the MS
                         to be later used for self-calibration (or to just plot and view them).

                            none : Do not save any model visibilities in the MS. The MS is opened
                                       in readonly mode.

                                       Model visibilities can be predicted in a separate step by
                                       restarting tclean with niter=0,savemodel=virtual or modelcolumn
                                       and not changing any image names so that it finds the .model on
                                       disk (or by changing imagename and setting startmodel to the
                                       original imagename).

                            virtual : In the last major cycle, save the image model and state of the
                                         gridder used during imaging within the SOURCE subtable of the
                                         MS. Images required for de-gridding will also be stored internally.
                                         All future references to model visibilities will activate the
                                         (de)gridder to compute them on-the-fly.  This mode is useful
                                         when the dataset is large enough that an additional model data
                                         column on disk may be too much extra disk I/O, when the
                                         gridder is simple enough that on-the-fly recomputing of the
                                         model visibilities is quicker than disk I/O.
                                         For e.g. that gridder='awproject' does not support virtual model.

                            modelcolumn : In the last major cycle, save predicted model visibilities
                                        in the MODEL_DATA column of the MS. This mode is useful when
                                        the de-gridding cost to produce the model visibilities is higher
                                        than the I/O required to read the model visibilities from disk.
                                        This mode is currently required for gridder='awproject'.
                                        This mode is also required for the ability to later pull out
                                        model visibilities from the MS into a python array for custom
                                        processing.

                          Note 1 : The imagename.model  image on disk will always be constructed
                                        if the minor cycle runs. This savemodel parameter applies only to
                                        model visibilities created by de-gridding the model image.

                          Note 2 :  It is possible for an MS to have both a virtual model
                                        as well as a model_data column, but under normal operation,
                                        the last used mode will get triggered.  Use the delmod task to
                                        clear out existing models from an MS if confusion arises.
                         Note 3:    when parallel=True, use savemodel='none'; Other options are not yet ready
                                    for use in parallel. If model visibilities need to be saved (virtual or modelcolumn):
                                    please run tclean in serial mode with niter=0; after the parallel run
    calcres              Calculate initial residual image

                         This parameter controls what the first major cycle does.

                         calcres=False with niter greater than 0 will assume that
                         a .residual image already exists  and that the minor cycle can
                         begin without recomputing it.

                         calcres=False with niter=0 implies that only the PSF will be made
                         and no data will be gridded.

                         calcres=True requires that calcpsf=True or that the .psf and .sumwt
                         images already exist on disk (for normalization purposes).

                         Usage example : For large runs (or a pipeline scripts) it may be
                                                     useful to first run tclean with niter=0 to create
                                                     an initial .residual to look at and perhaps make
                                                     a custom mask for. Imaging can be resumed
                                                     without recomputing it.
    calcpsf              Calculate PSF

                         This parameter controls what the first major cycle does.

                         calcpsf=False will assume that a .psf image already exists
                         and that the minor cycle can begin without recomputing it.
    psfcutoff            When the .psf image is created a 2 dimensional Gaussian is fit to the main lobe of the PSF.
                         Which pixels in the PSF are fitted is determined by psfcutoff.
                         The default value of psfcutoff is 0.35 and can varied from 0.01 to 0.99.
                         Fitting algorithm:
                             - A region of 41 x 41 pixels around the peak of the PSF is compared against the psfcutoff.
                                 Sidelobes are ignored by radially searching from the PSF peak.
                             - Calculate the bottom left corner (blc) and top right corner (trc) from the points. Expand blc and trc with a number of pixels (5).
                             - Create a new sub-matrix from blc and trc.
                             - Interpolate matrix to a target number of points (3001) using CUBIC spline.
                             - All the non-sidelobe points, in the interpolated matrix, that are above the psfcutoff are used to fit a Gaussian.
                                 A Levenberg-Marquardt algorithm is used.
                             - If the fitting fails the algorithm is repeated with the psfcutoff decreased (psfcutoff=psfcutoff/1.5).
                                 A message in the log will apear if the fitting fails along with the new value of psfcutoff.
                                 This will be done up to 50 times if fitting fails.
                         This Gaussian beam is defined by a major axis, minor axis, and position angle.
                         During the restoration process, this Gaussian beam is used as the Clean beam.
                         Varying psfcutoff might be useful for producing a better fit for highly non-Gaussian PSFs, however, the resulting fits should be carefully checked.
                         This parameter should rarely be changed.

                         (This is not the support size for clark clean.)
    parallel             Run major cycles in parallel (this feature is experimental)

                          Parallel tclean will run only if casa has already been started using mpirun.
                          Please refer to HPC documentation for details on how to start this on your system.

                          Example :  mpirun -n 3 -xterm 0 `which casa`

                          Continuum Imaging :
                             -  Data are partitioned (in time) into NProc pieces
                             -  Gridding/iFT is done separately per partition
                             -  Images (and weights) are gathered and then normalized
                             - One non-parallel minor cycle is run
                             - Model image is scattered to all processes
                             - Major cycle is done in parallel per partition

                         Cube Imaging :
                             - Data and Image coordinates are partitioned (in freq) into NProc pieces
                             - Each partition is processed independently (major and minor cycles)
                             - All processes are synchronized at major cycle boundaries for convergence checks
                             - At the end, cubes from all partitions are concatenated along the spectral axis

                         Note 1 :  Iteration control for cube imaging is independent per partition.
                                       - There is currently no communication between them to synchronize
                                          information such as peak residual and cyclethreshold. Therefore,
                                          different chunks may trigger major cycles at different levels.
                                      (Proper synchronization of iteration control is work in progress.)
    [1;42mRETURNS[1;m                 void

    --------- examples -----------------------------------------------------------



    Please refer to the CASAdocs pages for the task tclean for examples.




    '''
    def __stop( self ):
        self.__result_future.set_result(self.__retrieve_result( ))

    def _abort_handler( self, err ):
        self._error_result = err
        self.__stop( )

    def __reset( self ):
        if self.__pipes_initialized:
            self._pipe = { 'control': None }
            self._clean = { 'converge': { 'state': { } }, 'last-success': None }
            reset_bokeh_output( )
            reset_resource_manager( )

        ###
        ### reset asyncio result future
        ###
        self.__result_future = None

        ###
        ### used by data pipe (websocket) initialization function
        ###
        self.__pipes_initialized = False

        ###
        ### error or exception result
        ###
        self._error_result = None

    '''
        _gen_port_fwd_cmd()

    Create an SSH port-forwarding command to create the tunnels necessary for remote connection.
    NOTE: This assumes that the same remote ports are also available locally - which may
        NOT always be true.
    '''
    def _gen_port_fwd_cmd(self):
        hostname = os.uname()[1]

        ###
        ### need to add extra cube ports here for multifield imaging
        ###
        ports = [ self._pipe['control'].address[1], self._clean['converge']['pipe'].address[1] ]

        for imid, imdetails in self._clean_targets.items( ):
            ports.append( imdetails['gui']['cube']._pipe['image'].address[1] )
            ports.append( imdetails['gui']['cube']._pipe['control'].address[1] )

        # Also forward http port if serving webpage
        if not self._is_notebook:
            ports.append(self._http_port)

        cmd = 'ssh'
        for port in ports:
            cmd += (' -L ' + str(port) + ':localhost:' + str(port))

        cmd += ' ' + str(hostname)
        return cmd

    def __init__( self, vis, imagename, selectdata=True, field='', spw='', timerange='', uvrange='', antenna='', scan='', observation='', intent='', datacolumn='corrected', imsize=[ int(100) ], cell=[  ], phasecenter='', stokes='I', projection='SIN', startmodel='', specmode='mfs', reffreq='', nchan=int(-1), start='', width='', outframe='LSRK', veltype='radio', restfreq=[  ], interpolation='linear', perchanweightdensity=True, gridder='standard', facets=int(1), psfphasecenter='', wprojplanes=int(1), vptable='', mosweight=True, aterm=True, psterm=False, wbawp=True, conjbeams=False, cfcache='', usepointing=False, computepastep=float(360.0), rotatepastep=float(360.0), pointingoffsetsigdev=[  ], pblimit=float(0.2), normtype='flatnoise', deconvolver='hogbom', scales=[  ], nterms=int(2), smallscalebias=float(0.0), fusedthreshold=float(0.0), largestscale=int(-1), restoration=True, restoringbeam=[  ], pbcor=False, outlierfile='', weighting='natural', robust=float(0.5), noise='1.0Jy', npixels=int(0), uvtaper=[ '' ], niter=int(0), gain=float(0.1), threshold=float(0.0), nsigma=float(0.0), cycleniter=int(-1), cyclefactor=float(1.0), minpsffraction=float(0.05), maxpsffraction=float(0.8), nmajor=int(-1), usemask='user', mask='', pbmask=float(0.0), sidelobethreshold=float(3.0), noisethreshold=float(5.0), lownoisethreshold=float(1.5), negativethreshold=float(0.0), smoothfactor=float(1.0), minbeamfrac=float(0.3), cutthreshold=float(0.01), growiterations=int(75), dogrowprune=True, minpercentchange=float(-1.0), verbose=False, fastnoise=True, restart=True, savemodel='none', calcres=True, calcpsf=True, psfcutoff=float(0.35), parallel=False ):

        ###
        ### With Bokeh 3.2.2, the spectrum and convergence plots extend beyond the edge of the
        ### browser window (requiring scrolling) if a width is not specified. It could be that
        ### this should be computed from the width of the tabbed control area at the right of
        ### the image display.
        ###
        self._conv_spect_plot_width = 450
        ###
        ### Create application context (which includes a temporary directory).
        ### This sets the title of the plot.
        ###
        self._app_state = AppContext( 'Interactive Clean' )

        ###
        ### Whether or not the Interactive Clean session is running remotely
        ###
        #self._is_remote = remote
        self._is_remote = False

        ###
        ### whether or not the session is being run from a jupyter notebook or script
        ###
        self._is_notebook = is_notebook()

        ##
        ## the http port for serving GUI in webpage if not running in script
        ##
        self._http_port = None

        ###
        ### the asyncio future that is used to transmit the result from interactive clean
        ###
        self.__result_future = None

        ###
        ### This is used to tell whether the websockets have been initialized, but also to
        ### indicate if __call__ is being called multiple times to allow for resetting Bokeh
        ###
        self.__pipes_initialized = False

        ###
        ### State required to manage iteration control
        ###
        self._control = { 'iteration': { } }

        ###
        ### color specs
        ###
        self._converge_color = { 'residual': 'black',
                                 'flux':     'forestgreen' }

        ###
        ### widgets shared across image tabs (multifield imaging)
        ###
        self._cube_palette = None
        self._image_bitmask_controls = None

        ###
        ### clean generator
        ###
        if _gclean is None:
            raise RuntimeError('casatasks gclean interface is not available')

        ###
        ### Set up dictionary of javascript code snippets
        ###
        self._initialize_javascript( )

        # Create folder for the generated html webpage - needs its own folder to not name conflict (must be 'index.html')
        webpage_dirname = imagename + '_webpage'
        ### Directory is created when an HTTP server is running
        ### (MAX)
#       if not os.path.isdir(webpage_dirname):
#          os.makedirs(webpage_dirname)
        self._webpage_path = os.path.abspath(webpage_dirname)

        self._pipe = { 'control': None }
        self._clean = { 'converge': { 'state': { } }, 'last-success': None }

        self._clean_targets = { imagename: { 'args': {'vis': vis, 'selectdata': selectdata, 'field': field, 'spw': spw, 'timerange': timerange, 'uvrange': uvrange, 'antenna': antenna, 'scan': scan, 'observation': observation, 'intent': intent, 'datacolumn': datacolumn, 'imagename': imagename, 'imsize': imsize, 'cell': cell, 'phasecenter': phasecenter, 'stokes': stokes, 'projection': projection, 'startmodel': startmodel, 'specmode': specmode, 'reffreq': reffreq, 'nchan': nchan, 'start': start, 'width': width, 'outframe': outframe, 'veltype': veltype, 'restfreq': restfreq, 'interpolation': interpolation, 'perchanweightdensity': perchanweightdensity, 'gridder': gridder, 'facets': facets, 'psfphasecenter': psfphasecenter, 'wprojplanes': wprojplanes, 'vptable': vptable, 'mosweight': mosweight, 'aterm': aterm, 'psterm': psterm, 'wbawp': wbawp, 'conjbeams': conjbeams, 'cfcache': cfcache, 'usepointing': usepointing, 'computepastep': computepastep, 'rotatepastep': rotatepastep, 'pointingoffsetsigdev': pointingoffsetsigdev, 'pblimit': pblimit, 'normtype': normtype, 'deconvolver': deconvolver, 'scales': scales, 'nterms': nterms, 'smallscalebias': smallscalebias, 'fusedthreshold': fusedthreshold, 'largestscale': largestscale, 'restoration': restoration, 'restoringbeam': restoringbeam, 'pbcor': pbcor, 'outlierfile': outlierfile, 'weighting': weighting, 'robust': robust, 'noise': noise, 'npixels': npixels, 'uvtaper': uvtaper, 'niter': niter, 'gain': gain, 'threshold': threshold, 'nsigma': nsigma, 'cycleniter': cycleniter, 'cyclefactor': cyclefactor, 'minpsffraction': minpsffraction, 'maxpsffraction': maxpsffraction, 'nmajor': nmajor, 'usemask': usemask, 'mask': mask, 'pbmask': pbmask, 'sidelobethreshold': sidelobethreshold, 'noisethreshold': noisethreshold, 'lownoisethreshold': lownoisethreshold, 'negativethreshold': negativethreshold, 'smoothfactor': smoothfactor, 'minbeamfrac': minbeamfrac, 'cutthreshold': cutthreshold, 'growiterations': growiterations, 'dogrowprune': dogrowprune, 'minpercentchange': minpercentchange, 'verbose': verbose, 'fastnoise': fastnoise, 'restart': restart, 'savemodel': savemodel, 'calcres': calcres, 'calcpsf': calcpsf, 'psfcutoff': psfcutoff, 'parallel': parallel} } }
        self._parameters = ImagerParameters( **{ k:v for k,v in self._clean_targets[imagename]['args'].items( )
                                                 if k in ImagerParameters.__init__.__code__.co_varnames[1:] } )
        self._clean_targets[imagename]['args']['outlierfile'] = ''		### >>HERE>> outlierfile TEMPORARILY handled in _interactiveclean.py
        ###
        ### For 6.6.5, outliers are not yet completely implemented so the
        ### 'outlierfile' parameter may not be present.
        ###
        if 'outlierfile' in locals( ) and outlierfile and exists(outlierfile):
            outliers, err = self._parameters.parseOutlierFile(outlierfile)
            if err: raise RuntimeError( f'''outlierfile error: {err}''' )
            for image in outliers:
                if 'impars' in image and 'imagename' in image['impars']:
                    name = image['impars']['imagename']
                    self._clean_targets[name] = { }
                    args = {'vis': vis, 'selectdata': selectdata, 'field': field, 'spw': spw, 'timerange': timerange, 'uvrange': uvrange, 'antenna': antenna, 'scan': scan, 'observation': observation, 'intent': intent, 'datacolumn': datacolumn, 'imagename': imagename, 'imsize': imsize, 'cell': cell, 'phasecenter': phasecenter, 'stokes': stokes, 'projection': projection, 'startmodel': startmodel, 'specmode': specmode, 'reffreq': reffreq, 'nchan': nchan, 'start': start, 'width': width, 'outframe': outframe, 'veltype': veltype, 'restfreq': restfreq, 'interpolation': interpolation, 'perchanweightdensity': perchanweightdensity, 'gridder': gridder, 'facets': facets, 'psfphasecenter': psfphasecenter, 'wprojplanes': wprojplanes, 'vptable': vptable, 'mosweight': mosweight, 'aterm': aterm, 'psterm': psterm, 'wbawp': wbawp, 'conjbeams': conjbeams, 'cfcache': cfcache, 'usepointing': usepointing, 'computepastep': computepastep, 'rotatepastep': rotatepastep, 'pointingoffsetsigdev': pointingoffsetsigdev, 'pblimit': pblimit, 'normtype': normtype, 'deconvolver': deconvolver, 'scales': scales, 'nterms': nterms, 'smallscalebias': smallscalebias, 'fusedthreshold': fusedthreshold, 'largestscale': largestscale, 'restoration': restoration, 'restoringbeam': restoringbeam, 'pbcor': pbcor, 'outlierfile': outlierfile, 'weighting': weighting, 'robust': robust, 'noise': noise, 'npixels': npixels, 'uvtaper': uvtaper, 'niter': niter, 'gain': gain, 'threshold': threshold, 'nsigma': nsigma, 'cycleniter': cycleniter, 'cyclefactor': cyclefactor, 'minpsffraction': minpsffraction, 'maxpsffraction': maxpsffraction, 'nmajor': nmajor, 'usemask': usemask, 'mask': mask, 'pbmask': pbmask, 'sidelobethreshold': sidelobethreshold, 'noisethreshold': noisethreshold, 'lownoisethreshold': lownoisethreshold, 'negativethreshold': negativethreshold, 'smoothfactor': smoothfactor, 'minbeamfrac': minbeamfrac, 'cutthreshold': cutthreshold, 'growiterations': growiterations, 'dogrowprune': dogrowprune, 'minpercentchange': minpercentchange, 'verbose': verbose, 'fastnoise': fastnoise, 'restart': restart, 'savemodel': savemodel, 'calcres': calcres, 'calcpsf': calcpsf, 'psfcutoff': psfcutoff, 'parallel': parallel}
                    args['outlierfile'] = ''					### >>HERE>> outlierfile TEMPORARILY handled in _interactiveclean.py
                    for _,arg_mods in image.items( ):
                        for k,v in arg_mods.items( ):
                            if k in args:
                                args[k] = v
                    self._clean_targets[name]['args'] = args

        ###
        ### create clean interface -- final version will have only one gclean object
        ###
        convergence_state={ 'convergence': {}, 'cyclethreshold': {} }
        self._clean['gclean'] = None
        self._clean['masks'] = { }
        self._clean['imid'] = [ ]
        self._clean['gclean_rest'] = [ ]
        for imid, imdetails in self._clean_targets.items( ):
            self._clean['imid'].append(imid)

            ###
            ### Residual path...
            ###
            if 'path' not in imdetails: imdetails['path'] = { }
            if self._clean['gclean'] is None:

                self._clean['gclean'] = _gclean( **imdetails['args'] )
                stopdesc, stopcode, majordone, majorleft, iterleft, imdetails['converge'] = next(self._clean['gclean'])

                if imdetails['converge']['major'] is None or imdetails['converge']['chan'] is None:
                    ###
                    ### gclean should provide argument checking (https://github.com/casangi/casagui/issues/33)
                    ### but currently gclean can be initialized with bad arguments and it is not known until
                    ### the initial calls to tclean/deconvolve
                    ###
                    raise RuntimeError('gclean failure "%s" not returned' % ('major' if imdetails['converge']['major'] is None else 'chan'))

                clean_cmds = self._clean['gclean'].cmds( )

                if imdetails['converge'] is None or len(imdetails['converge'].keys()) == 0:
                    raise RuntimeError(stopdesc)

                convergence_state['convergence'][imid] = imdetails['converge']['chan']
                convergence_state['cyclethreshold'][imid] = imdetails['converge']['major']['cyclethreshold']

                self._clean['masks'][imid] = self._clean['gclean'].mask( )

                if deconvolver == 'mtmfs':
                    imdetails['path']['residual'] = ("%s.residual.tt0" % imid) if self._clean['gclean'].has_next() else (self._clean['gclean'].finalize()['image'])
                else:
                    imdetails['path']['residual'] = ("%s.residual" % imid) if self._clean['gclean'].has_next() else (self._clean['gclean'].finalize()['image'])


            else:
                next_gclean =  _gclean( **imdetails['args'] )
                stopdesc, stopcode, majordone, majorleft, iterleft, imdetails['converge'] = next(next_gclean)
                clean_cmds = self._clean['gclean'].cmds( )

                if imdetails['converge'] is None or len(imdetails['converge'].keys()) == 0:
                    raise RuntimeError(stopdesc)

                convergence_state['convergence'][imid] = imdetails['converge']['chan']
                convergence_state['cyclethreshold'][imid] = imdetails['converge']['major']['cyclethreshold']

                self._clean['masks'][imid] = next_gclean.mask( )

                if deconvolver == 'mtmfs':
                    imdetails['path']['residual'] = ("%s.residual.tt0" % imid) if next_gclean.has_next() else (next_gclean.finalize()['image'])
                else:
                    imdetails['path']['residual'] = ("%s.residual" % imid) if next_gclean.has_next() else (next_gclean.finalize()['image'])

                self._clean['gclean_rest'].append(next_gclean)

        self._clean['last-success'] = dict( result='converged' if stopcode != 0 else 'update', stopcode=stopcode, cmd=clean_cmds,
                                            convergence=convergence_state['convergence'],
                                            iterdone=0, iterleft=iterleft,
                                            majordone=majordone, majorleft=majorleft, cyclethreshold=convergence_state['cyclethreshold'], stopdesc=stopdesc )

        for idx, (imid, imdetails) in enumerate(self._clean_targets.items( )):
            imdetails['gui'] = { }

            imdetails['gui'] = { 'params': { 'iteration': { }, 'automask': { } },
                                 'image': { },
                                 'image-adjust': { } }

            ###
            ### Only the first image should initialize the initial convergence state
            ###
            imdetails['gui']['cube'] = CubeMask( imdetails['path']['residual'], mask=self._clean['masks'][imid], abort=self._abort_handler,
                                                 init_script=CustomJS( args=dict( initial_convergence_state=convergence_state, name=imid ),
                                                                       code='''document._casa_convergence_data = initial_convergence_state''' )
                                                             if idx == 0 else None )

            ###
            ### Iteration Parameters
            ###
            imdetails['params'] = { }
            imdetails['params']['it'] = { }
            imdetails['params']['it']['nmajor'] = majorleft
            imdetails['params']['it']['niter'] = iterleft
            imdetails['params']['it']['cycleniter'] = cycleniter
            imdetails['params']['it']['threshold'] = threshold
            imdetails['params']['it']['cyclefactor'] = cyclefactor
            imdetails['params']['it']['gain'] = gain
            imdetails['params']['it']['nsigma'] = nsigma

            ###
            ### Auto Masking Parameters
            ###
            imdetails['params']['am'] = { }
            imdetails['params']['am']['usemask'] = usemask
            imdetails['params']['am']['noisethreshold'] = noisethreshold
            imdetails['params']['am']['sidelobethreshold'] = sidelobethreshold
            imdetails['params']['am']['lownoisethreshold'] = lownoisethreshold
            imdetails['params']['am']['minbeamfrac'] = minbeamfrac
            imdetails['params']['am']['negativethreshold'] = negativethreshold
            imdetails['params']['am']['dogrowprune'] = dogrowprune
            imdetails['params']['am']['fastnoise'] = fastnoise

    def _init_pipes( self ):
        if not self.__pipes_initialized:
            self.__pipes_initialized = True
            self._pipe['control'] = DataPipe( address=find_ws_address( ), abort=self._abort_handler )
            ###
            ### One pipe for updating the convergence plots.
            ###
            self._clean['converge'] = { 'state': None }
            self._clean['converge']['pipe'] = DataPipe( address=find_ws_address( ), abort=self._abort_handler )
            self._clean['converge']['id'] = str(uuid4( ))



            # Get port for serving HTTP server if running in script
            self._http_port = find_ws_address("")[1]
        for imid, imdetails in self._clean_targets.items( ):
            imdetails['gui']['cube']._init_pipes( )

    def _create_convergence_gui( self, imdetails, orient='horizontal', sizing_mode='stretch_width', **kw ):
        TOOLTIPS='''<div>
                        <div>
                            <span style="font-weight: bold;">@type</span>
                            <span>@values</span>
                        </div>
                        <div>
                            <span style="font-weight: bold; font-size: 10px">cycle threshold</span>
                            <span>@cyclethreshold</span>
                        </div>
                        <div>
                            <span style="font-weight: bold; font-size: 10px">stop</span>
                            <span>@stopDesc</span>
                        </div>
                    </div>'''

        hover = HoverTool( tooltips=TOOLTIPS )
        imdetails['gui']['convergence'] = figure( sizing_mode=sizing_mode, y_axis_location="right",
                                                  tools=[ hover ], toolbar_location=None, **kw )

        if orient == 'vertical':
            imdetails['gui']['convergence'].yaxis.axis_label='Iteration (cycle threshold dotted red)'
            imdetails['gui']['convergence'].xaxis.axis_label='Peak Residual'
            imdetails['gui']['convergence'].extra_x_ranges = { 'residual_range': DataRange1d( follow='end' ),
                                                               'flux_range': DataRange1d( follow='end' ) }

            imdetails['gui']['convergence'].step( 'values', 'iterations', source=imdetails['converge-data']['cyclethreshold'],
                                                  line_color='red', x_range_name='residual_range', line_dash='dotted', line_width=2 )
            imdetails['gui']['convergence'].line(   'values', 'iterations',   source=imdetails['converge-data']['residual'],
                                                    line_color=self._converge_color['residual'], x_range_name='residual_range' )
            imdetails['gui']['convergence'].circle( 'values', 'iterations',   source=imdetails['converge-data']['residual'],
                                                    color=self._converge_color['residual'], x_range_name='residual_range',size=10 )
            imdetails['gui']['convergence'].line(   'values', 'iterations', source=imdetails['converge-data']['flux'],
                                                    line_color=self._converge_color['flux'], x_range_name='flux_range' )
            imdetails['gui']['convergence'].circle( 'values', 'iterations', source=imdetails['converge-data']['flux'],
                                                    color=self._converge_color['flux'], x_range_name='flux_range', size=10 )

            imdetails['gui']['convergence'].add_layout( LinearAxis( x_range_name='flux_range', axis_label='Total Flux',
                                                        axis_line_color=self._converge_color['flux'],
                                                        major_label_text_color=self._converge_color['flux'],
                                                        axis_label_text_color=self._converge_color['flux'],
                                                        major_tick_line_color=self._converge_color['flux'],
                                                        minor_tick_line_color=self._converge_color['flux'] ), 'above')

        else:
            imdetails['gui']['convergence'].xaxis.axis_label='Iteration (cycle threshold dotted red)'
            imdetails['gui']['convergence'].yaxis.axis_label='Peak Residual'
            imdetails['gui']['convergence'].extra_y_ranges = { 'residual_range': DataRange1d( follow='end' ),
                                                               'flux_range': DataRange1d( follow='end' ) }

            imdetails['gui']['convergence'].step( 'iterations', 'values', source=imdetails['converge-data']['cyclethreshold'],
                                                  line_color='red', y_range_name='residual_range', line_dash='dotted', line_width=2 )
            imdetails['gui']['convergence'].line(   'iterations', 'values',   source=imdetails['converge-data']['residual'],
                                                    line_color=self._converge_color['residual'], y_range_name='residual_range' )
            imdetails['gui']['convergence'].circle( 'iterations', 'values',   source=imdetails['converge-data']['residual'],
                                                    color=self._converge_color['residual'], y_range_name='residual_range',size=10 )
            imdetails['gui']['convergence'].line(   'iterations', 'values', source=imdetails['converge-data']['flux'],
                                                    line_color=self._converge_color['flux'], y_range_name='flux_range' )
            imdetails['gui']['convergence'].circle( 'iterations', 'values', source=imdetails['converge-data']['flux'],
                                                    color=self._converge_color['flux'], y_range_name='flux_range', size=10 )

            imdetails['gui']['convergence'].add_layout( LinearAxis( y_range_name='flux_range', axis_label='Total Flux',
                                                        axis_line_color=self._converge_color['flux'],
                                                        major_label_text_color=self._converge_color['flux'],
                                                        axis_label_text_color=self._converge_color['flux'],
                                                        major_tick_line_color=self._converge_color['flux'],
                                                        minor_tick_line_color=self._converge_color['flux'] ), 'right')


    def _launch_gui( self ):
        '''create and show GUI
        '''
        ###
        ### Will contain the top level GUI
        ###
        self._fig = { }

        ###
        ### Python-side handler for events from the interactive clean control buttons
        ###
        async def clean_handler( msg, self=self ):
            if msg['action'] == 'next' or msg['action'] == 'finish':

                if 'mask' in msg['value']:
                    ###
                    ### >>HERE>> breadcrumbs must be specific to the field they are related to...
                    ###
                    if 'breadcrumbs' in msg['value'] and msg['value']['breadcrumbs'] is not None and msg['value']['breadcrumbs'] != self._last_mask_breadcrumbs:
                        self._last_mask_breadcrumbs = msg['value']['breadcrumbs']
                        mask_dir = "%s.mask" % self._imagename
                        shutil.rmtree(mask_dir)
                        new_mask = imdetails['gui']['cube'].jsmask_to_raw(msg['value']['mask'])
                        self._mask_history.append(new_mask)

                        msg['value']['mask'] = convert_masks(masks=new_mask, coord='pixel', cdesc=imdetails['gui']['cube'].coorddesc())

                    else:
                        ##### seemingly the mask path used to be spliced in?
                        #msg['value']['mask'] = self._mask_path
                        pass
                else:
                    ##### seemingly the mask path used to be spliced in?
                    #msg['value']['mask'] = self._mask_path
                    pass

                ###
                ### In the final implementation, there will only be one gclean object...
                ###
                convergence_state={ 'convergence': {}, 'cyclethreshold': {} }
                err,errmsg = self._clean['gclean'].update( dict( **msg['value']['iteration'],
                                                                 **msg['value']['automask'] ) )

                iteration_limit = int(msg['value']['iteration']['niter'])
                stopdesc, stopcode, majordone, majorleft, iterleft, self._convergence_data = await self._clean['gclean'].__anext__( )

                clean_cmds = self._clean['gclean'].cmds( )

                if len(self._convergence_data['chan']) == 0 or stopcode == -1:
                    ### stopcode == -1 indicates an error condition within gclean
                    return dict( result='error', stopcode=stopcode, cmd=clean_cmds,
                                 convergence=None, majordone=majordone,
                                 majorleft=majorleft, iterleft=iterleft, stopdesc=stopdesc )

                convergence_state['convergence'][self._clean['imid'][0]] = self._convergence_data['chan']
                convergence_state['cyclethreshold'][self._clean['imid'][0]] = self._convergence_data['major']['cyclethreshold']

                for g in zip(self._clean['imid'][1:],self._clean['gclean_rest']):
                    e,em = g[1].update( dict( **msg['value']['iteration'],
                                              **msg['value']['automask'] ) )
                    sdesc, scode, majord, majorl, iterl, cvg = await g[1].__anext__( )

                    clean_cmds = clean_cmds + g[1].cmds( )

                    if len(cvg['chan']) == 0 or scode == -1:
                        convergence_state['convergence'][g[0]] = { }
                        convergence_state['cyclethreshold'][g[0]] = { }
                    else:
                        convergence_state['convergence'][g[0]] = cvg['chan']
                        convergence_state['cyclethreshold'][g[0]] = cvg['major']['cyclethreshold']

                ### stopcode != 0 indicates that some stopping criteria has been reached
                ###               this will also catch errors as well as convergence
                ###               (so 'converged' isn't quite right...)
                self._clean['last-success'] = dict( result='converged' if stopcode != 0 else 'update', stopcode=stopcode, cmd=clean_cmds,
                                                   convergence=convergence_state['convergence'],
                                                   iterdone=iteration_limit - iterleft, iterleft=iterleft,
                                                   majordone=majordone, majorleft=majorleft, cyclethreshold=convergence_state['cyclethreshold'], stopdesc=stopdesc )
                return self._clean['last-success']

            elif msg['action'] == 'stop':
                self.__stop( )
                return dict( result='stopped', update=dict( ) )
            elif msg['action'] == 'status':
                return dict( result="ok", update=dict( ) )
            else:
                print( "got something else: '%s'" % msg['action'] )

        ###
        ### set up websockets which will be used for control and convergence updates
        ###
        self._init_pipes( )

        ###
        ### Setup id that will be used for messages from each button
        ###
        self._clean_ids = { }
        for btn in "continue", 'finish', 'stop':
            self._clean_ids[btn] = str(uuid4( ))
            #print("%s: %s" % ( btn, self._clean_ids[btn] ) )
            self._pipe['control'].register( self._clean_ids[btn], clean_handler )


        ###
        ### There is one set of tclean controls for all images/outlier/etc. because
        ### in the final version gclean will handle the iterations for all fields...
        ###
        cwidth = 64
        cheight = 40
        self._control['iteration'] = { }
        self._control['iteration']['continue'] = TipButton( max_width=cwidth, max_height=cheight, name='continue',
                                                        icon=svg_icon(icon_name="iclean-continue", size=18),
                                                        tooltip=Tooltip( content=HTML( '''Stop after <b>one major cycle</b> or when any stopping criteria is met.''' ), position='left') )
        self._control['iteration']['finish'] = TipButton( max_width=cwidth, max_height=cheight, name='finish',
                                                      icon=svg_icon(icon_name="iclean-finish", size=18),
                                                      tooltip=Tooltip( content=HTML( '''<b>Continue</b> until some stopping criteria is met.''' ), position='left') )
        self._control['iteration']['stop'] = TipButton( button_type="danger", max_width=cwidth, max_height=cheight, name='stop',
                                                    icon=svg_icon(icon_name="iclean-stop", size=18),
                                                    tooltip=Tooltip( content=HTML( '''<p>Clicking a <font color="red">red</font> stop button will cause this tab to close and control will return to Python.<p>Clicking an <font color="orange">orange</font> stop button will cause <tt>tclean</tt> to stop after the current major cycle.''' ), position='left' ) )

        ###
        ### The single SHARED help button will be supplied by the first CubeMask...
        ###
        help_button = None
        ###
        ### First status line will be reused...
        ###
        status_line = None

        ###
        ### Manage the widgets which are shared between tabs...
        ###
        icw = SharedWidgets( )
        for imid, imdetails in self._clean_targets.items( ):
            imdetails['image-channels'] = imdetails['gui']['cube'].shape( )[3]

            status_line = imdetails['gui']['stopcode'] = imdetails['gui']['cube'].status_text( "<p>initial residual image</p>" if imdetails['image-channels'] > 1 else "<p>initial <b>single-channel</b> residual image</p>", width=230, reuse=status_line )

            ###
            ### Retrieve convergence information
            ###
            def convergence_handler( msg, self=self, imid=imid ):
                if msg['action'] == 'retrieve':
                    return { 'result': self._clean['last-success'] }
                else:
                    return { 'result': None, 'error': 'unrecognized action' }

            self._clean['converge']['pipe'].register( self._clean['converge']['id'], convergence_handler )

            ###
            ### Data source that will be used for updating the convergence plot
            ###
            stokes = 0
            convergence = imdetails['converge']['chan'][0][stokes]
            imdetails['converge-data'] = { }
            imdetails['converge-data']['flux']     = ColumnDataSource( data=dict( values=convergence['modelFlux'], iterations=convergence['iterations'],
                                                               cyclethreshold=convergence['cycleThresh'],
                                                               stopDesc=list( map( ImagingDict.get_summaryminor_stopdesc, convergence['stopCode'] ) ),
                                                               type=['flux'] * len(convergence['iterations']) ) )
            imdetails['converge-data']['residual'] = ColumnDataSource( data=dict( values=convergence['peakRes'],   iterations=convergence['iterations'],
                                                               cyclethreshold=convergence['cycleThresh'],
                                                               stopDesc=list( map( ImagingDict.get_summaryminor_stopdesc, convergence['stopCode'] ) ),
                                                               type=['residual'] * len(convergence['iterations'])) )
            imdetails['converge-data']['cyclethreshold'] = ColumnDataSource( data=dict( values=convergence['cycleThresh'], iterations=convergence['iterations'] ) )


            ###
            ### help page for cube interactions
            ###
            if help_button is None:
                help_button = imdetails['gui']['cube'].help( rows=[ '<tr><td><i><b>red</b> stop button</i></td><td>clicking the stop button (when red) will close the dialog and control to python</td></tr>',
                                                                    '<tr><td><i><b>orange</b> stop button</i></td><td>clicking the stop button (when orange) will return control to the GUI after the currently executing tclean run completes</td></tr>' ], position='right' )


            self._create_convergence_gui( imdetails, orient='horizontal', sizing_mode='stretch_height', width=self._conv_spect_plot_width )

            imdetails['gui']['params']['iteration']['nmajor'] = icw.nmajor( title='nmajor', value="%s" % imdetails['params']['it']['nmajor'], width=90 )
            imdetails['gui']['params']['iteration']['niter'] = icw.niter( title='niter', value="%s" % imdetails['params']['it']['niter'], width=90 )
            imdetails['gui']['params']['iteration']['cycleniter'] = icw.cycleniter( title="cycleniter", value="%s" % imdetails['params']['it']['cycleniter'], width=90 )
            imdetails['gui']['params']['iteration']['threshold'] = icw.threshold( title="threshold", value="%s" % imdetails['params']['it']['threshold'], width=90 )
            imdetails['gui']['params']['iteration']['cyclefactor'] = icw.cyclefactor( value="%s" % imdetails['params']['it']['cyclefactor'], title="cyclefactor", width=90 )
            imdetails['gui']['params']['iteration']['gain'] = icw.gain( title='gain', value="%s" % imdetails['params']['it']['gain'], width=90 )
            imdetails['gui']['params']['iteration']['nsigma'] = icw.nsigma( title='nsigma', value="%s" % imdetails['params']['it']['nsigma'], width=90 )

            if imdetails['params']['am']['usemask'] == 'auto-multithresh':
                ###
                ### Currently automasking tab is only available when the user selects 'auto-multithresh'
                ###
                imdetails['gui']['params']['automask']['active'] = True
                imdetails['gui']['params']['automask']['noisethreshold'] = icw.noisethreshold( title='noisethreshold', value="%s" % imdetails['params']['am']['noisethreshold'], margin=( 5, 25, 5, 5 ), width=90 )
                imdetails['gui']['params']['automask']['sidelobethreshold'] = icw.sidelobethreshold( title='sidelobethreshold', value="%s" % imdetails['params']['am']['sidelobethreshold'], margin=( 5, 25, 5, 5 ), width=90 )
                imdetails['gui']['params']['automask']['lownoisethreshold'] = icw.lownoisethreshold( title='lownoisethreshold', value="%s" % imdetails['params']['am']['lownoisethreshold'], margin=( 5, 25, 5, 5 ), width=90 )
                imdetails['gui']['params']['automask']['minbeamfrac'] = icw.minbeamfrac( title='minbeamfrac', value="%s" % imdetails['params']['am']['minbeamfrac'], width=90 )
                imdetails['gui']['params']['automask']['negativethreshold'] = icw.negativethreshold( title='negativethreshold', value="%s" % imdetails['params']['am']['negativethreshold'], margin=( 5, 25, 5, 5 ), width=90 )
                imdetails['gui']['params']['automask']['dogrowprune'] = icw.dogrowprune( label='dogrowprune', active=imdetails['params']['am']['dogrowprune'], margin=( 15, 25, 5, 5 ) )
                imdetails['gui']['params']['automask']['fastnoise'] = icw.fastnoise( label='fastnoise', active=imdetails['params']['am']['fastnoise'], margin=( 15, 25, 5, 5 ) )


            imdetails['gui']['image']['src'] = imdetails['gui']['cube'].js_obj( )
            imdetails['gui']['image']['fig'] = imdetails['gui']['cube'].image( grid=False, height_policy='max', width_policy='max',
                                                                               channelcb=CustomJS( args=dict( img_state={ 'src': imdetails['gui']['image']['src'],
                                                                                                                          'flux': imdetails['converge-data']['flux'],
                                                                                                                          'residual': imdetails['converge-data']['residual'],
                                                                                                                          'cyclethreshold': imdetails['converge-data']['cyclethreshold'] },
                                                                                                              imid=imid,
                                                                                                              ctrl={ 'converge': self._clean['converge'] },
                                                                                                              stopdescmap=ImagingDict.get_summaryminor_stopdesc( ) ),
                                                                                                   code=self._js['update-converge'] +
                                                                                                        '''update_convergence_single( img_state, document._casa_convergence_data.chan[imid] )''' ) )

            ###
            ### spectrum plot must be disabled during iteration due to "tap to change channel" functionality
            ###
            if imdetails['image-channels'] > 1:
                imdetails['gui']['spectrum'] = imdetails['gui']['cube'].spectrum( orient='vertical', sizing_mode='stretch_height', width=self._conv_spect_plot_width )
                imdetails['gui']['slider'] = imdetails['gui']['cube'].slider( show_value=False, title='', margin=(14,5,5,5), sizing_mode="scale_width" )
                imdetails['gui']['goto'] = imdetails['gui']['cube'].goto( )
            else:
                imdetails['gui']['spectrum'] = None
                imdetails['gui']['slider'] = None
                imdetails['gui']['goto'] = None

            imdetails['gui']['channel-ctrl'] = imdetails['gui']['cube'].channel_ctrl( )

            imdetails['gui']['cursor-pixel-text'] = imdetails['gui']['cube'].pixel_tracking_text( margin=(-3, 5, 3, 30) )

            self._image_bitmask_controls = imdetails['gui']['cube'].bitmask_controls( reuse=self._image_bitmask_controls, button_type='light' )

            if imdetails['params']['am']['usemask'] == 'auto-multithresh':
                imdetails['gui']['auto-masking-panel'] = [ TabPanel( child=column( row( Tip( imdetails['gui']['params']['automask']['noisethreshold'],
                                                                                             tooltip=Tooltip( content=HTML( 'sets the signal-to-noise threshold above which significant emission is masked during the initial round of mask creation' ),
                                                                                                              position='bottom' ) ),
                                                                                        Tip( imdetails['gui']['params']['automask']['sidelobethreshold'],
                                                                                             tooltip=Tooltip( content=HTML( 'sets a threshold based on the sidelobe level above which significant emission is masked during the initial round of mask creation' ),
                                                                                                              position='bottom' ) ),
                                                                                        Tip( imdetails['gui']['params']['automask']['minbeamfrac'],
                                                                                             tooltip=Tooltip( content=HTML( 'sets the minimum size a region must be to be retained in the mask' ),
                                                                                                              position='bottom' ) ) ),
                                                                                   row( Tip( imdetails['gui']['params']['automask']['lownoisethreshold'],
                                                                                             tooltip=Tooltip( content=HTML( 'sets the threshold into which the initial mask (which is determined by either noisethreshold or sidelobethreshold) is expanded in order to include low signal-to-noise regions in the mask' ),
                                                                                                              position='bottom' ) ),
                                                                                        Tip( imdetails['gui']['params']['automask']['negativethreshold'],
                                                                                             tooltip=Tooltip( content=HTML( 'sets the signal-to-noise threshold for absorption features to be masked' ),
                                                                                                              position='bottom' ) ) ),
                                                                                   row( Tip( imdetails['gui']['params']['automask']['dogrowprune'],
                                                                                             tooltip=Tooltip( content=HTML( 'allows you to turn off the pruning of the low signal-to-noise mask, which speeds up masking for images and cubes with complex low signal-to-noise emission' ),
                                                                                                              position='bottom' ) ),
                                                                                        Tip( imdetails['gui']['params']['automask']['fastnoise'],
                                                                                             tooltip=Tooltip( content=HTML( 'When set to True, a simpler but faster noise calucation is used' ),
                                                                                                              position='bottom' ) ) ) ),
                                                                                   title='Automask' ) ]
            else:
                imdetails['gui']['auto-masking-panel'] = [ ]

        ###
        ### button to display the tclean log -- in the final implmentation, outliers and other multifield imaging should be handled by gclean
        ###
        self._log_button = TipButton( max_width=help_button.width, max_height=help_button.height, name='log',
                                      icon=svg_icon(icon_name="bp-application-sm", size=25),
                                      tooltip=Tooltip( content=HTML('''click here to see the <pre>tclean</pre> execution log'''), position="right" ),
                                      margin=(-1, 0, -10, 0), button_type='light',
                                      stylesheets=[ InlineStyleSheet( css='''.bk-btn { border: 0px solid #ccc;  padding: 0 var(--padding-vertical) var(--padding-horizontal); margin-top: 3px; }''' ) ] )

        self._control['iteration']['cb'] = CustomJS( args=dict( images_state={ k: { 'status': v['gui']['stopcode'],
                                                                                    'automask': v['gui']['params']['automask'],
                                                                                    'iteration': v['gui']['params']['iteration'],
                                                                                    'img': v['gui']['image']['fig'],
                                                                                    'spectrum': v['gui']['spectrum'],
                                                                                    'src': v['gui']['image']['src'],
                                                                                    'flux': v['converge-data']['flux'],
                                                                                    'cyclethreshold': v['converge-data']['cyclethreshold'],
                                                                                    'residual': v['converge-data']['residual'],
                                                                                    'navi': { 'slider': v['gui']['slider'],
                                                                                              'goto': v['gui']['goto'],
                                                                                              ## it doesn't seem like pixel tracking must be disabled
                                                                                              ##'tracking': v['gui']['cursor-pixel-text'],
                                                                                              'stokes': v['gui']['channel-ctrl'][1] } }
                                                                               for k,v in self._clean_targets.items( ) },
                                                                ctrl={ 'converge': self._clean['converge'] },
                                                                clean_ctrl=self._control['iteration'],
                                                                state=dict( mode='interactive', stopped=False, awaiting_stop=False, mask="" ),
                                                                ctrl_pipe=self._pipe['control'],
                                                                ids=self._clean_ids,
                                                                logbutton=self._log_button,
                                                                stopdescmap=ImagingDict.get_summaryminor_stopdesc( )
                                                              ),
                                                 code=self._js['update-converge'] + self._js['clean-refresh'] + self._js['clean-disable'] +
                                                      self._js['clean-enable'] + self._js['clean-status-update'] +
                                                      self._js['iter-gui-update'] + self._js['clean-wait'] +
                                                      '''function invalid_niter( s ) {
                                                             let v = parseInt( s )
                                                             if ( v > 0 ) return ''
                                                             if ( v == 0 ) return 'niter is zero'
                                                             if ( v < 0 ) return 'niter cannot be negative'
                                                             if ( isNaN(v) ) return 'niter must be an integer'
                                                         }
                                                         const itobj = Object.entries(images_state)[0][1].iteration
                                                         if ( ! state.stopped && cb_obj.origin.name == 'finish' ) {
                                                             let invalid = invalid_niter(itobj.niter.value)
                                                             if ( invalid ) update_status( invalid )
                                                             else {
                                                                 state.mode = 'continuous'
                                                                 update_status( 'Running multiple iterations' )
                                                                 disable( false )
                                                                 clean_ctrl.stop.button_type = "warning"
                                                                 const thevalue = get_update_dictionary( )
                                                                 ctrl_pipe.send( ids[cb_obj.origin.name],
                                                                                 { action: 'finish',
                                                                                   value: thevalue },
                                                                                 update_gui )
                                                             }
                                                         }
                                                         if ( ! state.stopped && state.mode === 'interactive' &&
                                                              cb_obj.origin.name === 'continue' ) {
                                                             let invalid = invalid_niter(itobj.niter.value)
                                                             if ( invalid ) update_status( invalid )
                                                             else {
                                                                 update_status( 'Running one set of deconvolution iterations' )
                                                                 disable( true )
                                                                 // only send message for button that was pressed
                                                                 // it's unclear whether 'this.origin.' or 'cb_obj.origin.' should be used
                                                                 // (or even if 'XXX.origin.' is public)...
                                                                 ctrl_pipe.send( ids[cb_obj.origin.name],
                                                                                 { action: 'next',
                                                                                   value: get_update_dictionary( ) },
                                                                                 update_gui )
                                                             }
                                                         }
                                                         if ( state.mode === 'interactive' && cb_obj.origin.name === 'stop' ) {
                                                             if ( confirm( "Are you sure you want to end this interactive clean session and close the GUI?" ) ) {
                                                                 disable( true )
                                                                 //ctrl_pipe.send( ids[cb_obj.origin.name],
                                                                 //                { action: 'stop',
                                                                 //                  value: { } },
                                                                 //                update_gui )
                                                                 document._casa_window_closed = true
                                                                 /*** this will close the tab >>>>---------+   ***/
                                                                 /***                                      |   ***/
                                                                 /***     vvvvv----------------------------+   ***/
                                                                 document._done( Object.entries(images_state).reduce((acc,[k,v]) => ({ ...acc, [k]: v.src.masks( ) }),{ } ) )
                                                             }
                                                         } else if ( state.mode === 'continuous' &&
                                                                     cb_obj.origin.name === 'stop' &&
                                                                     ! state.awaiting_stop ) {
                                                             disable( true )
                                                             state.awaiting_stop = true
                                                             ctrl_pipe.send( ids[cb_obj.origin.name],
                                                                             { action: 'status',
                                                                               value: { } },
                                                                             wait_for_tclean_stop )
                                                         }''' )


        self._control['iteration']['continue'].js_on_click( self._control['iteration']['cb'] )
        self._control['iteration']['finish'].js_on_click( self._control['iteration']['cb'] )
        self._control['iteration']['stop'].js_on_click( self._control['iteration']['cb'] )

        self._log_button.js_on_click( CustomJS( args=dict( logbutton=self._log_button ),
                                                code='''function format_log( elem ) {
                                                             return `<html>
                                                                     <head>
                                                                         <style type="text/css">
                                                                             body {
                                                                                 counter-reset: section;
                                                                             }
                                                                             p:before {
                                                                                 font-weight: bold;
                                                                                 counter-increment: section;
                                                                                 content: "" counter(section) ": ";
                                                                             }
                                                                         </style>
                                                                     </head>
                                                                     <body>
                                                                         <h1>Interactive Clean History</h1>
                                                                     ` + elem.map((x) => `<p>${x}</p>`).join('\\n') + '</body>\\n</html>'
                                                         }
                                                         let b = cb_obj.origin
                                                         if ( ! b._window || b._window.closed ) {
                                                             b._window = window.open("about:blank","Interactive Clean Log")
                                                             b._window.document.write(format_log(b._log))
                                                             b._window.document.close( )
                                                         }''' ) )

        ###
        ### Setup script that will be called when the user closes the
        ### browser tab that is running interactive clean
        ###
        initial_log = self._clean['gclean'].cmds( )
        for g in self._clean['gclean_rest']:
            initial_log = initial_log + g.cmds( )

        self._pipe['control'].init_script=CustomJS( args=dict( ctrl_pipe=self._pipe['control'],
                                                               ids=self._clean_ids,
                                                               logbutton=self._log_button,
                                                               log=initial_log,
                                                               initial_image=list(self._clean_targets.items( ))[0][0]
                                                             ),
                                                      code=self._js['initialize'] +
                                                           '''if ( ! logbutton._log ) {
                                                                  /*** store log list with log button for access in other callbacks ***/
                                                                  logbutton._log = log
                                                              }''' )

        tab_panels = list( map( self._create_image_panel, self._clean_targets.items( ) ) )

        for imid, imdetails in self._clean_targets.items( ):
            imdetails['gui']['cube'].connect( )

        image_tabs = Tabs( tabs=tab_panels, tabs_location='below', height_policy='max', width_policy='max' )

        self._fig['layout'] = column(
                                  row( help_button,
                                       self._log_button,
                                       Spacer( height=self._control['iteration']['stop'].height, sizing_mode="scale_width" ),
                                       Div( text="<div><b>status:</b></div>" ),
                                       status_line,
                                       self._control['iteration']['stop'], self._control['iteration']['continue'], self._control['iteration']['finish'], sizing_mode="scale_width" ),
                                  row( image_tabs, height_policy='max', width_policy='max' ),
                                  height_policy='max', width_policy='max' )

        ###
        ### Keep track of which image is currently active in document._casa_image_name (which is
        ### initialized in self._js['initialize']). Also, update the current control sub-tab
        ### when the field main-tab is changed. An attempt to manage this all within the
        ### control sub-tabs using a reference to self._image_control_tab_groups from
        ### each control sub-tab failed with:
        ###
        ###     bokeh.core.serialization.SerializationError: circular reference
        ###
        image_tabs.js_on_change( 'active', CustomJS( args=dict( names=[ t[0] for t in self._clean_targets.items( ) ],
                                                                itergroups=self._image_control_tab_groups ),
                                                     code='''if ( ! hasprop(document,'_casa_last_control_tab') ) {
                                                                 document._casa_last_control_tab = 0
                                                             }
                                                             document._casa_image_name = names[cb_obj.active]
                                                             itergroups[document._casa_image_name].active = document._casa_last_control_tab''' ) )

        # Change display type depending on runtime environment
        if self._is_notebook:
            output_notebook()
        else:
            ### Directory is created when an HTTP server is running
            ### (MAX)
###         output_file(self._imagename+'_webpage/index.html')
            pass

        show(self._fig['layout'])

    def _create_colormap_adjust( self, imdetails ):
        palette = imdetails['gui']['cube'].palette( reuse=self._cube_palette )
        return column( row( Div(text="<div><b>Colormap:</b></div>",margin=(5,2,5,25)), palette ),
                       imdetails['gui']['cube'].colormap_adjust( ), sizing_mode='stretch_both' )


    def _create_control_image_tab( self, imid, imdetails ):
        result = Tabs( tabs=[ TabPanel(child=column( row( Tip( imdetails['gui']['params']['iteration']['nmajor'],
                                                             tooltip=Tooltip( content=HTML( 'maximum number of major cycles to run before stopping'),
                                                                              position='bottom' ) ),
                                                        Tip( imdetails['gui']['params']['iteration']['niter'],
                                                             tooltip=Tooltip( content=HTML( 'number of clean iterations to run' ),
                                                                              position='bottom' ) ),
                                                        Tip( imdetails['gui']['params']['iteration']['threshold'],
                                                             tooltip=Tooltip( content=HTML( 'stopping threshold' ),
                                                                              position='bottom' ) ) ),
                                                   row( Tip( imdetails['gui']['params']['iteration']['nsigma'],
                                                             tooltip=Tooltip( content=HTML( 'multiplicative factor for rms-based threshold stopping'),
                                                                              position='bottom' ) ),
                                                        Tip( imdetails['gui']['params']['iteration']['gain'],
                                                             tooltip=Tooltip( content=HTML( 'fraction of the source flux to subtract out of the residual image'),
                                                                              position='bottom' ) ) ),
                                                   row( Tip( imdetails['gui']['params']['iteration']['cycleniter'],
                                                             tooltip=Tooltip( content=HTML( 'maximum number of <b>minor-cycle</b> iterations' ),
                                                                              position='bottom' ) ),
                                                        Tip( imdetails['gui']['params']['iteration']['cyclefactor'],
                                                             tooltip=Tooltip( content=HTML( 'scaling on PSF sidelobe level to compute the minor-cycle stopping threshold' ),
                                                                              position='bottom_left' ) ), background="lightgray" ),
                                                   imdetails['gui']['convergence'], sizing_mode='stretch_height' ),
                                     title='Iteration' ) ] +
                          ( [ TabPanel( child=imdetails['gui']['spectrum'],
                                        title='Spectrum' ) ] if imdetails['image-channels'] > 1 else [ ] ) +
                          [ TabPanel( child=self._create_colormap_adjust(imdetails),
                                      title='Colormap' ),
                            TabPanel( child=imdetails['gui']['cube'].statistics( ),
                                      title='Statistics' ) ] + imdetails['gui']['auto-masking-panel'],
                     width=500, sizing_mode='stretch_height', tabs_location='below' )

        if not hasattr(self,'_image_control_tab_groups'):
            self._image_control_tab_groups = { }

        self._image_control_tab_groups[imid] = result
        result.js_on_change( 'active', CustomJS( args=dict( ),
                                                 code='''document._casa_last_control_tab = cb_obj.active''' ) )
        return result

    def _create_image_panel( self, imagetuple ):
        imid, imdetails = imagetuple



        return TabPanel( child=column( row( *imdetails['gui']['channel-ctrl'], imdetails['gui']['cube'].coord_ctrl( ),
                                            *self._image_bitmask_controls,
                                            #Spacer( height=5, height_policy="fixed", sizing_mode="scale_width" ),
                                            imdetails['gui']['cursor-pixel-text'],
                                            row( Spacer( sizing_mode='stretch_width' ),
                                                 imdetails['gui']['cube'].tapedeck( size='20px' ) if imdetails['image-channels'] > 1 else Div( ),
                                                 Spacer( height=5, width=350 ), width_policy='max' ),
                                            width_policy='max' ),
                                       row( imdetails['gui']['image']['fig'],
                                            column( row( imdetails['gui']['goto'],
                                                         imdetails['gui']['slider'],
                                                         width_policy='max' ) if imdetails['image-channels'] > 1 else Div( ),
                                                    self._create_control_image_tab(imid, imdetails), height_policy='max' ),
                                            height_policy='max', width_policy='max' ),
                                       height_policy='max', width_policy='max' ), title=imid )

    def __call__( self ):
        '''Display GUI and process events until the user stops the application.

        Example:
            Create ``iclean`` object and display::

                print( "Result: %s" %
                       iclean( vis='refim_point_withline.ms', imagename='test', imsize=512,
                               cell='12.0arcsec', specmode='cube',
                               interpolation='nearest', ... )( ) )
        '''

        self.setup()

        # If Interactive Clean is being run remotely, print helper info for port tunneling
        if self._is_remote:
            # Tunnel ports for Jupyter kernel connection
            print("\nImportant: Copy the following line and run in your local terminal to establish port forwarding.\
                You may need to change the last argument to align with your ssh config.\n")
            print(self._gen_port_fwd_cmd())

            # TODO: Include?
            # VSCode will auto-forward ports that appear in well-formatted addresses.
            # Printing this line will cause VSCode to autoforward the ports
            # print("Cmd: " + str(repr(self.auto_fwd_ports_vscode())))
            input("\nPress enter when port forwarding is setup...")

        async def _run_( ):
            async with self.serve( ) as s:
                await s

        if self._is_notebook:
            ic_task = asyncio.create_task(_run_())
        else:
            asyncio.run(_run_( ))
            return self.result( )

    def setup( self ):
        self.__reset( )
        self._init_pipes()

    @asynccontextmanager
    async def serve( self ):
        '''This function is intended for developers who would like to embed interactive
        clean as a part of a larger GUI. This embedded use of interactive clean is not
        currently supported and would require the addition of parameters to this function
        as well as changes to the interactive clean implementation. However, this function
        does expose the ``asyncio.Future`` that is used to signal completion of the
        interactive cleaning operation, and it provides the coroutines which must be
        managed by asyncio to make the interactive clean GUI responsive.

        Example:
            Create ``iclean`` object, process events and retrieve result::

                ic = iclean( vis='refim_point_withline.ms', imagename='test', imsize=512,
                             cell='12.0arcsec', specmode='cube', interpolation='nearest', ... )
                async def process_events( ):
                    async with ic.serve( ) as state:
                        await state[0]

                asyncio.run(process_events( ))
                print( "Result:", ic.result( ) )


        Returns
        -------
        (asyncio.Future, dictionary of coroutines)
        '''
        def start_http_server():
            import http.server
            import socketserver
            PORT = self._http_port
            DIRECTORY=self._webpage_path

            class Handler(http.server.SimpleHTTPRequestHandler):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, directory=DIRECTORY, **kwargs)

            with socketserver.TCPServer(("", PORT), Handler) as httpd:
                print("\nServing Interactive Clean webpage from local directory: ", DIRECTORY)
                print("Use Control-C to stop Interactive clean.\n")
                print("Copy and paste one of the below URLs into your browser (Chrome or Firefox) to view:")
                print("http://localhost:"+str(PORT))
                print("http://127.0.0.1:"+str(PORT))

                httpd.serve_forever()

        self._launch_gui( )

        async with CMC( *( [ ctx for img in self._clean_targets.keys( ) for ctx in
                             [
                                 self._clean_targets[img]['gui']['cube'].serve(self.__stop),
                             ]
                           ] + [ websockets.serve( self._pipe['control'].process_messages,
                                                   self._pipe['control'].address[0],
                                                   self._pipe['control'].address[1] ),
                                 websockets.serve( self._clean['converge']['pipe'].process_messages,
                                                   self._clean['converge']['pipe'].address[0],
                                                   self._clean['converge']['pipe'].address[1] ) ]
                          ) ):
            self.__result_future = asyncio.Future( )
            yield self.__result_future

    def __retrieve_result( self ):
        '''If InteractiveClean had a return value, it would be filled in as part of the
        GUI dialog between Python and JavaScript and this function would return it'''
        if isinstance(self._error_result,Exception):
            raise self._error_result
        elif self._error_result is not None:
            return self._error_result
        return { k: v['converge'] for k,v in self._clean_targets.items( ) }

    def result( self ):
        '''If InteractiveClean had a return value, it would be filled in as part of the
        GUI dialog between Python and JavaScript and this function would return it'''
        if self.__result_future is None:
            raise RuntimeError( 'no interactive clean result is available' )

        self._clean['gclean'].restore( )
        for g in self._clean['gclean_rest']:
            g.restore( )

        return self.__result_future.result( )

    def masks( self ):
        '''Retrieves the masks which were used with interactive clean.

        Returns
        -------
        The standard ``casagui`` cube region dictionary which contains two elements
        ``masks`` and ``polys``.

        The value of the ``masks`` element is a dictionary that is indexed by
        tuples of ``(stokes,chan)`` and the value of each element is a list
        whose elements describe the polygons drawn on the channel represented
        by ``(stokes,chan)``. Each polygon description in this list has a
        polygon index (``p``) and a x/y translation (``d``).

        The value of the ``polys`` element is a dictionary that is indexed by
        polygon indexes. The value of each polygon index is a dictionary containing
        ``type`` (whose value is either ``'rect'`` or ``'poly``) and ``geometry``
        (whose value is a dictionary containing ``'xs'`` and ``'ys'`` (which are
        the x and y coordinates that define the polygon).

        This can be converted to other formats with ``casagui.utils.convert_masks``.
        '''
        return copy.deepcopy(self._mask_history)    ## don't allow users to change history

    def history( self ):
        '''Retrieves the commands used during the interactive clean session.

        Returns
        -------
        list[str]  tclean calls made during the interactive clean session.
        '''
        return self._clean.cmds( True )

    def _initialize_javascript( self ):
        self._js = { ### initialize state
                     ### --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---
                     ### -- document is used storing state                                                        --
                     ### --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---
                     'initialize':      '''if ( ! document._casa_initialized ) {
                                               document._casa_image_name = initial_image
                                               document._casa_initialized = true
                                               document._casa_window_closed = false
                                               window.addEventListener( 'beforeunload',
                                                                        function (e) {
                                                                            // if the window is already closed this message is never
                                                                            // delivered (unless interactive clean is called again then
                                                                            // the event shows up in the newly created control pipe
                                                                            if ( document._casa_window_closed == false ) {
                                                                                ctrl_pipe.send( ids['stop'],
                                                                                                { action: 'stop', value: { } },
                                                                                                  undefined ) } } )
                                           }''',

                     ### --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---
                     ### -- flux_src._convergence_data is used to store the complete                              --
                     ### --                                                                                       --
                     ### -- The "Insert here ..." code seems to be called when when the stokes plane is changed   --
                     ### -- but there have been no tclean iterations yet...                                       --
                     ### --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---
                     'update-converge': '''function update_convergence_single( target, data ) {
                                               const pos = target.src.cur_chan
                                               const imdata = data.get(pos[1]).get(pos[0])
                                               //  chan----------------^^^^^^      ^^^^^^----stokes
                                               const iterations = imdata.iterations
                                               const peakRes = imdata.peakRes
                                               const cyclethreshold = imdata.cycleThresh
                                               const modelFlux = imdata.modelFlux
                                               const stopCode = imdata.stopCode
                                               const stopDesc = imdata.stopCode.map( code => stopdescmap.has(code) ? stopdescmap.get(code): "" )
                                               target.residual.data = { iterations, cyclethreshold, stopDesc, values: peakRes, type: Array(iterations.length).fill('residual') }
                                               target.flux.data = { iterations, cyclethreshold, stopDesc, values: modelFlux, type: Array(iterations.length).fill('flux') }
                                               target.cyclethreshold.data = { iterations, values: cyclethreshold }
                                           }

                                           function update_convergence( recurse=false ) {
                                               let convdata
                                               if ( hasprop(document,'_casa_convergence_data') ) {
                                                   convdata = document._casa_convergence_data
                                               } else {
                                                   if ( ! recurse ) {
                                                       ctrl.converge.pipe.send( ctrl.converge.id, { action: 'retrieve' },
                                                                                (msg) => { if ( hasprop( msg.result, 'convergence' ) ) {
                                                                                               document._casa_convergence_data = { chan: msg.result.convergence,
                                                                                                                                   cyclethreshold: msg.result.cyclethreshold }
                                                                                               update_convergence(true)
                                                                                           } } )
                                                   } else { console.log( 'INTERNAL ERROR: fetching convergence data failed' ) }
                                                   return
                                               }

                                               Object.entries(images_state).map(
                                                   ([k,v],i) => { update_convergence_single(v,convdata.chan[k]) } )
                                           }''',

                     'clean-refresh':   '''function refresh( clean_msg ) {
                                               const itobj = Object.entries(images_state)[0][1].iteration
                                               let stokes = 0    // later we will receive the polarity
                                                                 // from some widget mechanism...
                                               //img_src.refresh( msg => { if ( 'stats' in msg ) { //  -- this should happen within CubeMask
                                               //                              stat_src.data = msg.stats
                                               //                          }
                                               //                        } )
                                               if ( clean_msg !== undefined ) {
                                                   if ( 'iterleft' in clean_msg ) {
                                                       itobj.niter.value = '' + clean_msg['iterleft']
                                                   } else if ( clean_msg !== undefined && 'iterdone' in clean_msg ) {
                                                       const remaining = parseInt(itobj.niter.value) - parseInt(clean_msg['iterdone'])
                                                       itobj.niter.value = '' + (remaining < 0 ? 0 : remaining)
                                                   }

                                                   if ( 'majorleft' in clean_msg ) {
                                                       itobj.nmajor.value = '' + clean_msg['majorleft']
                                                   } else if ( 'majordone' in clean_msg ) {
                                                       const nm = parseInt(itobj.nmajor.value)
                                                       if ( nm != -1 ) {
                                                           const remaining = nm - parseInt(clean_msg['majordone'])
                                                           itobj.nmajor.value = '' + (remaining < 0 ? 0 : remaining)
                                                       } else itobj.nmajor.value = '' + nm          // nmajor == -1 implies do not consider nmajor in stop decision
                                                   }

                                                   if ( hasprop(clean_msg,'convergence') && clean_msg.convergence != null ) {
                                                       document._casa_convergence_data = { chan: clean_msg.convergence,
                                                                                           cyclethreshold: clean_msg.cyclethreshold }
                                                   }
                                               }
                                               // >>HERE>> still needed?
                                               // >>HERE>> img_src.refresh( (data) => { if ( 'stats' in data ) cube_obj.update_statistics( data.stats ) } )

                                               update_convergence( )
                                           }''',

                       ###
                       ### enabling/disabling tools in imdetails['gui']['image']['fig'].toolbar.tools does not seem to not work
                       ###     imdetails['gui']['image']['fig'].toolbar.tools.tool_name (e.g. "Box Select", "Lasso Select")
                       ###
                       ### By design, images_state[*].automask.*/images_state[*].iteration.* are singletons which only need
                       ### to be disabled once...
                       ###
                       'clean-disable': '''function disable( with_stop ) {
                                               const amobj = Object.entries(images_state)[0][1].automask
                                               Object.entries(amobj).map(
                                                   ([k,v],i) => { if ( hasprop(v,'disabled') ) v.disabled = true } )
                                               const itobj = Object.entries(images_state)[0][1].iteration
                                               Object.entries(itobj).map(
                                                   ([k,v],i) => { if ( hasprop(v,'disabled') ) v.disabled = true } )
                                               Object.entries(images_state).map(
                                                   ([k,v],i) => {
                                                       v.img.disabled = true
                                                       if ( v.spectrum ) v.spectrum.disabled = true
                                                       v.src.disable_masking( )
                                                       v.src.disable_pixel_update( )
                                                       Object.entries(v.navi).map(
                                                           ([k1,v1],i1) => { if ( hasprop(v1,'disabled') ) v1.disabled = true }
                                                       )
                                                   }
                                               )
                                               clean_ctrl.continue.disabled = true
                                               clean_ctrl.finish.disabled = true
                                               clean_ctrl.stop.disabled = with_stop
                                           }''',

                       'clean-enable':  '''function enable( only_stop ) {
                                               const amobj = Object.entries(images_state)[0][1].automask
                                               Object.entries(amobj).map(
                                                   ([k,v],i) => { if ( hasprop(v,'disabled') ) v.disabled = false } )
                                               const itobj = Object.entries(images_state)[0][1].iteration
                                               Object.entries(itobj).map(
                                                   ([k,v],i) => { if ( hasprop(v,'disabled') ) v.disabled = false } )
                                               Object.entries(images_state).map(
                                                   ([k,v],i) => {
                                                       v.img.disabled = false
                                                       if ( v.spectrum ) v.spectrum.disabled = false
                                                       v.src.enable_masking( )
                                                       v.src.enable_pixel_update( )
                                                       Object.entries(v.navi).map(
                                                           ([k1,v1],i) => { if ( hasprop(v1,'disabled') ) v1.disabled = false } )
                                                   } )

                                               clean_ctrl.stop.disabled = false
                                               if ( ! only_stop ) {
                                                   clean_ctrl.continue.disabled = false
                                                   clean_ctrl.finish.disabled = false
                                               }
                                           }''',


                       'clean-status-update': '''function update_status( status ) {
                                               const stopstr = [ 'Zero stop code',
                                                                 'Iteration limit hit',
                                                                 'Force stop',
                                                                 'No change in peak residual across two major cycles',
                                                                 'Peak residual increased by 3x from last major cycle',
                                                                 'Peak residual increased by 3x from the minimum',
                                                                 'Zero mask found',
                                                                 'No mask found',
                                                                 'N-sigma or other valid exit criterion',
                                                                 'Stopping criteria encountered',
                                                                 'Unrecognized stop code' ]
                                               if ( typeof status === 'number' ) {
                                                   images_state[document._casa_image_name]['status'].text =
                                                       '<p>' +
                                                       stopstr[ status < 0 || status >= stopstr.length ?
                                                                stopstr.length - 1 : status ] +
                                                       '</p>'
                                               } else {
                                                   images_state[document._casa_image_name]['status'].text = `<p>${status}</p>`
                                               }
                                           }''',

                       'iter-gui-update': '''function get_update_dictionary( ) {
                                                  //const amste = images_state[document._casa_image_name]['automask']
                                                  //const clste = images_state[document._casa_image_name]['iteration']
                                                  // Assumption is that there is ONE set of iteration and automask updates
                                                  // for ALL imaging fields...
                                                  const amobj = Object.entries(images_state)[0][1].automask
                                                  const automask = amobj.active ?
                                                                   Object.entries(amobj).reduce(
                                                                       (acc,[k1,v1]) => { if ( hasprop(v1,'value') ) acc[k1] = v1.value; return acc },
                                                                       { dogrowprune: amobj.dogrowprune.active,
                                                                         fastnoise: amobj.fastnoise.active,
                                                                         active: true }
                                                                   ) : { }
                                                  const itobj = Object.entries(images_state)[0][1].iteration
                                                  const iteration = Object.entries(itobj).reduce(
                                                                        (acc,[k1,v1]) => { if ( hasprop(v1,'value') ) acc[k1] = v1.value; return acc },
                                                                        { }
                                                                    )

                                                  const masks = Object.entries(images_state).reduce( (acc,[k,v]) => { acc[k] = v.src.masks( ); return acc }, { } )
                                                  const breadcrumbs = Object.entries(images_state).reduce( (acc,[k,v]) => { acc[k] = v.src.breadcrumbs( ); return acc }, { } )
                                                  return { iteration, automask, masks, breadcrumbs, current_image: document._casa_image_name }
                                           }
                                           function update_log( log_lines ) {
                                               let b = logbutton
                                               b._log = b._log.concat( log_lines )
                                               if ( b._window && ! b._window.closed ) {
                                                   for ( const line of log_lines ) {
                                                       const p = b._window.document.createElement('p')
                                                       p.appendChild( b._window.document.createTextNode(line) )
                                                       b._window.document.body.appendChild(p)
                                                   }
                                               }
                                           }
                                           function update_gui( msg ) {
                                               const itobj = Object.entries(images_state)[0][1].iteration
                                               if ( msg.result === 'error' ) {
                                                   // ************************************************************************************
                                                   // ******** error occurs and is signaled by _gclean, e.g. exception in gclean  ********
                                                   // ************************************************************************************
                                                   state.mode = 'interactive'
                                                   clean_ctrl.stop.button_type = "danger"
                                                   enable(false)
                                                   state.stopped = false
                                                   update_status( msg.stopdesc ? msg.stopdesc : 'An internal error has occurred' )
                                                   if ( 'cmd' in msg ) {
                                                       update_log( msg.cmd )
                                                   }
                                               } else if ( msg.result === 'no-action' ) {
                                                   update_status( msg.stopdesc ? msg.stopdesc : 'nothing done' )
                                                   enable( false )
                                                   if ( 'cmd' in msg ) {
                                                       update_log( msg.cmd )
                                                   }
                                               } else if ( msg.result == 'converged' ) {
                                                   state.mode = 'interactive'
                                                   clean_ctrl.stop.button_type = "danger"
                                                   enable(false)
                                                   state.stopped = false
                                                   update_status( msg.stopdesc ? msg.stopdesc : 'stopping criteria reached' )
                                                   if ( 'cmd' in msg ) {
                                                       update_log( msg.cmd )
                                                   }
                                                   refresh( msg )
                                               } else if ( msg.result === 'update' ) {
                                                   if ( 'cmd' in msg ) {
                                                       update_log( msg.cmd )
                                                   }
                                                   refresh( msg )
                                                   // stopcode == 1: iteration limit hit
                                                   // stopcode == 9: major cycle limit hit
                                                   // *******************************************************************************************
                                                   // ******** perhaps the user should not be locked into exiting after the limit is hit ********
                                                   // *******************************************************************************************
                                                   //state.stopped = state.stopped || (msg.stopcode > 1 && msg.stopcode < 9) || msg.stopcode == 0
                                                   state.stopped = false
                                                   if ( state.mode === 'interactive' && ! state.awaiting_stop ) {
                                                       clean_ctrl.stop.button_type = "danger"
                                                       update_status( msg.stopdesc ? msg.stopdesc : 'stopcode' in msg ? msg.stopcode : -1 )
                                                       if ( ! state.stopped ) {
                                                           enable( false )
                                                       } else {
                                                           disable( false )
                                                       }
                                                   } else if ( state.mode === 'continuous' && ! state.awaiting_stop ) {
                                                       if ( ! state.stopped && itobj.niter.value > 0 && (itobj.nmajor.value > 0 || itobj.nmajor.value == -1) ) {
                                                           // *******************************************************************************************
                                                           // ******** 'niter.value > 0 so continue with one more iteration                      ********
                                                           // ******** 'nmajor.value' == -1 implies do not consider nmajor in stop consideration ********
                                                           // *******************************************************************************************
                                                           ctrl_pipe.send( ids[cb_obj.origin.name],
                                                                           { action: 'finish',
                                                                             value: get_update_dictionary( ) },
                                                                           update_gui )
                                                       } else if ( ! state.stopped  ) {
                                                           // *******************************************************************************************
                                                           // ******** 'niter.value <= 0 so iteration should stop                                ********
                                                           // *******************************************************************************************
                                                           state.mode = 'interactive'
                                                           clean_ctrl.stop.button_type = "danger"
                                                           enable(false)
                                                           state.stopped = false
                                                           update_status( msg.stopdesc ? msg.stopdesc : 'stopping criteria reached' )
                                                       } else {
                                                           state.mode = 'interactive'
                                                           clean_ctrl.stop.button_type = "danger"
                                                           enable(false)
                                                           state.stopped = false
                                                           update_status( msg.stopdesc ? msg.stopdesc : 'stopcode' in msg ? msg.stopcode : -1 )
                                                       }
                                                   }
                                               } else if ( msg.result === 'error' ) {
                                                   img_src.drop_breadcrumb('E')
                                                   if ( 'cmd' in msg ) {
                                                       update_log( msg.cmd )
                                                   }
                                                   state.mode = 'interactive'
                                                   clean_ctrl.stop.button_type = "danger"
                                                   state.stopped = false
                                                   update_status( 'stopcode' in msg ? msg.stopcode : -1 )
                                                   enable( false )
                                               }
                                           }''',

                       'clean-wait':    '''function wait_for_tclean_stop( msg ) {
                                               state.mode = 'interactive'
                                               clean_ctrl.stop.button_type = "danger"
                                               enable( false )
                                               state.awaiting_stop = false
                                               update_status( 'user requested stop' )
                                           }''',
        }
