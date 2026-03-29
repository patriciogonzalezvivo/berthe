#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import numpy as np

from .Element import Element
from .Image import Image
from .tools import transform


class Pattern(Element):
    def __init__( self, parent=None, **kwargs ):
        Element.__init__(self, **kwargs)
        self.width = float(kwargs.pop('width', 100))
        self.height = float(kwargs.pop('height', 100))
        self.anchor = kwargs.pop('anchor', [0.5, 0.5])

        if parent is None:
            x = np.zeros(1)
            x.fill(np.nan)
            y = np.zeros(1)
            y.fill(np.nan)
            self.data = (x, y)
        
        elif isinstance(parent, Pattern):
            x, y = parent.data
            self.data = (x.copy(), y.copy())
            self.width = parent.width
            self.height = parent.height
            self.translate = kwargs.pop('translate', parent.translate)
            self.scale = kwargs.pop('scale', parent.scale) 
            self.rotate = kwargs.pop('rotate', parent.rotate)
            self.anchor = kwargs.pop('rotate', parent.anchor)

        elif isinstance(parent, Element):
            # Handle Path and other Element objects by creating empty pattern
            x = np.zeros(1)
            x.fill(np.nan)
            y = np.zeros(1)
            y.fill(np.nan)
            self.data = (x, y)

        else:
            x, y = parent
            self.data = (x.copy(), y.copy())

    def __add__(self, other):
        return self.add(other)


    def __iadd__(self, other):
        return self.add(other)
    

    def copy(self):
        return Pattern(self)    
    

    def add(self, other):
        if isinstance(other, Pattern):
            x1, y1 = self.data
            x2, y2 = other.data
            
            if other.width != self.width:
                x2 = x2 * other.width
                x2 = x2 / self.width

            if other.height != self.height:
                y2 = y2 * other.height
                y2 = y2 / self.height

            self.data = (np.concatenate([x1, x2]), np.concatenate([y1, y2]))
            return self

        else:
            x1, y1 = self.data
            x2, y2 = other
            self.data = (np.concatenate([x1, x2]), np.concatenate([y1, y2]))
            return self


    @property
    def center(self):
        return [self.width * self.anchor[0], self.height * self.anchor[1]]


    def turn(self, rotation, x_offset=0.5, y_offset=0.5):
        """Rotates the given pattern by a given angle.
        Args:
            rotation (float): the angle of rotation in degrees
            x_offset (float): the x component of the center of rotation (optional)
            y_offset (float): the y component of the center of rotation (optional)
        """
        x, y = self.data
        # Removed unnecessary .copy() - operations below create new arrays anyway
        angle = np.radians(rotation)
        cos_a, sin_a = np.cos(angle), np.sin(angle)
        x_centered = x - x_offset
        y_centered = y - y_offset
        x_rot = x_centered * cos_a + y_centered * sin_a
        y_rot = -x_centered * sin_a + y_centered * cos_a

        self.data = (x_rot + x_offset, y_rot + y_offset)


    def _map(self, surface):
        """Returns values on a surface for points on a pattern.
        Args:
            surface (surface): the surface to trace along
        Returns:
            an array of surface heights for each point in the
            pattern. Line separators (i.e. values that are ``nan`` in
            the pattern) will be ``nan`` in the output, so the output
            will have the same dimensions as the x/y axes in the
            input pattern.
        """
        x, y = self.data
        # surface_h, surface_w = surface.shape
        surface_w, surface_h = surface.shape

        # First, we convert the points along the pattern into integers within
        # the bounds of the surface's index. The clipping here will also convert
        # the nan values to 0.
        # Handle NaN values before casting to avoid RuntimeWarning
        x_safe = np.nan_to_num(x, nan=0.0)
        y_safe = np.nan_to_num(y, nan=0.0)
        surface_x = np.clip( np.int32(surface_w * x_safe - 1e-9), 0, surface_w - 1)
        surface_y = np.clip( np.int32(surface_h * y_safe - 1e-9), 0, surface_h - 1)

        # Grab z-values along the pattern path. Note that this will include values
        # for every point, even if it is nan or had to be clipped to within the
        # bounds of the surface, so we have to fix that next.
        try:
            surface_z = surface[surface_x, surface_y]
        except IndexError:
            print(surface_x, surface_y, surface_w, surface_h)

        # # Set z-values that are either out of bounds or nan in the pattern to nan
        # # in the output.
        # # Numpy wants to warn about the fact that there are nan values in the
        # # patterns, so we silence warnings about this.
        # with np.errstate(invalid='ignore'):
        #     surface_z[  (x < 0) | (x >= 1) |
        #                 (y < 0) | (y >= 1)] = np.nan
        
        return surface_z


    def project(self, surface, angle=0, offset=0,**kwargs):

        # Map the pattern to get the Zs
        if isinstance(surface, Image):
            if surface.type == "grayscale":
                z = self._map(surface.data.T)
            elif surface.type == "mask":
                return self.mask(surface)
        else:
            z = self._map(surface.T)

        # Extract the Xs and Ys from the pattern
        x, y = self.data

        if angle != 0:        
            # The projection is as simple as linearly blending the Z and Y
            # dimensions. The multiples are calculated from the given
            # angle with standard trig.
            z_coef = np.sin(np.radians( (angle) ))
            y_coef = np.cos(np.radians( (angle) ))

            self.data = (x, (y * y_coef + offset * 0.5) - z * z_coef)
        else:
            self.data = (x, (y - offset * 0.5) + (z * offset * 0.5) )

        return self


    def mask(self, element, width=None, height=None):
        x, y = self.data

        if width == None:
            width = self.width
        if height == None:
            height = self.height

        if isinstance(element, Element):
            N = x.shape[0]
            z = np.zeros(N)
            for i in range(N):
                if np.isnan(x[i]) or np.isnan(y[i]):
                    continue
                pos = [x[i] * width, y[i] * height]
                if not element.inside(pos):
                    z[i] = np.nan
            self.data = (x, y + z)

        elif isinstance(element, Image):
            if element.type == "mask":
                # mask self.data based on element.data
                # Use nan_to_num to avoid RuntimeWarning on NaN values during cast
                x_safe = np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)
                y_safe = np.nan_to_num(y, nan=0.0, posinf=0.0, neginf=0.0)
                # Ensure the computed values are also finite before casting
                x_calc = element.data.shape[1] * (x_safe * width) / width - 1e-9
                y_calc = element.data.shape[0] * (y_safe * height) / height - 1e-9
                X_mask = np.int32(np.nan_to_num(x_calc, nan=0.0, posinf=0.0, neginf=0.0))
                Y_mask = np.int32(np.nan_to_num(y_calc, nan=0.0, posinf=0.0, neginf=0.0))
                for i in range(x.shape[0]):
                    if np.isnan(x[i]) or np.isnan(y[i]):
                        continue
                    mx = X_mask[i]
                    my = Y_mask[i]
                    if mx < 0 or mx >= element.data.shape[1] or my < 0 or my >= element.data.shape[0]:
                        self.data[0][i] = np.nan
                        self.data[1][i] = np.nan
                    else:
                        if not element.data[my, mx]:
                            self.data[0][i] = np.nan
                            self.data[1][i] = np.nan

            else:
                raise Exception("Pattern: Masking Image is not a mask but a", element.type)


    def carve(self, element, width=None, height=None):
        x, y = self.data

        if width == None:
            width = self.width
        if height == None:
            height = self.height

        if isinstance(element, Element):
            N = x.shape[0]
            z = np.zeros(N)
            for i in range(N):
                if np.isnan(x[i]) or np.isnan(y[i]):
                    continue
                pos = [x[i] * width, y[i] * height]
                if element.inside(pos):
                    z[i] = np.nan
            self.data = (x, y + z)

        # elif isinstance(element, Image):
        #     if element.type == "mask":
        #         self.data = (x, y + Image.data * 0.0)

        #     else:
        #         raise Exception("Pattern: Masking Image is not a mask but a", element.type)


    def getPoints(self):
        X, Y = self.data
        W, H = self.width, self.height

        pts = []
        for x, y in zip( *(X * W, Y * H) ):
            if not np.isnan(x) and not np.isnan(y):
                pts.append( transform( [x,y], rotate=self.rotate, scale=self.scale, translate=self.translate, anchor=self.center) )

        return pts


    def getPath(self, **kwargs):
        from .Path import Path

        X, Y = self.data
        W, H = self.width, self.height

        pts = []
        path = []
        draw = False
        for x, y in zip( *(X * W, Y * H) ):
            if np.isnan(x) or np.isnan(y):
                if draw and len(pts) > 0:
                    path.append( pts[:] )
                draw = False
            else:
                if not draw:
                    pts = [] 
                    draw = True
                pts.append( transform( [x,y], rotate=self.rotate, scale=self.scale, translate=self.translate, anchor=self.center) )

        if draw and len(pts) > 0:
            path.append( pts[:] )


        path = Path(path)

        optimize = kwargs.pop('optimize', False)
        if optimize:
            path = path.getSimplify().getSorted()

        return path


    def getGCodeString(self, surface, **kwargs):
        head_up_height = kwargs.pop('head_up_height', 3)
        depth = kwargs.pop('depth', -0.5)
        head_up_speed = kwargs.pop('head_up_speed', 800)
        head_down_speed = kwargs.pop('head_down_speed', 500)
        move_speed = kwargs.pop('move_speed', 300)

        width = kwargs.pop('width', self.width)
        height = kwargs.pop('height', self.height)
        threshold = kwargs.pop('threshold', 0.5)

        transformed = self.isTransformed

        gcode_str = ''
        gcode_str += "G0 Z%0.1f F" % (head_up_height) + str(head_up_speed) + "\n"
        
        # Map the pattern to get the Zs
        if isinstance(surface, Image):
            if surface.type == "grayscale":
                Z = self._map(surface.data.T)

            elif surface.type == "mask":
                return self.mask(surface)
        else:
            Z = self._map(surface.T)

        # Extract the Xs and Ys from the pattern
        X, Y = self.data

        draw = False
        for x, y, z in zip( *(X * width, Y * height, Z) ):
            if (np.isnan(x) or np.isnan(y)) or z < threshold:
                if draw:
                    draw = False

                    gcode_str += "G0 Z%0.1f F" % (head_up_height) + str(head_up_speed) + "\n"
            else:
                if not draw:
                    draw = True

                if transformed:
                    x, y = transform( [x,y], rotate=self.rotate, scale=self.scale, translate=self.translate, anchor=self.center)
                gcode_str += "G0 X%0.1f Y%0.1f\n" % (x, y)
                gcode_str += "G1 Z%0.1f F" % (depth * z) + str(head_down_speed) +"\n"

                

        return gcode_str
