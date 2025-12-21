#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import numpy as np

from .Element import Element
from .tools import linesIntersection, perpendicular, transform, distance

class Line(Element):
    def __init__( self, start, end, **kwargs):
        Element.__init__(self, **kwargs);
        self._start = np.array(start)
        self._end = np.array(end)

        self.resolution = int(kwargs.pop('resolution', 2))


    @property
    def center(self):
        return  self.start + (self.end - self.start) * 0.5

    
    @property
    def start(self):
        start = self._start
        if self.isTransformed:
            center = self._start + (self._end - self._start) * 0.5
            start = transform(start, translate=self.translate, rotate=self.rotate, scale=self.scale, anchor=center)
        return start


    @property
    def end(self):
        end = self._end
        if self.isTransformed:
            center = self._start + (self._end - self._start) * 0.5
            end = transform(end, translate=self.translate, rotate=self.rotate, scale=self.scale, anchor=center)
        return end


    @property
    def length(self):
        return distance(self.start, self.end)


    def intersect(self, line):
        return linesIntersection(self.start, self.end, line.start, line.end )


    def _toShapelyGeom(self):
        return self._toShapelyLineString()


    def _toShapelyLineString(self):
        try:
            from shapely import geometry
        except ImportError:
            geometry = None

        if geometry is None:
            raise Exception('To convert a Polyline to a Shapely LineString requires shapely. Try: pip install shapely')

        return geometry.LineString([self.start, self.end])


    def getPointPct(self, t):
        if t <= 0.0:
            return self.start
        if t >= 1.0:
            return self.end

        return self.start + (self.end - self.start) * t


    def getPoints(self):
        self.resolution == max(self.resolution, 2)

        if self.resolution == 2:
            return [self.start, self.end]
        else:
            points = []

            step = (self.end - self.start) / float(self.resolution-1)

            for i in range(0, self.resolution ):
                points.append( self.start + step * float(i))

        return points


    def _toShapelyGeom(self):
        try:
            from shapely import geometry
        except ImportError:
            geometry = None

        if geometry is None:
            raise Exception('To convert a Line to a Shapely LineString requires shapely. Try: pip install shapely')

        return geometry.LineString( self.getPoints() )


    def getStrokePath(self, **kwargs):
        from .Path import Path
        
        path = []
        A = self.start
        B = self.end

        if self.stroke_width > self.head_width:
            passes = self.stroke_width / self.head_width
            perp = perpendicular(A, B)
            perp_step = perp * self.head_width
            for i in range(int(-passes/2), int(passes/2) ):

                path.append( Line(A + perp_step * i, B + perp_step * i, resolution=self.resolution, head_width=self.head_width ).getPoints() )
        else:
            path.append( self.getPoints() )

        return Path(path, color=self.color, **kwargs)

