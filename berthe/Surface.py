#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from .Group import *
from .Image import *
# from .Pattern import *
# from .Polyline import Polyline

from .tools import dom2dict

class Surface(Group):
    def __init__(self, size = 'A3', **kwargs):
        Group.__init__(self, **kwargs)
        self.id = 'Body'

        if size == 'A4':
            self.width = 210.0
            self.height = 297.0
        elif size == 'A4_landscape':
            self.width = 297.0
            self.height = 210.0
        elif size == 'A3':
            self.width = 297.0
            self.height = 420.0
        elif size == 'A3_landscape':
            self.width = 420.0
            self.height = 297.0
        elif size == 'V2':
            self.width = 218.0
            self.height = 300.0
        elif size == 'V2_landscape':
            self.width = 300.0
            self.height = 218.0
        elif size == 'V3':
            self.width = 297.0
            self.height = 430.0
        elif size == 'V3_landscape':
            self.width = 430.0
            self.height = 297.0
        elif size == '12in x 16in':
            self.width = 304.8
            self.height = 406.4
        elif size == '16in x 12in':
            self.width = 406.4
            self.height = 304.8
        elif isinstance(size, tuple) or isinstance(size, list):
            if len(size) == 2:
                self.width = size[0]
                self.height = size[1]
        else:
            self.width = float(size)
            self.height = float(size)

    @property
    def size(self):
        return [self.width, self.height]


    @property
    def center(self):
        return [self.width * 0.5, self.height * 0.5]
        

    def fromSVG(self, filename: str) -> None:
        # TODO:
        #  - Add CubicBezier, QuadraticBezier support
        #  - Resolve nested and element transformations
        #  - Parse correctly the SVG

        from xml.dom.minidom import parse
        doc = parse(filename)
        doc.nodeValue

        svg = doc.getElementsByTagName('svg')[0]
        svg_att = dom2dict(svg) 
        viewBox = svg_att['viewBox'].split()
        width = float(viewBox[2])
        height = float(viewBox[3])

        scale = 'scale(' + str((1.0/width) * self.width) + ',' + str((1.0/height) * self.height) + ')'
        stroke_width = max(width/self.width, height/self.height ) * 0.2

        root_group = self.group( filename )
        root_group.parseSVGNode( svg )


    def toSVG(self, filename: str, **kwargs ) -> None:
        scale = kwargs.pop('scale', 1.0)
        margin = kwargs.pop('margin', [0.0, 0.0])
        unit = kwargs.pop('unit', 'mm')
        optimize = kwargs.pop('optimize', False)
        flip_x = kwargs.pop('flip_x', False)
        flip_y = kwargs.pop('flip_y', False)

        svg_str = '<?xml version="1.0" encoding="utf-8" ?>\n<svg '
        svg_str += 'width="'+ str(self.width) + unit + '" '
        svg_str += 'height="' + str(self.height) + unit + '" '
        svg_str += 'viewBox="0,0,'+ str(self.width * scale) + ',' + str(self.height * scale) + '" '
        svg_str += 'baseProfile="tiny" version="1.2" xmlns="http://www.w3.org/2000/svg" xmlns:ev="http://www.w3.org/2001/xml-events" xmlns:xlink="http://www.w3.org/1999/xlink" ><defs/>'

        for el in self.elements:
            if isinstance(el, Group ):
                grp = el

                if margin[0] != 0.0 or margin[1] != 0.0: 
                    grp = grp.getTranslated(margin[0], margin[1])

                if flip_x:
                    def flip_onX(x, y):
                        return (self.width - x, y)
                    grp = grp.getTransformed(flip_onX)

                if flip_y:
                    def flip_onY(x, y):
                        return (x, self.height - y)
                    grp = grp.getTransformed(flip_onY)

                svg_str += grp.getSVGElementString()
            else:
                path = el.getPath()

                if optimize:
                    path = path.getSimplify().getSorted()

                if margin[0] != 0.0 or margin[1] != 0.0: 
                    path = path.getTranslated(margin[0], margin[1])

                if flip_x:
                    def flip_onX(x, y):
                        return (self.width - x, y)
                    path = path.getTransformed(flip_onX)

                if flip_y:
                    def flip_onY(x, y):
                        return (x, self.height - y)
                    path = path.getTransformed(flip_onY)

                svg_str += path.getSVGElementString()

        svg_str += '</svg>'

        with open(filename, "w") as file:
            file.write(svg_str)


    def toGCODE(self, filename: str, **kwargs ) -> None:
        flip_x = kwargs.pop('flip_x', False)
        flip_y = kwargs.pop('flip_y', True)
        auto_center = kwargs.pop('auto_center', True)
        depth = kwargs.pop('depth', -1.0)
        depth_step = kwargs.pop('depth_step', -0.2)
        head_width = kwargs.pop('head_width', self.head_width)
        # head_width_at_depth = kwargs.pop('head_width_at_depth', head_width)

        def getGCODEHeader(self, **kwargs):
            return 'M3\n'

        def getGCODEFooter(self, **kwargs):
            gcode_str = "G0 Z10\n"
            gcode_str += "G0 X0 Y0\n"
            gcode_str += "M5\n"
            return gcode_str

        gcode_str = getGCODEHeader()

        # Initial shallow and precise pass
        path = self.getPath().getSimplify().getSorted()

        if auto_center:
            path = path.getCentered(self.width, self.height)
            path = path.getTranslated(-self.width*0.5, -self.height*0.5)

        if flip_x:
            def flip_onX(x, y):
                return (-x, y)
            path = path.getTransformed(flip_onX)

        if flip_y:
            def flip_onY(x, y):
                return (x, -y)
            path = path.getTransformed(flip_onY)

        z = depth_step
        while z > depth:
            gcode_str += path.getGCodeString(head_down_height=z, **kwargs)
            z += depth_step

        gcode_str += getGCODEFooter()

        with open(filename, "w") as file:
            file.write(gcode_str)


    def toPNG(self, filename: str, **kwargs) -> None:
        try:
            import cairocffi as cairo
        except ImportError:
            cairo = None

        if cairo is None:
            raise Exception('Surface.toPNG() requires cairo')

        sort = kwargs.pop('sort', False)
        flip_x = kwargs.pop('flip_x', False)
        flip_y = kwargs.pop('flip_y', False)
        scale = kwargs.pop('scale', 20)
        margin = kwargs.pop('margin', [0, 0])
        line_width = kwargs.pop('line_width', 20.0/scale)
        show_bounds = kwargs.pop('show_bounds', False)
        debug = kwargs.pop('debug', False)
        optimize = kwargs.pop('optimize', False)

        margin *= scale
        width = int(scale * self.width)
        height = int(scale * self.height)
        surface = cairo.ImageSurface(cairo.FORMAT_RGB24, width, height)
        dc = cairo.Context(surface)
        dc.set_line_cap(cairo.LINE_CAP_ROUND)
        dc.set_line_join(cairo.LINE_JOIN_ROUND)
        dc.scale(scale, scale)
        dc.set_source_rgb(1, 1, 1)
        dc.paint()
        if show_bounds:
            dc.set_source_rgb(0.5, 0.5, 0.5)
            dc.set_line_width(1 / scale)
            dc.rectangle(0, 0, self.width ,self.height)
            dc.stroke()

        def draw_path(dc, path):
            if optimize:
                path = path.getSimplify()
                
            if sort:
                path = path.getSorted()
                
            if margin[0] != 0.0 or margin[1] != 0.0: 
                path = path.getTranslated(margin[0], margin[1])

            if flip_x:
                def flip_onX(x, y):
                    return (self.width - x, y)
                path = path.getTransformed(flip_onX)

            if flip_y:
                def flip_onY(x, y):
                    return (x, self.height - y)
                path = path.getTransformed(flip_onY)        

            lastPoint = [0.0, 0.0]
            rgb = (0.0, 0.0, 0.0)
            # convert SVG color to RGB
            if path.color is not None:
                svg_color =  path.color
                if svg_color.startswith('#') and (len(svg_color) == 7 or len(svg_color) == 4):
                    if len(svg_color) == 7:
                        r = int(svg_color[1:3], 16) / 255.0
                        g = int(svg_color[3:5], 16) / 255.0
                        b = int(svg_color[5:7], 16) / 255.0
                    else:
                        r = int(svg_color[1]*2, 16) / 255.0
                        g = int(svg_color[2]*2, 16) / 255.0
                        b = int(svg_color[3]*2, 16) / 255.0
                    rgb = (r, g, b)
                elif svg_color.startswith('rgb'):
                    svg_color = svg_color.replace('rgb(', '').replace(')', '')
                    parts = svg_color.split(',')
                    if len(parts) == 3:
                        r = int(parts[0].strip()) / 255.0
                        g = int(parts[1].strip()) / 255.0
                        b = int(parts[2].strip()) / 255.0
                        rgb = (r, g, b)
            
            for points in path:
                if debug:
                    dc.set_line_width(1 / scale)
                    dc.set_source_rgb(0.5, 0.0, 0.0)
                    dc.move_to(*lastPoint)
                    dc.line_to(*points[0])
                    dc.stroke()
                else:
                    dc.move_to(*points[0])

                dc.set_source_rgb(rgb[0], rgb[1], rgb[2])
                dc.set_line_width(line_width * path.stroke_width)
                for x, y in points:    
                    dc.line_to(x, y)
                    lastPoint = [x, y]
                dc.stroke()

        for el in self.elements:
            if isinstance(el, Group ):
                grp = el
                for el in grp.elements:
                    if isinstance(el, Path ):
                        draw_path(dc, el)
                    else:
                        draw_path(dc, el.getPath())
            else:
                path = el.getPath()
                draw_path(dc, path)

        surface.write_to_png(filename)


    # def fromMesh(self, mesh, camera_matrix, projection="perspective", **kwargs)
    #     try:
    #         from Meshes import Mesh
    #     except ImportError:
    #         Mesh = None

    #     if Mesh is None:
    #         raise Exception('Surface.fromMesh() requires Meshes')


    def toMesh(self, **kwargs):
        try:
            from Meshes import Mesh
        except ImportError:
            Mesh = None

        if Mesh is None:
            raise Exception('Surface.toMesh() requires Meshes')

        optimize = kwargs.pop('optimize', False)
        flip_x = kwargs.pop('flip_x', False)
        flip_y = kwargs.pop('flip_y', True)
        auto_center = kwargs.pop('auto_center', True)
        color = kwargs.pop('color', None)
        depth = kwargs.pop('depth', 0.0)

        mesh = Mesh("Mesh")

        path = self.getPath()

        if optimize:
            path = path.getSimplify().getSorted()

        if auto_center:
            path = path.getCentered(self.width, self.height)
            path = path.getTranslated(-self.width*0.5, -self.height*0.5)

        if flip_x:
            def flip_onX(x, y):
                return (-x, y)
            path = path.getTransformed(flip_onX)

        if flip_y:
            def flip_onY(x, y):
                return (x, -y)
            path = path.getTransformed(flip_onY)

        lastIndex = 0
        for points in path:
            section = 0
            for x, y in points:
                mesh.addVertex( [x, y, depth] )

                if section > 0:
                    mesh.addEdge(lastIndex-1, lastIndex)

                lastIndex += 1
                section +=1

        return mesh

    def toBlenderCurve(self, **kwargs):
        try:
            import bpy
        except ImportError:
            bpy = None

        if bpy is None:
            raise Exception('Surface.toBlenderCurve() requires Blender enviroment')

        optimize = kwargs.pop('optimize', False)
        flip_x = kwargs.pop('flip_x', False)
        flip_y = kwargs.pop('flip_y', True)
        auto_center = kwargs.pop('auto_center', True)
        color = kwargs.pop('color', None)
        depth = kwargs.pop('depth', 0.0)
        type = kwargs.pop('type', 'POLY')

        path = self.getPath()

        if optimize:
            path = path.getSimplify().getSorted()

        if auto_center:
            path = path.getCentered(self.width, self.height)
            path = path.getTranslated(-self.width*0.5, -self.height*0.5)

        if flip_x:
            def flip_onX(x, y):
                return (-x, y)
            path = path.getTransformed(flip_onX)

        if flip_y:
            def flip_onY(x, y):
                return (x, -y)
            path = path.getTransformed(flip_onY)

        curvedata = bpy.data.curves.new(name="path", type='CURVE')  
        curvedata.dimensions = '3D'  
    
        objectdata = bpy.data.objects.new("Surface", curvedata)  
        objectdata.location = (0,0,0)
    
        scene = bpy.context.scene   
        scene.collection.objects.link(objectdata)
        
        for points in path:
            polyline = curvedata.splines.new(type)  # POLY | NURBS
            polyline.points.add(len(points)-1)  
            for num in range(len(points)):
                coord = [0.0, 0.0, 0.0, 1.0]

                for i in range(min(len(points[num]), 4)):
                    coord[i] = points[num][i]
                
                polyline.points[num].co = (coord[0], coord[1], coord[2], coord[3])
    
            polyline.order_u = len(polyline.points)-1
            polyline.use_endpoint_u = True



        