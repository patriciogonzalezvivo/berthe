#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from Surface import *
from Surface.convert import *

invert = False
threshold_value = 0.5
angle = 10
scale = 0.1
translate=[0.0, 40.0]
samples = 20
pattern_resolution = 200

# Depth
heightmap = Image('lucy_depth.png')
mask = heightmap.copy()
mask.threshold(0.1)

grayscale = Image( 'lucy_dof.png' )

axi = Surface()

contours = Path()
for threshold in range(samples):
    contours.add( ImageContourToPath(heightmap, 0.1+threshold*0.01) )

contours_pattern = contours.getScaled(scale).getPattern(width=heightmap.width*scale, height=heightmap.height*scale)
# contours_pattern.transform = [100.0, 150.0]  
axi.pattern( contours_pattern, translate=[0.0, 150.0]  )
axi.text( "ImageContourToPath > Pattern", [50.0, 250.0], scale=0.1 )

axi.pattern( GrayscaleToPattern(grayscale, threshold=0.5, invert=invert, pattern_resolution=200, pattern_angle=45, mask=mask), translate=[0.0, 15.0] )
axi.text( "GrayscaleToPattern", [50.0, 100.0], scale=0.1 )

axi.pattern( HeightmapToPattern(heightmap, camera_angle=angle, grayscale=grayscale, threshold=threshold_value, invert=invert, pattern_resolution=pattern_resolution, pattern_angle=45, mask=mask), translate=[100.0, 20.0] )
axi.text( "HeightmapToPattern", [150.0, 100.0], scale=0.1 )

contours_filtered_pattern = HeightmapToPattern(heightmap, camera_angle=angle, grayscale=grayscale, threshold=threshold_value, invert=invert, pattern=contours_pattern, mask=mask)
axi.pattern( contours_filtered_pattern, translate=[100.0, 150.0] )
axi.text( "ImageContourToPath > Pattern > HeightmapToPattern ", [150.0, 250.0], scale=0.1 )

axi.toSVG('image.svg')