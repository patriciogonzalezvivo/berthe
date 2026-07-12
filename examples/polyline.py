#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from Surface import *

# Depth
heightmap = Image('lucy_depth.png')
axi = Surface()

contours = ImageContourToPath(heightmap, 0.1).getScaled(0.1)
contour = Polyline( contours.path[0] )

axi.polyline( contour )
axi.text( "Polyline", [50.0, 92.0], scale=0.1 )

contour_convexHull = contour.getConvexHull()
axi.polyline( contour_convexHull, translate=[200.0, 100.0])
axi.text( ".getConvexHull()", center=[250.0, 192.0], scale=0.1 )


contour_simpler = contour.getSimplify(0.5)
axi.polyline( contour_simpler, translate=[200.0, 200.0])
axi.text( ".getSimplify(0.5)", center=[250.0, 292.0], scale=0.1 )


contour_offset = contour.getOffset(5)
axi.polyline( contour_offset, translate=[0.0, 100.0])
axi.text( ".getOffset(5)", center=[50.0, 197.0], scale=0.1 )


contour_buffer = contour.getBuffer(5)
axi.polyline( contour_buffer, translate=[100.0, 100.0])
axi.text( ".getBuffer(5)", center=[150.0, 197.0], scale=0.1 )

polygon1 = Polygon(contour.getSimplify(0.25), translate=[-15.0, 200.0])
polygon2 = Polygon(contour.getSimplify(0.25), translate=[15.0, 200.0])
axi.add(polygon1)
axi.add(polygon2)
indices = polygon1.getIntersections(polygon2)
for index in indices:
    axi.circle( polygon1.getPointAtIndexInterpolated(index), 1)
axi.text( ".getPointAtIndexInterpolated(...)", [50.0, 292.0], scale=0.1 )

# contour.
contour.head_width = 0.5
contour.fill = True
contour.translate=[200.0, 0.0] 
axi.polyline( contour )
axi.text( "fill=True", [250.0, 92.0], scale=0.1 )
axi.text( "head_width=0.5", [250.0, 97.0], scale=0.1 )

# contour.
contour.head_width = 0.25
contour.fill = False
contour.stroke_width = 2.0
contour.translate=[100.0, 0.0] 
axi.add( contour )
axi.text( "stroke_width=2", [150.0, 92.0], scale=0.1 )
axi.text( "head_width=0.25", [150.0, 97.0], scale=0.1 )


axi.toSVG('polyline.svg')
# axi.toPNG('polyline.png', optimize=True, debug=True )