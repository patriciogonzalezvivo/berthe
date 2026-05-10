#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import math
import numpy as np

from .Element import Element

class Rectangle(Element):
    def __init__( self, pos, size, **kwargs ):
        Element.__init__(self, **kwargs);

        # support both 'anchor' and 'align' (consistent with Text)
        self.anchor = kwargs.pop('anchor', kwargs.pop('align', 'center'))

        if isinstance(self.scale, (tuple, list)):
            sx, sy = self.scale[0], self.scale[1]
        else:
            sx = sy = self.scale

        hw = size[0] * 0.5 * sx
        hh = size[1] * 0.5 * sy

        if self.anchor == 'center':
            self._center = pos
        elif self.anchor == 'top_left':
            self._center = (pos[0] + hw, pos[1] + hh)
        elif self.anchor == 'top_right':
            self._center = (pos[0] - hw, pos[1] + hh)
        elif self.anchor == 'bottom_left':
            self._center = (pos[0] + hw, pos[1] - hh)
        elif self.anchor == 'bottom_right':
            self._center = (pos[0] - hw, pos[1] - hh)
        elif self.anchor == 'left':
            self._center = (pos[0] + hw, pos[1])
        elif self.anchor == 'right':
            self._center = (pos[0] - hw, pos[1])
        elif self.anchor == 'top':
            self._center = (pos[0], pos[1] + hh)
        elif self.anchor == 'bottom':
            self._center = (pos[0], pos[1] - hh)

        self._center = np.array(self._center)
        self.size = size
        # self.size[0] = float(kwargs.pop('width', size[0]))
        # self.size[1] = float(kwargs.pop('height', size[1]))


    def inside( self, pos ):
        if self.isTransformed:
            return Element.inside(self, pos, self.getPoints() )
        elif (pos[0] > self.center[0] - self.size[0] * 0.5) and (pos[0] < self.center[0] + self.size[0] * 0.5):
            if (pos[1] > self.center[1] - self.size[1] * 0.5) and (pos[1] < self.center[1] + self.size[1] * 0.5):
                return True

        return False


    @property
    def center(self):
        return self._center + self.translate


    @property
    def width(self):
        if isinstance(self.size, tuple) or isinstance(self.size, list):
            return self.size[0]
        else:
            return self.size

    @property
    def height(self):
        if isinstance(self.size, tuple) or isinstance(self.size, list):
            return self.size[1]
        else:
            return self.size


    @property
    def radius(self):
        rx = self.width * 0.5
        ry = self.height * 0.5

        rx = math.sqrt( rx * rx + ry * ry )
        ry = rx

        if isinstance(self.scale, tuple) or isinstance(self.scale, list):
            rx *= self.scale[0]
            ry *= self.scale[1]
        else:
            rx *= self.scale
            ry *= self.scale

        return [rx, ry]


    def getCoorners(self):
        cx, cy = self.center

        if isinstance(self.scale, (tuple, list)):
            hw = self.width * 0.5 * self.scale[0]
            hh = self.height * 0.5 * self.scale[1]
        else:
            hw = self.width * 0.5 * self.scale
            hh = self.height * 0.5 * self.scale

        if self.rotate != 0.0:
            c = math.cos(math.radians(self.rotate))
            s = math.sin(math.radians(self.rotate))
            def rot(x, y):
                return [cx + x * c - y * s, cy + x * s + y * c]
            return [rot(hw, hh), rot(hw, -hh), rot(-hw, -hh), rot(-hw, hh)]

        return [
            [cx + hw, cy + hh],
            [cx + hw, cy - hh],
            [cx - hw, cy - hh],
            [cx - hw, cy + hh],
        ]


    def getPoints(self):
        points = self.getCoorners()
        points.append(points[0])
        return points


    def getOffset(self, offset):
        return Rectangle( self.center, size=[self.width + offset, self.height + offset], stroke_width=self.stroke_width, head_width=self.head_width )


    def getBuffer(self, offset):
        if offset <= 0:
            import copy
            return copy.copy(self)

        return self.getOffset(offset)


    def getStrokePath(self, **kwargs):
        from .Path import Path
        
        corners = self.getCoorners()
        # Corner order from getCoorners: [TR, BR, BL, TL]
        signs = [[1, 1], [1, -1], [-1, -1], [-1, 1]]

        half_stroke = (self.stroke_width * self.head_width) * 0.5

        def make_ring(d):
            ring = [[px + sx * d, py + sy * d] for (px, py), (sx, sy) in zip(corners, signs)]
            ring.append(ring[0])
            return ring

        path = []
        if self.stroke_width > self.head_width or self.fill:
            d = half_stroke
            d_target = -half_stroke
            path.append(make_ring(d))
            while d > d_target:
                d = max(d - self.head_width, d_target)
                path.append(make_ring(d))
        else:
            path.append(self.getPoints())

        return Path(path)

    
    def getFillPath(self, **kwargs):
        from .Path import Path
        
        corners = self.getCoorners()
        signs = [[1, 1], [1, -1], [-1, -1], [-1, 1]]

        if isinstance(self.scale, (tuple, list)):
            min_dim = min(self.width * self.scale[0], self.height * self.scale[1]) * 0.5
        else:
            min_dim = min(self.width, self.height) * self.scale * 0.5

        half_stroke = (self.stroke_width * self.head_width) * 0.5

        def make_ring(d):
            ring = [[px + sx * d, py + sy * d] for (px, py), (sx, sy) in zip(corners, signs)]
            ring.append(ring[0])
            return ring

        path = []
        if self.stroke_width > self.head_width or self.fill:
            d = -half_stroke
            d_target = -min_dim
            path.append(make_ring(d))
            while d > d_target:
                d = max(d - self.head_width, d_target)
                path.append(make_ring(d))
        else:
            path.append(self.getPoints())

        return Path(path)


    # def getPathString(self):
        
    #     def path_gen(**kwargs):
    #         points = self.getPoints(**kwargs)
    #         return 'M' + 'L'.join('{0} {1}'.format(x,y) for x,y in points)

    #     path_str = ''
    #     if self.stroke_width > self.head_width or self.fill:

    #         if isinstance(self.size, tuple) or isinstance(self.size, list):
    #             rx = self.size[0] * 0.5
    #             ry = self.size[1] * 0.5
    #         else:
    #             rx = self.size * 0.5
    #             ry = self.size * 0.5

    #         if isinstance(self.scale, tuple) or isinstance(self.scale, list):
    #             rx *= self.scale[0]
    #             ry *= self.scale[1]
    #         else:
    #             rx *= self.scale
    #             ry *= self.scale

    #         w = rx + (self.stroke_width * self.head_width) * 0.5
    #         h = ry + (self.stroke_width * self.head_width) * 0.5

    #         w_target = rx - (self.stroke_width * self.head_width) * 0.5
    #         h_target = ry - (self.stroke_width * self.head_width) * 0.5

    #         if self.fill:
    #             w_target = 0
    #             h_target = 0

    #         while w > w_target or h > h_target:
    #             path_str += path_gen( size_offset=[w - rx, h - ry] )
    #             w = max(w - self.head_width, w_target)
    #             h = max(h - self.head_width, h_target)
    #     else:
    #         path_str += path_gen()
    #     return path_str