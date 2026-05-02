#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import math
import numpy as np

# Basic trigonometry
# -----------------------------------------------------------------

def normalize(v, tolerance=0.00001):
    """Return the unit vector of *v*, or ``None`` if *v* is zero-length."""
    mag2 = sum(n * n for n in v)
    if abs(mag2 - 1.0) > tolerance:
        mag = math.sqrt(mag2)
        if mag == 0.0:
            return None
        v = tuple(n / mag for n in v)
    return np.array(v)


def dot(v1, v2):
    """Dot product of two sequences of equal or unequal length (uses the shorter)."""
    lim = min(len(v1), len(v2))
    return float(np.dot(v1[:lim], v2[:lim]))


def length(v):
    """Euclidean length of vector *v*."""
    return float(np.linalg.norm(v))


def distance(A, B):
    """Euclidean distance between points *A* and *B*."""
    ab = np.array(B) - np.array(A)
    return np.sqrt( ab[0] * ab[0] + ab[1] * ab[1] )


def perpendicular(A, B):
    """Unit vector perpendicular to the segment A→B, rotated 90° CCW."""
    ab = np.array(B) - np.array(A)
    dir_ab = normalize(ab)
    return np.array([-dir_ab[1], dir_ab[0]])


def rotate(xy, deg, anchor=[0, 0]):
    """Rotate point *xy* by *deg* degrees around *anchor*."""
    radians = math.radians(deg)
    x, y = xy

    x = x - anchor[0]
    y = y - anchor[1]
    cos_rad = math.cos(radians)
    sin_rad = math.sin(radians)
    qx = anchor[0] + cos_rad * x + sin_rad * y
    qy = anchor[1] + -sin_rad * x + cos_rad * y

    return np.array([qx, qy])


def clamp(value, min_value, max_value):
    """Clamp *value* to the inclusive range [*min_value*, *max_value*]."""
    return max(min(value, max_value), min_value)


def transform(xy, rotate = 0, scale = [1,1], translate = [0,0], anchor=[0, 0]):
    x, y = xy
    
    if scale != [1, 1] or rotate != 0:
        radians = math.radians(rotate)
        if isinstance(scale, tuple) or isinstance(scale, list):
            scale_x, scale_y = scale
        else:
            scale_x, scale_y = scale, scale

        x = x - anchor[0]
        y = y - anchor[1]

        cos_theta = math.cos(radians)
        sin_theta = math.sin(radians)
        nx = x * cos_theta - y * sin_theta
        ny = x * sin_theta + y * cos_theta

        nx *= scale_x
        ny *= scale_y

        nx += anchor[0]
        ny += anchor[1] 
    else:
        nx = x
        ny = y

    nx += translate[0]
    ny += translate[1]
    return [nx, ny]


def remap(value, in_min, in_max, out_min, out_max):
    """Linearly remap *value* from [*in_min*, *in_max*] to [*out_min*, *out_max*]."""
    in_span = in_max - in_min
    out_span = out_max - out_min

    value = float(value - in_min)
    if value != 0:
        value /= float(in_span)
    return out_min + (value * out_span)


def lerp(A, B, t):
    """Linear interpolation: return A + (B - A) * t.  Works for scalars and arrays."""
    A = np.array(A)
    B = np.array(B)
    return A * (1.0 - t) + B * t

# Path operations 
# -----------------------------------------------------------------

def points_length(points):
    """Total arc-length of an open polyline defined by a list of (x, y) pairs."""
    result = 0
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        result += math.hypot(x2 - x1, y2 - y1)
    return result


def path_length(path):
    """Sum of arc-lengths of all sub-paths in *path* (a list of polylines)."""
    return sum([points_length(path) for path in path], 0)


def join_path(path, tolerance):
    if len(path) < 2:
        return path
    result = [list(path[0])]
    for path in path[1:]:
        x1, y1 = result[-1][-1]
        x2, y2 = path[0]
        d = hypot(x2 - x1, y2 - y1)
        if d <= tolerance:
            result[-1].extend(path)
        else:
            result.append(list(path))
    return result

# Convertions
# -----------------------------------------------------------------

def polar2xy(center, angle, radius):
    """Convert polar coordinates to Cartesian (x, y).

    *angle* is in degrees, measured counter-clockwise from the positive X axis.
    *radius* may be a scalar or a (rx, ry) tuple for elliptical coordinates.
    """
    a = math.radians(angle)
    rx = 1.0
    ry = 1.0
    if isinstance(radius, tuple) or isinstance(radius, list):
        rx = radius[0]
        ry = radius[1]
    else:
        rx = radius
        ry = radius
    return np.array([   center[0] + rx * math.cos(a), 
                        center[1] + ry * math.sin(a)    ])


