#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import math
import numpy as np

from .Bbox import Bbox
from .tools import pointInside, hex2fill

class Element(object):
    def __init__(self, **kwargs):
        self.head_width = kwargs.pop('head_width', 0.2)
        self.id = kwargs.pop('id', None)

        self.stroke_width = kwargs.pop('stroke_width', self.head_width)
        self.stroke_width = kwargs.pop('stroke-width', self.stroke_width)
        if isinstance(self.stroke_width, str):
            self.stroke_width = float(self.stroke_width)

        self.fill = kwargs.pop('fill', False)
        if isinstance(self.fill, str):
            if self.fill.lower() == "none":
                self.fill = False
            else:
                self.fill = hex2fill(self.fill)

        self.translate = kwargs.pop('translate', np.array([0, 0]) )
        self.rotate = kwargs.pop('rotate', 0.0)
        self.scale = kwargs.pop('scale', 1.0)
        self.parent = None
        self.color = kwargs.pop('color', None)
        
    @property
    def isTransformed(self):
        return self.translate[0] != 0.0 or self.translate[1] != 0.0 or self.scale != 1.0 or self.rotate != 0.0


    @property
    def bounds(self):
        return Bbox( points=self.getPoints() )


    @property
    def center(self):
        return bounds.center


    def inside( self, pos ):
        return pointInside( pos, self.getPoints() )

    
    def getPoints(self):
        print('getPoints(): Function not declare')
        return []


    def _toShapelyGeom(self):
        try:
            from shapely import geometry
        except ImportError:
            geometry = None

        if geometry is None:
            raise Exception('To convert an Element to a Shapely geometry requires shapely. Try: pip install shapely')

        return geometry.Polygon( self.getPoints() )


    def getBuffer(self, offset):
        from .Polyline import Polyline
        
        if offset <= 0:
            import copy
            return copy.copy(self)
            
        return Polyline( self.getPoints(), stroke_width=self.stroke_width, head_width=self.head_width ).getBuffer(offset)


    def getTransformed(self, func):
        raise Exception('Not implemented for', type(self))


    def getTranslated(self, dx, dy):
        def func(x, y):
            return (x + dx, y + dy)
        return self.getTransformed(func)


    def getScaled(self, sx, sy=None):
        if sy is None:
            sy = sx
        def func(x, y):
            return (x * sx, y * sy)
        return self.getTransformed(func)


    def getRotated(self, angle):
        c = math.cos(math.radians(angle))
        s = math.sin(math.radians(angle))
        def func(x, y):
            return (x * c - y * s, y * c + x * s)
        return self.getTransformed(func)


    def getStrokePath(self, **kwargs ):
        # raise Exception('getPath(): Function not declare. Going with a simple convertion of the getPoints() to a Path')
        from .Path import Path
        return Path([ self.getPoints() ], color=self.color) 


    def getFillPath(self, **kwargs ):
        from .Path import Path
        return Path([ self.getPoints() ], color=self.color)


    def getPath(self, **kwargs):
        # # raise Exception('getPath(): Function not declare. Going with a simple convertion of the getPoints() to a Path')
        # from .Path import Path
        if self.fill:
            return self.getFillPath(**kwargs)
        else:
            return self.getStrokePath(**kwargs)


    def getSVGElementString(self):
        return self.getPath().getSVGElementString()


