#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import numpy as np
from PIL import Image as PILImage

def normalise(im):
    """Normalize an image matrix from 0 - 255 to 0.0 - 1.0f range at 64bit  
    """
    return np.clip(np.float64(im) / 255, 0, None)


def extract_rgb(image):
    """Extract the RGB planes from an RGBA image.
    
    Note that this returns a copy. If you wish to obtain a view that
    allows mutating pixels, simply use slicing instead. For
    example, to invert the colors of an image while leaving alpha
    intact, you can do:
    <code>myimage[:,:,:3] = 1.0 - myimage[:,:,:3]</code>.
    """
    assert len(image.shape) == 3 and image.shape[2] >= 3
    planes = np.dsplit(image, image.shape[2])
    return np.dstack(planes[:3])


def reshape(image):
    """Add a trailing dimension to single-channel 2D images.
    See also <a href="#unshape">unshape</a>.
    """
    if len(image.shape) == 2:
        image = np.reshape(image, image.shape + (1,))
    return image


def load_image_rgb(filename):
    """Load a Image in a RGB 64bit floating point matrix
    """
    img = PILImage.open( filename ).convert('RGB')
    array = np.array(img, np.uint8)
    array = extract_rgb(array)
    array = normalise(array)
    return array


def load_grayscale(filename):
    """Load a Image in a GRAYSCALE 64bit floating point matrix
    """
    img = PILImage.open( filename ).convert('L')
    array = np.array(img, np.uint8)
    array = normalise(array)
    return array 


def load_normalmap(filename):
    return load_image_rgb(filename) * 2.0 - 1.0


class Image(object):
    def __init__( self, data, type='grayscale' ):
        self.filename = "nan"
        self.type = type

        if isinstance(data, str):
            self.filename = data
            if type == '2D_angle':
                self.data = load_normalmap( data )
                self.data = np.arctan2(self.data [..., 1], self.data [..., 0]) 
                self.data = (self.data  / np.pi) * 0.5 + 0.5
            else:
                self.data = load_grayscale( data )

        elif isinstance(data, Image):
            self.data = data.data.copy()
            self.type = data.type
            self.filename = data.filename

        elif isinstance(data, (np.ndarray, np.generic) ):
            self.data = data.copy()

        else:
            raise Exception('Unknown data type')
            return

        self.height, self.width = self.data.shape[:2]


    def __sub__(self, other=None):
        if isinstance(other, (np.ndarray, np.generic) ):
            self.data[ np.invert(other) ] = np.nan

        elif isinstance(other, Image):
            if other.type == "mask":
                # self.data[ np.invert(other.data)] = np.nan
                # Ensure other.data is boolean and shapes match
                mask = np.invert(other.data.astype(bool))
                if mask.shape == self.data.shape:
                    self.data[mask] = np.nan
            elif other.type == "grayscale":
                self.data -= other.data
            else:
                raise Exception("Other is not a mask")

        elif other is None:
            return self

        else:
            raise Exception('Unknown data type')

        return self


    def fill(self, value, change_type=None):
        self.data.fill(value)
        if change_type is not None:
            self.type = change_type
        elif isinstance(value, float):
            self.type = 'grayscale'
        return self


    def copy(self):
        return Image(self)


    def threshold(self, threshold=0.5, invert=False):
        if invert:
            self.data = self.data < threshold
        else:
            self.data = self.data > threshold
        
        # Change type to mask... for now on the array will have booleans and not floats
        self.type = "mask" 
        return self


    def dither(self, threshold=0.5, invert=False ):
        """Floyd-Steinberg dithering algorithm.
        Note: This implementation uses nested loops which can be slow for large images.
        For images >1024x1024, consider reducing resolution before dithering.
        Performance: ~O(width * height) with per-pixel operations.
        """
        derr = np.zeros(self.data.shape, dtype=float)

        div = 8
        for y in range(self.data.shape[0]):
            for x in range(self.data.shape[1]):
                newval = derr[y,x] + self.data[y,x]
                if newval >= threshold:
                    errval = newval - 1.0
                    self.data[y,x] = 1.
                else:
                    errval = newval
                    self.data[y,x] = 0.
                if x + 1 < self.data.shape[1]:
                    derr[y, x + 1] += errval / div
                    if x + 2 < self.data.shape[1]:
                        derr[y, x + 2] += errval / div
                if y + 1 < self.data.shape[0]:
                    derr[y + 1, x - 1] += errval / div
                    derr[y + 1, x] += errval / div
                    if y + 2 < self.data.shape[0]:
                        derr[y + 2, x] += errval / div
                    if x + 1 < self.data.shape[1]:
                        derr[y + 1, x + 1] += errval / div
        self.data = self.data[::1,:]
        return self.threshold(0.5, not invert)


    def occlude(self, angle):
        if angle == 0:
            return self

        s = self.data.shape[0]
        
        # Just as in projection, we calculate the Y and Z
        # coefficients with sin/cos.
        y_coef = np.cos(np.radians( (angle) ))
        z_coef = np.sin(np.radians( (angle) ))
        
        # Rotate the surface so that the visibilty mask represents
        # the visibility at the desired angle.
        projected_surface = (
            - y_coef * np.expand_dims(np.linspace(0., 1., s), axis=1)
            + z_coef * self.data
        )
        
        # Calculate the cumulative maximum along each cross-section of
        # the projected surface. We flip on the input and output because
        # we want to accumulate from the bottom of the surface up, rather
        # than the top-down. This is because we interpret the bottom of
        # the surface as closer to the observer.
        projected_surface_max = np.flipud(np.maximum.accumulate(np.flipud(projected_surface)))
        
        # Compare each point on the surface to the cumulative maximum
        # along its cross-section.
        mask = projected_surface == projected_surface_max
        self.data[ np.invert( mask ) ] = np.nan

        return self


