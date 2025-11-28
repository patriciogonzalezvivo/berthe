from .Element import Element
from .Polyline import Polyline
from .Path import Path
from .Bbox import Bbox
from .hershey_fonts import *
from .tools import transform

class Text(Element):
    def __init__( self, text, center, **kwargs ):
        Element.__init__(self, **kwargs);
        self.text = str(text)
        self._center = center

        self.font =  kwargs.pop('font', FUTURAL)
        self.spacing =  kwargs.pop('spacing', 0)
        self.extra =  kwargs.pop('extra', 0)
        self.auto_flip = kwargs.pop('auto_flip', False )


    @property
    def center(self):
        return self._center + self.translate


    @property
    def length(self):
        x = 0
        for ch in self.text:
            index = ord(ch) - 32
            if index < 0 or index >= 96:
                x += self.spacing
                continue

            lt, rt, coords = self.font[index]
            x += rt - lt + self.spacing

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
                x += self.spacing
                continue

            lt, rt, coords = self.font[index]
            for path in coords:
                path = [ (x + i - lt, j) for i, j in path]
                if path:
                    line = Polyline(path)
                    bbox.join( line.bounds )
                    result.append( line )
            x += rt - lt + self.spacing
            if index == 0:
                x += self.extra


        toCenter = transform(bbox.center, rotate=rotate, scale=self.scale)
        translate = [ self.center[0] - toCenter[0], self.center[1] - toCenter[1] ]

        polys = []
        for line in result:
            points = []
            for point in line.points:
                points.append( transform(point, translate=translate, rotate=rotate, scale=self.scale) )
            polys.append( Polyline(points, stroke_width=stroke_width) )

        return polys


    def getPoints(self):
        points = []
        polys = self.getPolylines( stroke_width=self.head_width )

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

        polys = self.getPolylines( stroke_width=self.head_width )
        polygons = []
        for poly in polys:
            polygons.append( poly._toShapelyLineString() )

        return geometry.MultiPolygons( polygons )


    def getBuffer(self, offset):
        if offset <= 0.0:
            return copy.copy(self)

        from .Polygon import Polygon

        polys = self.getPolylines( stroke_width=self.head_width )
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
        

    def getStrokePath(self, **kwargs):
        path = Path()
        polys = self.getPolylines(**kwargs)

        for poly in polys:
            path.add( poly.getStrokePath(**kwargs) )

        return path


    