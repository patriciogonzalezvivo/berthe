#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from Surface import Surface

paper = Surface()

paper.circle((paper.width*0.5, paper.height*0.5), paper.width*0.5 )
paper.rect((paper.width*0.5, paper.height*0.5), (paper.width, paper.height) )
paper.text('hello world', (paper.width*0.5, paper.height*0.5) )

paper.toSVG('hello_world.svg')