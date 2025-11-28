#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from .tools import remap

class Bbox(object):
    def __init__( self, **kwargs ):
        self.min_x, self.min_y = float("inf"), float("inf")
        self.max_x, self.max_y = float("-inf"), float("-inf")

        if 'x' in kwargs:
            self.min_x = kwargs['x'] 
            if 'width' in kwargs:
                self.max_x = self.min_x + kwargs['width']
        else:
            if 'width' in kwargs:
                self.min_x = 0
                self.max_x = kwargs['width']

        if 'y' in kwargs:
            self.min_y = kwargs['y'] 
            if 'height' in kwargs:
                self.max_y = self.min_y + kwargs['height']
        else:
            if 'height' in kwargs:
                self.min_y = 0
                self.max_y = kwargs['height']

        if 'points' in kwargs:
            self.setFromPoints( kwargs['points'] )


    def setFromPoints(self, points):
        self.min_x, self.min_y = float("inf"), float("inf")
        self.max_x, self.max_y = float("-inf"), float("-inf")

        for x, y in points:            # Set min coords
            print (x, y)
            if x < self.min_x:
                self.min_x = x
            if y < self.min_y:
                self.min_y = y
            # Set max coords
            if x > self.max_x:
                self.max_x = x
            if y > self.max_y:
                self.max_y = y

        print(self.min_x, self.min_y, self.max_x, self.max_y)


    def join(self, other):
        if isinstance(other, Bbox):
            self.min_x = min( self.min_x, other.min_x)
            self.min_y = min( self.min_y, other.min_y)
            self.max_x = max( self.max_x, other.max_x)
            self.max_y = max( self.max_y, other.max_y)


    def __repr__(self):
        return "BoundingBox({}, {}, {}, {})".format(
            self.min_x, self.max_x, self.min_y, self.max_y)

    @property
    def x(self):
        return self.min_x


    @property
    def y(self):
        return self.min_y


    @property
    def width(self):
        return self.max_x - self.min_x


    @property
    def height(self):
        return self.max_y - self.min_y


    @property
    def center(self):
        return [ self.min_x + (self.max_x - self.min_x) * 0.5, 
                 self.min_y + (self.max_y - self.min_y) * 0.5 ]

    @property
    def limits(self):
        return (self.min_x, self.min_y, self.max_x, self.max_y)


    def inside( self, pos ):
        if (pos[0] > self.min_x) and (pos[0] < self.max_x):
            if (pos[1] > self.min_y) and (pos[1] < self.max_y):
                return True
        return False


    def normalize(self, pos):
        return [remap(float(pos[0]), float(self.min_x), float(self.max_x), 0.0, 1.0),
                remap(float(pos[1]), float(self.min_x), float(self.max_y), 0.0, 1.0) ]

    