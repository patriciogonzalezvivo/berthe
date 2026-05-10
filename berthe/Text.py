from .Element import Element
from .Polyline import Polyline
from .Path import Path
from .Bbox import Bbox
from .hershey_fonts import *
from .tools import transform
import math


def _offset_stroke(points, offset):
    """Offset a polyline's points perpendicularly by `offset` units.
    Works correctly for 2-point strokes (which Hershey fonts mostly are).
    For each interior point, averages the normals of adjacent segments."""
    n = len(points)
    if n < 2 or abs(offset) < 1e-9:
        return points

    # compute per-segment normals
    seg_normals = []
    for i in range(n - 1):
        dx = points[i+1][0] - points[i][0]
        dy = points[i+1][1] - points[i][1]
        length = math.sqrt(dx*dx + dy*dy)
        if length < 1e-9:
            seg_normals.append((0.0, 0.0))
        else:
            seg_normals.append((-dy / length, dx / length))

    # assign per-point normals (average adjacent segments)
    pt_normals = []
    for i in range(n):
        if i == 0:
            nx, ny = seg_normals[0]
        elif i == n - 1:
            nx, ny = seg_normals[-1]
        else:
            ax, ay = seg_normals[i-1]
            bx, by = seg_normals[i]
            nx, ny = ax + bx, ay + by
            mag = math.sqrt(nx*nx + ny*ny)
            if mag > 1e-9:
                nx, ny = nx / mag, ny / mag
        pt_normals.append((nx, ny))

    return [(p[0] + nx * offset, p[1] + ny * offset)
            for p, (nx, ny) in zip(points, pt_normals)]

class Text(Element):
    def __init__( self, text, pos, **kwargs ):
        Element.__init__(self, **kwargs);
        self.text = str(text)
        self.font =  kwargs.pop('font', FUTURAL)
        self.letter_spacing = kwargs.pop('letter_spacing', kwargs.pop('spacing', 0))
        self.extra =  kwargs.pop('extra', 0)
        self.auto_flip = kwargs.pop('auto_flip', False )
        self.align = kwargs.pop('align', 'center');
        self.weight = kwargs.pop('weight', 100)
        if self.align == 'center':
            self._center = pos
        elif self.align == 'left':
            self._center = (pos[0] + self.length / 2.0, pos[1])
        elif self.align == 'right':
            self._center = (pos[0] - self.length / 2.0, pos[1])


    @property
    def center(self):
        return self._center + self.translate


    @property
    def length(self):
        x = 0
        for ch in self.text:
            index = ord(ch) - 32
            if index < 0 or index >= 96:
                x += self.letter_spacing
                continue

            lt, rt, coords = self.font[index]
            x += rt - lt + self.letter_spacing

        if isinstance(self.scale, tuple) or isinstance(self.scale, list):
            x *= self.scale[0]
        else:
            x *= self.scale

        return x


    def getPolylines(self, **kwargs):
        rotate = kwargs.pop('rotate', self.rotate )
        stroke_width = kwargs.pop('stroke_width', self.stroke_width )

        if self.auto_flip:
            if rotate >= 90 and rotate < 270:
                rotate += 180
            elif rotate < -90 and rotate > -270:
                rotate += 180

        # Based on hershey implementation by Michael Fogleman https://github.com/fogleman/axi/blob/master/axi/hershey.py
        result = []

        bbox = Bbox()
        x = 0
        for ch in self.text:
            index = ord(ch) - 32
            if index < 0 or index >= 96:
                x += self.letter_spacing
                continue

            lt, rt, coords = self.font[index]
            for path in coords:
                path = [ (x + i - lt, j) for i, j in path]
                if path:
                    line = Polyline(path)
                    bbox.join( line.bounds )
                    result.append( line )
            x += rt - lt + self.letter_spacing
            if index == 0:
                x += self.extra

        toCenter = transform(bbox.center, rotate=rotate, scale=self.scale)
        translate = [ self.center[0] - toCenter[0], self.center[1] - toCenter[1] ]

        # weight=100 → 1 pass at offset 0.
        # spread = how far out from centre (in mm) each side.
        # Passes are evenly spaced by head_width, symmetric around 0.
        # Intermediate weights (150, 220 …) produce the right fractional spread.
        spread = (self.weight / 100.0 - 1.0) * self.head_width
        if spread <= 1e-9:
            offsets = [0.0]
        else:
            offsets = []
            o = -spread
            while o <= spread + 1e-9:
                offsets.append(o)
                o += self.head_width

        polys = []
        for line in result:
            points = [ transform(p, translate=translate, rotate=rotate, scale=self.scale) for p in line.points ]
            for off in offsets:
                pts = _offset_stroke(points, off)
                polys.append( Polyline(pts) )

        return polys


    def getStrokePath(self, **kwargs):
        polys = self.getPolylines(**kwargs)
        return Path([ poly.getPoints() for poly in polys ], color=self.color)


    def getPoints(self):
        points = []
        polys = self.getPolylines( stroke_width=self.stroke_width )

        for poly in polys:
            points.extend( poly.getPoints() )

        return points


    def _toShapelyGeom(self):
        try:
            from shapely import geometry
        except ImportError:
            geometry = None

        if geometry is None:
            raise Exception('To convert a Text to a Shapely MultiPolygon requires shapely. Try: pip install shapely')

        polys = self.getPolylines( stroke_width=self.stroke_width )
        polygons = []
        for poly in polys:
            polygons.append( poly._toShapelyLineString() )

        return geometry.MultiPolygons( polygons )


    def getBuffer(self, offset):
        if offset <= 0.0:
            return copy.copy(self)

        from .Polygon import Polygon

        polys = self.getPolylines( stroke_width=self.stroke_width )
        polygons = []
        for poly in polys:
            polygons.append( poly._toShapelyLineString().buffer(offset) )

        from shapely.ops import cascaded_union

        buf = cascaded_union(polygons)
        path = Path()
        
        try:
            for ring in buf:
                polygon = Polygon( list(ring.exterior.coords) )
                for i in ring.interiors:
                    polygon.addHole( list(i.coords) )
                path.add( polygon )

        # Not a Multipolygon. Must be a Polygon
        except TypeError:
            polygon = Polygon( list(buf.exterior.coords) )
            
            for i in buf.interiors:
                polygon.addHole( list(i.coords) )

            path.add( polygon )
            
        return path
        




    