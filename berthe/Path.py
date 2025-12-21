#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import math
import numpy as np

from .Element import Element
from .Index import Index
from .tools import path_length, transform

# Mostly rom Axi by Michael Fogleman
# https://github.com/fogleman/axi/blob/master/axi/spatial.py

class Path(Element):
    def __init__(self, path=None, **kwargs):
        Element.__init__(self, **kwargs);
        # self.head_width = kwargs.pop('head_width', 0.2)
        # self.id = kwargs.pop('id', None)

        if path is None:
            self.path = []
        elif isinstance(path, Path):
            self.path = path.path

        elif isinstance(path, Element):
            self.path = path.getPath()

        elif isinstance(path, str):
            self.path = []
            self.setFromString(path)

        else:
            self.path = path

        self._length = None
        self._down_length = None


    def __len__(self):
        return len(self.path)


    def __iter__(self):
        self._index = 0
        return self


    def __next__(self):
        if self._index < len(self.path):
            result = self[ self._index ]
            self._index += 1
            return result
        else:
            raise StopIteration


    def next(self):
        return self.__next__()


    def __getitem__(self, index):
        from .Polyline import Polyline
        if type(index) is int:
            return Polyline( self.path[index], translate=self.translate, scale=self.scale, rotate=self.rotate, head_width=self.head_width, color=self.color )
        else:
            return None


    @property
    def length(self):
        if self._length is None:
            length = self.down_length
            for p0, p1 in zip(self.path, self.path[1:]):
                x0, y0 = p0[-1]
                x1, y1 = p1[0]
                length += math.hypot(x1 - x0, y1 - y0)
            self._length = length
        return self._length


    @property
    def up_length(self):
        return self.length - self.down_length


    @property
    def down_length(self):
        if self._down_length is None:
            self._down_length = path_length(self.path)
        return self._down_length


    @property
    def width(self):
        return self.bounds.width


    @property
    def height(self):
        return self.bounds.height
    

    def add(self, other):
        from .Polyline import Polyline

        if isinstance(other, Path):
            self.path.extend( other.path )
        elif isinstance(other, Polyline):
            points  = other.getPoints() 
            if len(points) > 1: 
                self.path.append( points )
        elif isinstance(other, Element):
            self.path.extend( other.getPath() )
        elif isinstance(other, list):
            self.path.append( other )
        else:
            raise Exception("Error, don't know what to do with: ", other)


    def setFromString(self, path_string, **kwargs):

        # From Andy Port 
        # https://github.com/mathandy/svgpathtools/blob/master/svgpathtools/parser.py#L35

        import re
        COMMANDS = set('MmZzLlHhVvCcSsQqTtAa')
        UPPERCASE = set('MZLHVCSQTA')

        COMMAND_RE = re.compile("([MmZzLlHhVvCcSsQqTtAa])")
        FLOAT_RE = re.compile("[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?")

        def tokenize_path(pathdef):
            for x in COMMAND_RE.split(pathdef):
                if x in COMMANDS:
                    yield x
                for token in FLOAT_RE.findall(x):
                    yield token

        # In the SVG specs, initial movetos are absolute, even if
        # specified as 'm'. This is the default behavior here as well.
        # But if you pass in a current_pos variable, the initial moveto
        # will be relative to that current_pos. This is useful.

        elements = list(tokenize_path(path_string))

        # Reverse for easy use of .pop()
        elements.reverse()

        current_pos = np.array([0.0, 0.0])
        start_pos = np.array([0.0, 0.0])
        command = None
        last_control = []

        from .Polyline import Polyline
        poly = Polyline(fill=self.fill, stroke_width=self.stroke_width)

        while elements:
            if elements[-1] in COMMANDS:
                # New command.
                last_command = command  # Used by S and T
                command = elements.pop()
                absolute = command in UPPERCASE
                command = command.upper()
            else:
                # If this element starts with numbers, it is an implicit command
                # and we don't change the command. Check that it's allowed:
                if command is None:
                    raise ValueError("Unallowed implicit command in %s, position %s" % (
                        path_string, len(path_string.split()) - len(elements)))

            if command == 'M':
                # Moveto command.
                pos = np.array([float(elements.pop()), float(elements.pop())])
                if absolute:
                    current_pos = pos
                else:
                    current_pos += pos

                # when M is called, reset start_pos

                if poly.size() > 0:
                    self.add( poly.getPath() )
                    poly = Polyline(fill=self.fill, stroke_width=self.stroke_width)

                # This behavior of Z is defined in svg spec:
                # http://www.w3.org/TR/SVG/paths.html#PathDataClosePathCommand
                start_pos = current_pos

                # Implicit moveto commands are treated as lineto commands.
                # So we set command to lineto here, in case there are
                # further implicit commands after this moveto.
                command = 'L'
                poly.lineTo( current_pos )

            elif command == 'Z':
                # Close path
                # if not (current_pos.all() == start_pos.all()):
                #     poly.lineTo( start_pos )

                poly.setClosed( True )
                poly = poly.getSimplify()
                self.add( poly.getPath() )
                poly = Polyline(fill=self.fill, stroke_width=self.stroke_width)

                current_pos = start_pos
                command = None

            elif command == 'L':
                pos = np.array([float(elements.pop()), float(elements.pop())])
                if not absolute:
                    pos += current_pos

                poly.lineTo( pos )
                current_pos = pos

            elif command == 'H':
                pos = np.array([float(elements.pop()), current_pos[1]])
                if not absolute:
                    pos += np.array([ current_pos[0], 0 ])
                poly.lineTo( pos )
                current_pos = pos

            elif command == 'V':
                pos = np.array([current_pos[0], float(elements.pop())])
                if not absolute:
                    pos += np.array([ 0, current_pos[1] ])
                poly.lineTo( pos )
                current_pos = pos

            elif command == 'C':
                control1 = np.array([float(elements.pop()), float(elements.pop())])
                control2 = np.array([float(elements.pop()), float(elements.pop())])
                end = np.array([float(elements.pop()), float(elements.pop())])

                if not absolute:
                    control1 += current_pos
                    control2 += current_pos
                    end += current_pos

                poly.cubicBezierTo( control1, control2, end )
                current_pos = end
                last_control = control2[:]

            elif command == 'S':
                # Smooth curve. First control point is the "reflection" of
                # the second control point in the previous path.

                if last_command not in 'CS':
                    # If there is no previous command or if the previous command
                    # was not an C, c, S or s, assume the first control point is
                    # coincident with the current point.
                    control1 = current_pos
                else:
                    # The first control point is assumed to be the reflection of
                    # the second control point on the previous command relative
                    # to the current point.
                    control1 = current_pos + current_pos - last_control

                control2 = np.array([float(elements.pop()), float(elements.pop())])
                end = np.array([float(elements.pop()), float(elements.pop())])

                if not absolute:
                    control2 += current_pos
                    end += current_pos

                poly.cubicBezierTo( control1, control2, end )
                current_pos = end
                last_control = control2

            # elif command == 'Q':
            #     control = float(elements.pop()) + float(elements.pop()) * 1j
            #     end = float(elements.pop()) + float(elements.pop()) * 1j

            #     if not absolute:
            #         control += current_pos
            #         end += current_pos

            #     segments.append(QuadraticBezier(current_pos, control, end))
            #     current_pos = end

            # elif command == 'T':
            #     # Smooth curve. Control point is the "reflection" of
            #     # the second control point in the previous path.

            #     if last_command not in 'QT':
            #         # If there is no previous command or if the previous command
            #         # was not an Q, q, T or t, assume the first control point is
            #         # coincident with the current point.
            #         control = current_pos
            #     else:
            #         # The control point is assumed to be the reflection of
            #         # the control point on the previous command relative
            #         # to the current point.
            #         control = current_pos + current_pos - segments[-1].control

            #     end = float(elements.pop()) + float(elements.pop()) * 1j

            #     if not absolute:
            #         end += current_pos

            #     segments.append(QuadraticBezier(current_pos, control, end))
            #     current_pos = end

            elif command == 'A':
                radius = np.array([float(elements.pop()), float(elements.pop())])
                rotation = float(elements.pop())
                arc = float(elements.pop())
                sweep = float(elements.pop())
                end = np.array([float(elements.pop()), float(elements.pop())])

                if not absolute:
                    end += current_pos

                poly.arcTo( end, radius, large_arc=arc, sweep=sweep, rotate=rotation )
                current_pos = end
            else:
                print('Command', command, 'in not implemented' )

        if poly.size() > 0:
            poly = poly.getSimplify()
            self.add( poly.getPath() )


    def getPoints(self):
        return [(x, y) for points in self.path for x, y in points]


    def getConvexHull(self):
        try:
            from .Polyline import Polyline
            from shapely import geometry
        except ImportError:
            geometry = None

        if geometry is None:
            raise Exception('Polyline.getConvexHull() requires Shapely')

        polygon = geometry.Polygon( self.getPoints() )
        return Polyline( polygon.convex_hull.exterior.coords, head_width=self.head_width, color=self.color )


    def getPattern(self, width, height, **kwargs):
        resolution = kwargs.pop('resolution', None)

        from .Pattern import Pattern
        from .Polyline import Polyline
        pattern = Pattern(width=width, height=height, **kwargs, color=self.color)

        for points in self.path:
        
            if resolution:
                poly = Polyline(points)
                poly = poly.getResampledBySpacing(resolution)
                points = poly.getPoints()

            N = len(points)
            x = np.zeros(int(N)+1)
            y = np.zeros(int(N)+1)
            x.fill(np.nan)
            y.fill(np.nan)

            for i in range(N):
                X, Y = points[i]
                x[i] = X / float(pattern.width)
                y[i] = Y / float(pattern.height)

            x[N] = np.nan
            y[N] = np.nan

            pattern.add( (x.flatten('F'), y.flatten('F')) )

        return pattern


    def getSorted(self, reversable=True):
        if len(self.path) < 2:
            return self

        path = self.path[:]

        first = path[0]
        path.remove(first)
        result = [first]
        points = []

        for path in path:
            x1, y1 = path[0]
            x2, y2 = path[-1]
            points.append((x1, y1, path, False))

            if reversable:
                points.append((x2, y2, path, True))

        if len(points) <= 2:
            return self

        index = Index( chain=points )

        while index.size > 0:
            x, y, path, reverse = index.nearest(result[-1][-1])
            x1, y1 = path[0]
            x2, y2 = path[-1]
            index.remove((x1, y1, path, False))

            if reversable:
                index.remove((x2, y2, path, True))

            if reverse:
                result.append(list(reversed(path)))
            else:
                result.append(path)

        return Path( result, head_width=self.head_width, color=self.color )


    def getJoined(self, tolerance = None, boundary = None):
        try:
            from shapely import geometry
        except ImportError:
            geometry = None

        if boundary != None and geometry is None:
            print('Path.joined() will not work with boundary bacause needs Shapely')
            boundary = None

        if len(self.path) < 2:
            return self

        if tolerance is None:
            tolerance = self.head_width

        result = [list(self.path[0])]
        for path in self.path[1:]:
            x1, y1 = result[-1][-1]
            x2, y2 = path[0]

            join = False

            if boundary != None:
                walk_path = geometry.LineString( [result[-1][-1], path[0]] )
                walk_cut = walk_path.buffer( self.head_width * 0.5 )
                join = walk_cut.within(boundary) # and walk_path.length < max_walk
            else:
                join = math.hypot(x2 - x1, y2 - y1) <= tolerance

            if join:
                result[-1].extend(path)
            else:
                result.append(list(path))

        return Path(result, color=self.color)


    def getSimplify(self, tolerance = None):
        from .Polyline import Polyline

        result = Path(color=self.color)
        for points in self.path:
            if len(points) > 1:
                result.add( Polyline( points ).getSimplify(tolerance) )
        return result


    def getResampledBySpacing(self, spacing, **kwargs):
        from .Polyline import Polyline

        result = Path(color=self.color)
        for points in self.path:
            if len(points) > 1:
                result.add( Polyline( points, **kwargs ).getResampledBySpacing(spacing) )
        return result
    

    def splitByLength(self, length: float) -> list:
        """
        Split the Path into a list of Path objects, each with total length <= length.
        Splits can occur inside individual polylines by interpolating points.
        """
        from .Polyline import Polyline

        if length <= 0:
            raise ValueError("length must be > 0")

        result = []
        # current Path being built
        current_path = Path(color=self.color)
        current_len = 0.0
        # current polyline points being built inside current_path
        current_poly = None

        for points in self.path:
            if len(points) < 2:
                continue
            # work on a local mutable copy of the polyline points (tuples)
            pts = [tuple(p) for p in points]

            i = 0
            while i < len(pts) - 1:
                p0 = np.array(pts[i], dtype=float)
                p1 = np.array(pts[i + 1], dtype=float)
                edge_vec = p1 - p0
                edge_len = math.hypot(edge_vec[0], edge_vec[1])

                # if edge length is effectively zero, skip
                if edge_len <= 1e-12:
                    # Ensure we still carry forward the vertex
                    if current_poly is None:
                        current_poly = [tuple(p0)]
                    # append the end point (even if same)
                    current_poly.append(tuple(p1))
                    i += 1
                    continue

                remaining_capacity = length - current_len

                if edge_len <= remaining_capacity + 1e-12:
                    # we can fit the whole edge into current_path
                    if current_poly is None:
                        current_poly = [tuple(p0)]
                    current_poly.append(tuple(p1))
                    current_len += edge_len
                    i += 1
                else:
                    # need to split this edge: interpolate a point at t
                    t = max(0.0, min(1.0, remaining_capacity / edge_len))
                    split_pt = p0 + edge_vec * t
                    # add segment up to split_pt into current_poly
                    if current_poly is None:
                        current_poly = [tuple(p0)]
                    current_poly.append((float(split_pt[0]), float(split_pt[1])))

                    # finalize current_path with this polyline
                    if current_poly:
                        current_path.add(current_poly)
                        current_poly = None

                    result.append(current_path)
                    # start a new current_path
                    current_path = Path(color=self.color)
                    current_len = 0.0

                    # replace pts[i] with split_pt so next iteration works on remaining edge
                    pts[i] = (float(split_pt[0]), float(split_pt[1]))
                    # do not increment i so next loop will process the remaining portion from split_pt -> original p1

            # finished this input polyline; if we have an active current_poly, add it to current_path
            if current_poly:
                current_path.add(current_poly)
                current_poly = None

        # after processing all polylines, append the last current_path if it has data
        if len(current_path.path) > 0:
            result.append(current_path)

        return result


    def getTransformed(self, func):
        return Path([[func(x, y) for x, y in points] for points in self.path], color=self.color)


    def getMoved(self, x, y, ax, ay):
        bbox = self.bounds
        x1, y1, x2, y2 = bbox.limits
        dx = x1 + (x2 - x1) * ax - x
        dy = y1 + (y2 - y1) * ay - y
        return self.getTranslated(-dx, -dy)


    def getCentered(self, width, height):
        return self.getMoved(width / 2, height / 2, 0.5, 0.5)


    def getRotatedToFit(self, width, height, step=5):
        for angle in range(0, 180, step):
            path = self.getRotated(angle)
            if path.width <= width and path.height <= height:
                return path.getCentered(width, height)
        return None


    def getScaledToFit(self, width, height, padding=0):
        width -= padding * 2
        height -= padding * 2
        scale = min(width / self.width, height / self.height)
        return self.getScaled(scale, scale).getCentered(width, height)


    def getRotateAndScaleToFit(self, width, height, padding=0, step=1):
        values = []
        width -= padding * 2
        height -= padding * 2
        hull = self.getConvexHull()
        for angle in range(0, 180, step):
            d = hull.getRotated(angle)
            scale = min(width / d.bounds.width, height / d.bounds.height)
            values.append((scale, angle))
        scale, angle = max(values)
        return self.getRotated(angle).getScaled(scale, scale).getCentered(width, height)


    def getSVGElementString(self):
        path_str = ''

        if len(self.path) == 0:
            return path_str

        # for points in self.path:
        #     path_str += 'M' + ' L'.join('{0} {1}'.format(x,y) for x,y in points)

        if self.isTransformed:
            for points in self.path:
                first = True
                for point in points:
                    p = transform(point, translate=self.translate, scale=self.scale, rotate=self.rotate)
                    if first:
                        first = False
                        path_str += 'M%0.1f %0.1f' % (p[0], p[1])
                    else:
                        path_str += 'L%0.1f %0.1f' % (p[0], p[1])
        else:
            for points in self.path:
                path_str += 'M' + ' L'.join('{0} {1}'.format(x,y) for x,y in points)

        svg_str = '<path '
        if self.id != None:
            svg_str += 'id="' + self.id + '" '
        svg_str += 'd="' + path_str + '" '

        if self.color != None:
            svg_str += f'fill="none" stroke="{self.color}" stroke-width="{self.head_width}" '
        else:
            svg_str += f'fill="none" stroke-width="{self.head_width}" '

        svg_str += '/>\n'
        
        return svg_str


    def getGCodeString(self, **kwargs):
        head_up_height = kwargs.pop('head_up_height', 3)
        head_down_height = kwargs.pop('head_down_height', -0.5)
        head_up_speed = kwargs.pop('head_up_speed', 800)
        head_down_speed = kwargs.pop('head_down_speed', 500)
        move_speed = kwargs.pop('move_speed', 300)
        # bed_max_x = kwargs.pop('bed_max_x', 200)
        # bed_max_y = kwargs.pop('bed_max_y', 200)


        transformed = self.isTransformed
        gcode_str = ''
        for points in self.path:
            gcode_str += "G0 Z%0.1f F" % (head_up_height) + str(head_up_speed) + "\n"
            
            p = points[0][:]
            if transformed:
                p = transform(points[0], translate=self.translate, scale=self.scale, rotate=self.rotate)
                gcode_str += "G0 X%0.1f Y%0.1f\n" % (p[0], p[1])
            else:
                gcode_str += "G0 X%0.1f Y%0.1f\n" % (p[0], p[1])

            gcode_str += "G1 Z%0.1f F" % (head_down_height) + str(head_down_speed) +"\n"

            first = True
            for point in points[1:]:
                # if x > 0 and x < bed_max_x and y > 0 and y < bed_max_y:  
                p = point[:]
                if transformed:
                    p = transform(p, translate=self.translate, scale=self.scale, rotate=self.rotate)
                gcode_str += "G1 X%0.1f Y%0.1f" % (p[0], p[1])

                if first:
                    gcode_str += " F" + str(move_speed)
                    first = False
                gcode_str += '\n'

        gcode_str += "G0 Z%0.1f\n" % (head_up_height)
        return  gcode_str

    def add_coords(self, coords, color=None, head_width=None, close=True):
        """
        Add a raw coordinate ring to the path without instantiating a Polyline object.
        coords: iterable of (x,y) pairs or numpy array
        color/head_width/close: optional metadata
        """
        # lazy init storage for lightweight rings (keeps memory smaller than full Polyline objects)
        if not hasattr(self, '_rings'):
            self._rings = []
        # normalize coords to a plain Python list (fast) - avoid creating other objects
        if hasattr(coords, 'tolist'):
            pts = coords.tolist()
        else:
            pts = list(coords)

        # store lightweight metadata for later use if needed
        self._rings.append({
            "points": pts,
            "color": color if color is not None else getattr(self, "color", None),
            "head_width": head_width if head_width is not None else getattr(self, "head_width", None),
            "close": close
        })

        # Also append to the canonical storage used by existing Path consumers
        # so methods like getSimplify/getSorted/getJoined see the new ring.
        # Keep it as a plain list of points to remain compatible.
        self.path.append(pts)

        return self