def xy2polar(center, pos):
    """Convert Cartesian *pos* to (angle_degrees, radius) relative to *center*."""
    ab = np.array(pos) - np.array(center)

    dist = np.sqrt( ab[0] * ab[0] + ab[1] * ab[1] )
    
    angle = math.atan2(ab[1], ab[0])
    return [math.degrees(angle), dist]


# Bezier controls
# -----------------------------------------------------------------

def lineProp( pointA, pointB ):
    lengthX = pointB[0] - pointA[0]
    lengthY = pointB[1] - pointA[1]
    return math.sqrt( math.pow(lengthX, 2) + math.pow(lengthY, 2)), math.atan2(lengthY, lengthX)


def controlPoint( current, _previous, _next, reverse ):
    p = _previous
    n = _next

    if _previous is None:
        p = current
    if _next is None:
        n = current

    smoothing = 0.2
    o = lineProp(p, n) 

    angle = o[1]
    if reverse: 
        angle += math.pi
    length = o[0] * smoothing

    x = current[0] + math.cos(angle) * length
    y = current[1] + math.sin(angle) * length

    return [x, y]


def bezierCommand( point, i, a ):
    #  start control point
    cpsX, cpsY = controlPoint(a[i - 1], a[i - 2], point, False) 

    #  end control point
    if i + 1 >= len(a):
        cpeX, cpeY = controlPoint(point, a[i - 1], None, True)
    else:
        cpeX, cpeY = controlPoint(point, a[i - 1], a[i + 1], True)

    return ' C ' + str(cpsX) + ',' + str(cpsY) + " " + str(cpeX) + "," + str(cpeY) + " " + str(point[0]) + "," + str(point[1])

# Collisions

#  https://github.com/openframeworks/openFrameworks/blob/patch-release/libs/openFrameworks/graphics/ofPolyline.inl#L622
def pointInside( pos, points ):
    counter = 0

    # double xinters;
    p1 = [0.0, 0.0]
    p2 = [0.0, 0.0]

    N = len(points)

    p1 = points[0]

    for i in range(1, N + 1):
        p2 = points[i % N]

        if pos[1] > min(p1[1], p2[1]):
            if pos[1] <= max(p1[1], p2[1]):
                if pos[0] <= max(p1[0], p2[0]):
                    if p1[1] != p2[1]:
                        xinters = (pos[1] - p1[1]) * (p2[0] - p1[0]) / (p2[1] - p1[1]) + p1[0]
                        if p1[0] == p2[0] or pos[0] <= xinters:
                            counter += 1
        p1 = p2
        
    return counter % 2 != 0

# https://github.com/openframeworks/openFrameworks/blob/master/libs/openFrameworks/math/ofMath.h#L435
def linesIntersection(line1Start, line1End, line2Start, line2End):
    intersection = [0.0, 0.0]
    diffLA = np.array(line1End) - np.array(line1Start)
    compareA = diffLA[0] * line1Start[1] - diffLA[1] * line1Start[0]
    if ( ( diffLA[0]*line2Start[1] - diffLA[1]*line2Start[0] ) < compareA ) ^ ( ( diffLA[0]*line2End[1] - diffLA[1]*line2End[0] ) < compareA ):

        diffLB = np.array(line2End) - np.array(line2Start)
        compareB = diffLB[0] * line2Start[1] - diffLB[1] * line2Start[0]
        if ( ( diffLB[0]*line1Start[1] - diffLB[1]*line1Start[0] ) < compareB ) ^ ( ( diffLB[0]*line1End[1] - diffLB[1]*line1End[0]) < compareB ):
            lDetDivInv = 1 / ((diffLA[0] * diffLB[1]) - (diffLA[1] * diffLB[0]))
            intersection[0] =  -((diffLA[0] * compareB) - (compareA * diffLB[0])) * lDetDivInv
            intersection[1] =  -((diffLA[1] * compareB) - (compareA * diffLB[1])) * lDetDivInv
            return intersection

    return None


# PARSING SVGs files 

def dom2dict(element):
    """Converts DOM elements to dictionaries of attributes."""
    keys = list(element.attributes.keys())
    values = [val.value for val in list(element.attributes.values())]
    return dict(list(zip(keys, values)))


