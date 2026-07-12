#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import math
from Surface import *

WIDTH = 297.0
# HEIGHT = 420.0
# CENTER = (WIDTH*0.5, HEIGHT*0.5)
MARGIN = WIDTH*0.1

path_str = ""

cols = 20
col_width = (WIDTH-MARGIN * 2.0)/cols
col_height = 20
ang_step = 180.0/cols
scl_step = 1.0/cols

x = MARGIN
y = MARGIN

axi = Surface()

axi.text( "rect", [MARGIN, y-10], scale=0.1 )
for col in range(cols):
    if col == cols-1:
        axi.rect([x + col * col_width, y], [col_width*0.8, col_width*0.8], rotate=col*ang_step, stroke_width=col+0.2, fill=True)
    else:
        axi.rect([x + col * col_width, y], [col_width*0.8, col_width*0.8], rotate=col*ang_step, stroke_width=col+0.2)

    axi.rect([x + col * col_width, y + col_height], [col_width*0.8, col_width*0.8], rotate=col*ang_step, scale=scl_step+scl_step*col*2.0, fill=True)

y += col_height * 2.0

axi.text( "hex", [MARGIN, y-10], scale=0.1 )
for col in range(cols):
    if col == cols-1:
        axi.hex([x + col * col_width, y], col_width*0.3, rotate=col*ang_step, stroke_width=col+0.2, fill=True)
    else:
        axi.hex([x + col * col_width, y], col_width*0.3, rotate=col*ang_step, stroke_width=col+0.2)

    axi.hex([x + col * col_width, y + col_height], col_width*0.3, rotate=col*ang_step, scale=scl_step+scl_step*col*2.0, fill=True)

y += col_height * 2.0

axi.text( "circle", [MARGIN, y-10], scale=0.1 )
for col in range(cols):
    axi.circle([x + col * col_width, y], col_width*0.25, rotate=col*ang_step, scale=scl_step+scl_step*col*2.0, fill=True)

    if col == cols-1:
        axi.circle([x + col * col_width, y + col_height], col_width*0.25, rotate=col*ang_step, stroke_width=col+0.2, fill=True)
    else:
        axi.circle([x + col * col_width, y + col_height], col_width*0.25, rotate=col*ang_step, stroke_width=col+0.2)

    if col == cols-1:
        axi.circle([x + col * col_width, y + col_height * 2.0], col_width*0.25, open_angle=90, rotate=col*ang_step, stroke_width=col+0.2, fill=True)
    else:
        axi.circle([x + col * col_width, y + col_height * 2.0], col_width*0.25, open_angle=90, rotate=col*ang_step, stroke_width=col+0.2)

y += col_height * 2.0

axi.text( "line", [MARGIN, y+col_height-10], scale=0.1 )
for col in range(cols):
    axi.line([-col_width*0.5, 0.0], [col_width*0.5,0.0], translate=[x + col * col_width, y + col_height], rotate=col*ang_step, stroke_width=col*0.25+0.2)

y += col_height

axi.text( "polyline", [MARGIN, y+col_height-10], scale=0.1 )
poly = Polyline( [ [-col_width*0.5, 0.0], [col_width*0.5, 0.0], [0.0, col_width*0.5], [0.0, -col_width*0.5] ] )
for col in range(cols):
    poly.translate = [x + col * col_width, y + col_height]
    poly.rotate = col*ang_step
    axi.polyline( poly.getPoints(), stroke_width=col*0.25+0.2 )

y += col_height * 1.5

points = []
for t in range(int(MARGIN), int(WIDTH-MARGIN)):
    t = float(t)
    points.append( [t, math.sin(t * 0.1) * col_height*0.5] )

poly = axi.polyline(points, translate=[0.0, y + col_height])
axi.polyline( poly.getOffset(10.0), stroke_width=1.0 )

y += col_height * 2.

axi.text( "text", [MARGIN, y+col_height-10], scale=0.1 )
for col in range(cols):
    stroke = col*axi.head_width+axi.head_width
    axi.text( "Hi", [x + col * col_width, y + col_height], scale=0.2, rotate=col*ang_step, stroke_width=stroke)
    axi.text( "Hi", [x + col * col_width, y + col_height * 2.0], rotate=col*ang_step*0.5, scale=(scl_step+scl_step*col*2.0)*0.2 )


axi.toSVG('elements.svg')
# axi.toGCODE('elements.gcode')