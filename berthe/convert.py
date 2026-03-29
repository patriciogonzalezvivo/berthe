#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from collections import defaultdict
from .pattern_generators import *

from .Path import Path
from .Polygon import Polygon
from .Image import Image
from .Pattern import *
from .tools import transform


def ImageDrawingToPath(image_path, epsilon_factor=0.0001, scale=1.0, translate=(0,0)):
    try:
        import cv2 as cv
    except ImportError:
        cv = None

    if cv is None:
        raise Exception('Surface.fromThreshold() requires OpenCV')
    
    try:
        from skimage.morphology import skeletonize
    except ImportError:
        skeletonize = None

    if skeletonize is None:
        raise Exception('Surface.fromThreshold() requires scikit-image')
    
    # 1. Load and Preprocess
    image = cv.imread(image_path)
    if image is None:
        print(f"Error: Could not load image at {image_path}")
        return

    gray = cv.cvtColor(image, cv.COLOR_BGR2GRAY)
    _, binary = cv.threshold(gray, 127, 255, cv.THRESH_BINARY_INV) # Invert for black lines on white background

    skeleton = skeletonize(binary // 255)
    skeleton_display = (skeleton * 255).astype(np.uint8)

    # 2. Find Contours
    contours, _ = cv.findContours(skeleton_display, cv.RETR_LIST, cv.CHAIN_APPROX_SIMPLE)

    vector_paths = []
    for contour in contours:
        # 3. Approximate Contours
        epsilon = epsilon_factor * cv.arcLength(contour, True)
        approx = cv.approxPolyDP(contour, epsilon, True)
        
        # 4. Scale and Translate
        points = [(point[0][0] * scale + translate[0], point[0][1] * scale + translate[1]) for point in approx]
        if len(points) > 1:
            vector_paths.append(points)

    return Path(vector_paths)


def ImageSurfaceCoorners(image_path, scale=1.0, translate=(0,0)):
    try:
        import cv2 as cv
    except ImportError:
        cv = None

    if cv is None:
        raise Exception('Surface.fromThreshold() requires OpenCV')
    
    # 1. Load and Preprocess
    image = cv.imread(image_path)
    if image is None:
        print(f"Error: Could not load image at {image_path}")
        return

    gray = cv.cvtColor(image, cv.COLOR_BGR2GRAY)
    _, binary = cv.threshold(gray, 127, 255, cv.THRESH_BINARY)

    # 2. Find Contours
    contours, _ = cv.findContours(binary, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)

    # 3. Scale and Translate
    contours = [[(point[0][0] * scale + translate[0], point[0][1] * scale + translate[1]) for point in contour] for contour in contours]

    # Flatten the list of contours
    contours = [point for contour in contours for point in contour]

    return contours


def ImageContourToPath(filename, threshold=0.5, scale=1.0):
    try:
        import cv2 as cv
    except ImportError:
        cv = None

    if cv is None:
        raise Exception('Surface.fromThreshold() requires OpenCV')

    path = []    

    if isinstance(filename, Image):
        filename = filename.filename
    im = cv.imread( filename )
    blur = cv.GaussianBlur(im, (3, 3),0)
    imgray = cv.cvtColor( blur, cv.COLOR_BGR2GRAY )
    ret, thresh = cv.threshold(imgray, int(threshold * 255), 255, cv.THRESH_BINARY)
    
    # Handle different OpenCV versions
    contours_result = cv.findContours(thresh, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)
    if len(contours_result) == 3:
        # OpenCV 3.x returns (image, contours, hierarchy)
        image, contours, hierarchy = contours_result
    else:
        # OpenCV 4.x returns (contours, hierarchy)
        contours, hierarchy = contours_result

    # height, width = im.shape[:2]
    # scale = [ (1.0 / width) * size[0], (1.0 / height) * size[1] ]

    for contour in contours:
        points = []
        for point in contour:
            # points.append( (point[0][0] * scale[0], point[0][1] * scale[1]) )
            points.append( (point[0][0] * scale, point[0][1] * scale) )
        
        # if len(points) > 2:
        #     points.append( points[0] )
            
        path.append( points )

    return Path( path )


def ImageThresholdToPolygons(filename, threshold=0.5, min_area=10.0, scale=1.0, rotate=0, translate=[0.0, 0.0]):
    try:
        import cv2 as cv
    except ImportError:
        cv = None

    if cv is None:
        raise Exception('Surface.fromThreshold() requires OpenCV')

    polygons = []    

    if isinstance(filename, Image):
        filename = filename.filename
    im = cv.imread( filename )
    blur = cv.GaussianBlur(im, (3, 3),0)
    imgray = cv.cvtColor( blur, cv.COLOR_BGR2GRAY )
    ret, thresh = cv.threshold(imgray, int(threshold * 255), 255, cv.THRESH_BINARY)
    
    # Handle different OpenCV versions
    contours_result = cv.findContours(thresh, cv.RETR_CCOMP, cv.CHAIN_APPROX_SIMPLE)
    if len(contours_result) == 3:
        # OpenCV 3.x returns (image, contours, hierarchy)
        image, contours, hierarchy = contours_result
    else:
        # OpenCV 4.x returns (contours, hierarchy)
        contours, hierarchy = contours_result

    if not contours:
        return polygons

    # Handle case where hierarchy might be None
    if hierarchy is None:
        # If no hierarchy, treat all contours as parent contours
        for idx, cnt in enumerate(contours):
            if cv.contourArea(cnt) >= min_area:
                assert cnt.shape[1] == 1
                poly = Polygon( trans(cnt[:, 0, :]) )
                polygons.append(poly)
        return polygons

    # now messy stuff to associate parent and child contours
    cnt_children = defaultdict(list)
    child_contours = set()
    assert hierarchy.shape[0] == 1
    # http://docs.opencv.org/3.1.0/d9/d8b/tutorial_py_contours_hierarchy.html
    for idx, (_, _, _, parent_idx) in enumerate(hierarchy[0]):
        if parent_idx != -1:
            child_contours.add(idx)
            cnt_children[parent_idx].append(contours[idx])
    # create actual polygons filtering by area (removes artifacts)

    def trans(points):
        result = []
        for point in points:
            result.append( transform([point[0], point[1]], translate=translate, scale=scale, rotate=rotate ))
        return result

    for idx, cnt in enumerate(contours):
        if idx not in child_contours and cv.contourArea(cnt) >= min_area:
            assert cnt.shape[1] == 1
            poly = Polygon( trans(cnt[:, 0, :]) )

            for c in cnt_children.get(idx, []):
                if cv.contourArea(c) >= min_area:
                    poly.addHole( trans(c[:, 0, :]) )
            polygons.append(poly)

    return polygons


def GrayscaleToPattern(grayscale, **kwargs):
    grayscale = Image( grayscale )

    threshold = float(kwargs.pop('threshold', 0.5))
    invert = kwargs.pop('invert', False)
    pattern = kwargs.pop('pattern', None)
    pattern_angle = float(kwargs.pop('pattern_angle', 0.0))
    mask = kwargs.pop('mask', None)

    # Make surface to carve from (copy from gradient to get same dinesions)
    surface = grayscale.copy()
    surface.fill(1.0)

    # Make gradient into dither mask
    grayscale.dither(threshold=threshold, invert=invert)
    surface = surface - grayscale

    # Load and remove Mask
    if isinstance(mask, str):
        mask = Image(mask)
        mask = mask.threshold()
        surface = surface - mask

    surface = surface.data * 0.0;

    # Create pattern
    if pattern is None:
        pattern_resolution = int(kwargs.pop('pattern_resolution', min(grayscale.width, grayscale.height) * 0.5))
        pattern_presicion = float(kwargs.pop('pattern_presicion', 1.0))
        pattern_offset = float(kwargs.pop('pattern_offset', 0.0)) 
        pattern = Pattern( stripes_pattern(pattern_resolution, min(grayscale.width, grayscale.height) * pattern_presicion, pattern_offset), **kwargs)
    elif not isinstance(pattern, Pattern):
        pattern = Pattern( pattern, **kwargs  )

    if pattern_angle > 0:
        pattern.turn(pattern_angle)

    # # Project pattern on surface 
    pattern.project(surface)

    return pattern


def HeightmapToPattern(filename, **kwargs):
    grayscale = kwargs.pop('grayscale', None)
    camera_angle = float(kwargs.pop('camera_angle', 10.0))

    threshold = float(kwargs.pop('threshold', 0.5))
    invert = kwargs.pop('invert', False)
    pattern = kwargs.pop('pattern', None)
    pattern_angle = float(kwargs.pop('pattern_angle', 0.0))
    mask = kwargs.pop('mask', None)

    # Load heightmap
    heightmap = Image(filename)
    heightmap.occlude(camera_angle)

    # load and remove mask
    if isinstance(mask, str):
        mask = Image(mask)
        mask = mask.threshold()
    heightmap = heightmap - mask

    # Load gradient into dither mask
    if grayscale is not None:
        gradientmap = Image( grayscale )
        heightmap = heightmap - gradientmap.dither(threshold=threshold, invert=invert)

    # Create pattern
    if pattern is None:
        pattern_resolution = int(kwargs.pop('pattern_resolution', min(heightmap.width, heightmap.height) * 0.5))
        pattern_presicion = float(kwargs.pop('pattern_presicion', 1.0))
        pattern_offset = float(kwargs.pop('pattern_offset', 0.0)) 
        pattern = Pattern( stripes_pattern(num_lines=pattern_resolution, resolution=min(heightmap.width, heightmap.height) * pattern_presicion, offset=pattern_offset), **kwargs )
    elif not isinstance(pattern, Pattern):
        pattern = Pattern( pattern, **kwargs )

    if pattern_angle > 0:
        pattern.turn(pattern_angle)

    pattern.project(heightmap, camera_angle)

    return pattern