#  From Andy Port's svgpathtools 
# https://github.com/mathandy/svgpathtools/blob/master/svgpathtools/parser.py#L221
# 
def _parse_transform_substr(transform_substr):

    type_str, value_str = transform_substr.split('(')
    value_str = value_str.replace(',', ' ')
    values = list(map(float, filter(None, value_str.split(' '))))

    transform = np.identity(3)
    if 'matrix' in type_str:
        if not _check_num_parsed_values(values, [6]):
            return transform

        transform[0:2, 0:3] = np.array([values[0:6:2], values[1:6:2]])

    elif 'translate' in transform_substr:
        if not _check_num_parsed_values(values, [1, 2]):
            return transform

        transform[0, 2] = values[0]
        if len(values) > 1:
            transform[1, 2] = values[1]

    elif 'scale' in transform_substr:
        if not _check_num_parsed_values(values, [1, 2]):
            return transform

        x_scale = values[0]
        y_scale = values[1] if (len(values) > 1) else x_scale
        transform[0, 0] = x_scale
        transform[1, 1] = y_scale

    elif 'rotate' in transform_substr:
        if not _check_num_parsed_values(values, [1, 3]):
            return transform

        angle = values[0] * np.pi / 180.0
        if len(values) == 3:
            offset = values[1:3]
        else:
            offset = (0, 0)
        tf_offset = np.identity(3)
        tf_offset[0:2, 2:3] = np.array([[offset[0]], [offset[1]]])
        tf_rotate = np.identity(3)
        tf_rotate[0:2, 0:2] = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
        tf_offset_neg = np.identity(3)
        tf_offset_neg[0:2, 2:3] = np.array([[-offset[0]], [-offset[1]]])

        transform = tf_offset.dot(tf_rotate).dot(tf_offset_neg)

    elif 'skewX' in transform_substr:
        if not _check_num_parsed_values(values, [1]):
            return transform

        transform[0, 1] = np.tan(values[0] * np.pi / 180.0)

    elif 'skewY' in transform_substr:
        if not _check_num_parsed_values(values, [1]):
            return transform

        transform[1, 0] = np.tan(values[0] * np.pi / 180.0)
    else:
        # Return an identity matrix if the type of transform is unknown, and warn the user
        warnings.warn('Unknown SVG transform type: {0}'.format(type_str))

    return transform


def parse_transform(el, transform_str):
    """Converts a valid SVG transformation string into a 3x3 matrix.
    If the string is empty or null, this returns a 3x3 identity matrix"""
    if not transform_str:
        return np.identity(3)
    elif not isinstance(transform_str, str):
        raise TypeError('Must provide a string to parse')

    transform_substrs = transform_str.split(')')[:-1]
    for transform_substr in transform_substrs:

        type_str, value_str = transform_substr.split('(')
        value_str = value_str.replace(',', ' ')
        values = list(map(float, filter(None, value_str.split(' '))))

        if 'translate' in transform_substr:
            x_translate = float(values[0])
            y_translate = float(values[1])
            el = el.getTranslated(x_translate, y_translate)

        elif 'scale' in transform_substr:
            x_scale = float(values[0])
            y_scale = float(values[1]) if (len(values) > 1) else x_scale
            el = el.getScaled(x_scale, y_scale)

        elif 'rotate' in transform_substr:
            deg = float(values[0])
            el = el.getRotated(deg)

        # elif 'skewX' in transform_substr:
        #     if not _check_num_parsed_values(values, [1]):
        #         return transform

        #     transform[0, 1] = np.tan(values[0] * np.pi / 180.0)

        # elif 'skewY' in transform_substr:
        #     if not _check_num_parsed_values(values, [1]):
        #         return transform

        #     transform[1, 0] = np.tan(values[0] * np.pi / 180.0)
        else:
            # Return an identity matrix if the type of transform is unknown, and warn the user
            warnings.warn('Unknown SVG transform type: {0}'.format(type_str))

    return el


#  COLOR

# stackoverflow.com/questions/214359/converting-hex-color-to-rgb-and-vice-versa
def hex2rgb(value):
    """Converts a hexadeximal color string to an RGB 3-tuple
    EXAMPLE
    -------
    >>> hex2rgb('#0000FF')
    (0, 0, 255)
    """
    value = value.lstrip('#')
    lv = len(value)
    return tuple(int(value[i:i+lv//3], 16) for i in range(0, lv, lv//3))


def rgb2gray(rgb):
    # print(rgb)
    r, g, b = rgb[0], rgb[1], rgb[2]
    gray = 0.2989 * r + 0.5870 * g + 0.1140 * b

    return gray


def hex2gray(value):
    return rgb2gray(hex2rgb(value))


def hex2fill(value):
    value = hex2gray(value)
    return value < 50.0