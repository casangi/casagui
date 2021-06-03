# Axis Labeling Using The ``image`` Tool

<pre>
Date: Mon, 24 May 2021 12:06:52 -0400
From: dmehring <dmehring@nrao.edu>
To: Darrell Schiebel <drs@nrao.edu>
Subject: Re: image labels
</pre>

On 2021-05-23 09:46, Darrell Schiebel wrote:
> Hi Dave,
> 
> In a basic example, the getchunk function makes it easy to access 
> spectral
> planes from an image cube. I would like to generate an axis label (say
> J2000 RA/Dec) for each pixel along the X and Y axes (just two lists of
> strings). Do you know of a convenient way of doing this? I looked at 
> the
> image and coordsys docs and they were not forthcoming.
> 
> thanks very much,
> Darrell
<pre>
Hi Darrell
Something like this will get you the RA's for the bottom row of pixels 
(bear in mind that, in general, all pixels in a given column will have 
slightly different RA's from each other because of the projection of the 
spherical astronomical coordinate system onto the cartesian pixel grid).

ia.fromshape("", [20, 30, 40])
pix = np.zeros([len(ia.shape()), ia.shape()[0]]) # [dim of image, number 
of pixels along axis of interest]
pix[0, :] = range(ia.shape()[0])
csys = ia.coordsys()
world = csys.toworldmany(pix)['numeric']


In this case you want the RA values, so thats just world[0]. The values 
are in units given by the axes in the coordsys metadata.

arcmin in this case

csys.units()
Out[24]: ["'", "'", 'Hz']

If you want nicely formatted astronomer friendly strings, you'll have to 
use quanta

unit = csys.units()[0]
ra_arr = []
for ra in world[0]:
     ra_arr.append(qa.time(qa.quantity(ra, unit), 9))

print(ra_arr)

[['00:00:40.000'], ['00:00:36.000'], ['00:00:32.000'], ['00:00:28.000'], 
['00:00:24.000'], ['00:00:20.000'], ['00:00:16.000'], ['00:00:12.000'], 
['00:00:08.000'], ['00:00:04.000'], ['00:00:00.000'], ['23:59:56.000'], 
['23:59:52.000'], ['23:59:48.000'], ['23:59:44.000'], ['23:59:40.000'], 
['23:59:36.000'], ['23:59:32.000'], ['23:59:28.000'], ['23:59:24.000']]

You can do similar things for dec and freq by changing the principal 
axis used to 1 and 2, respectively, and manipulating the quantities a 
bit differently to get the desired output formats.
</pre>
