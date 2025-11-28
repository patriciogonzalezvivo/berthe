#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from .Element import Element

from .Line import Line
from .Arc import Arc
from .Circle import Circle
from .Rectangle import Rectangle
from .Hexagon import Hexagon
from .Polyline import Polyline
from .Polygon import Polygon
from .Text import Text
from .Path import Path
from .Pattern import Pattern

from .tools import dom2dict, parse_transform

class Group(Element):
    def __init__( self, id="Untitled", **kwargs ):
        Element.__init__(self, **kwargs);

        self.id = id
        self.elements = []
        self.subgroups = { } 

    def __iter__(self):
        self._index = 0
        return self


    def __next__(self):
        if self._index < len(self.elements):
            result = self[ self._index ]
            self._index += 1
            return result
        else:
            raise StopIteration


    def next(self):
        return self.__next__()


    def __getitem__(self, index):
        if type(index) is int:
            return self.elements[index]
        else:
            return None


    def add(self, element ):
        element.parent = self
        self.elements.append(element)
        if isinstance(element, Group):
            self.subgroups[element.id] = element
        return element


    def line(self, start_pos, end_pos, **kwargs):
        return self.add( Line(start_pos, end_pos, **kwargs) )


    def arc(self, start_pos, end_pos, radius, **kwargs):
        return self.add( Arc(start_pos, end_pos, radius, **kwargs) )


    def circle(self, center, radius, **kwargs):
        return self.add( Circle(center, radius, **kwargs) )


    def rect(self, center, size, **kwargs):
        return self.add( Rectangle(center, size, **kwargs) )


    def hex(self, center, radius, **kwargs):
        return self.add( Hexagon( center, radius, **kwargs) )


    def polyline(self, points, **kwargs):
        return self.add( Polyline(points, **kwargs) )


    def polygon(self, points, **kwargs):
        return self.add( Polygon(points, **kwargs) )


    def path(self, path, **kwargs):
        return self.add( Path(path, **kwargs) )


    def text(self, text, center, **kwargs):
        return self.add( Text(text, center, **kwargs) )


    def pattern(self, pattern, **kwargs):
        return self.add( Pattern(pattern, **kwargs) )


    def group(self, group_id, **kwargs):
        g = Group(group_id, **kwargs)
        self.subgroups[group_id] = g
        return self.add( g )


    def getTransformed(self, func):
        new_group = Group(self.id, fill=self.fill, stroke_width=self.stroke_width, head_width=self.head_width, color=self.color)

        for el in self.elements:
            if isinstance(el, Path) or isinstance(el, Group):
                new_el = el.getTransformed(func)
            else:
                new_el = el.getPath().getTransformed(func)
            new_group.add( new_el )

        return new_group


    def getPoints(self):
        points = []
        for el in self.elements:
            points.extend( el.getPoints() )
        return points


    # def getPath(self, **kwargs):
    #     import copy

    #     path = Path(color=self.color)
    #     for el in self.elements:
    #         if isinstance(el, Path ):
    #             path.add( el )
    #         else:
    #             if len(kwargs.items()) > 0:
    #                 tmp = copy.copy(el)
    #                 for key in kwargs:
    #                     tmp.__dict__[key] = kwargs[key]
    #                     print(key, tmp.__dict__[key])
    #                 path.add( tmp.getPath() )
    #             else:
    #                 # Make sure to end the previous subpath
    #                 path.add( el.getPath() )
    #     return path


    def parseSVGNode(self, node):
        att = dom2dict(node)
            
        self.id = att.pop('id', self.id)
        self.fill = att.pop('fill', self.fill)
        self.stroke_width = att.pop('stroke_width', self.stroke_width)
            
        for el in node.childNodes:
            if el.nodeName == "metadata":
                continue

            elif el.nodeName == "#text":
                continue

            elif el.nodeName == "g":
                el_att = dom2dict(el)

                sub_group = Group()
                sub_group.parseSVGNode( el )

                if 'transform' in el_att:
                    sub_group = parse_transform(sub_group, el_att['transform'])

                self.add(sub_group)


            elif el.nodeName == "polyline":
                el_att = dom2dict(el)

                polyline = Polyline(el_att['points'], 
                                id=el_att.pop('id', self.id + "_sub"), 
                                fill=el_att.pop('fill', self.fill), 
                                stroke_width=el_att.pop('stroke-width', self.stroke_width) )

                if 'transform' in el_att:
                    polyline = parse_transform(polyline, el_att['transform'])

                self.add( polyline )


            elif el.nodeName == "polygon":
                el_att = dom2dict(el)

                polygon = Polygon( el_att['points'], 
                                id=el_att.pop('id', self.id + "_sub"), 
                                fill=el_att.pop('fill', self.fill), 
                                stroke_width=el_att.pop('stroke-width', self.stroke_width) )

                if 'transform' in el_att:
                    polygon = parse_transform(polygon, el_att['transform'])

                self.add( polygon )


            elif el.nodeName == "path":
                el_att = dom2dict(el)

                path = Path(el_att['d'], 
                            id=el_att.pop('id', self.id + "_sub"), 
                            fill=el_att.pop('fill', self.fill), 
                            stroke_width=el_att.pop('stroke-width', self.stroke_width) )

                if 'transform' in el_att:
                    path = parse_transform(path, el_att['transform'])

                self.add( path )

            else:
                print(el.nodeName + " is no to be implemented")


    def getSVGElementString(self):
        svg_str = '<g '
        if self.id != None:
            svg_str += f'id="{self.id}" '
        svg_str += f'fill="none" stroke="{self.color}" stroke-width="{self.head_width}">'

        for el in self.elements:
            svg_str += el.getSVGElementString()

        svg_str += '</g>'
        
        return svg_str
        

