#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Display all sashiko patterns in a grid, one tile per pattern, with a label.

Output: sashiko_patterns.svg
"""

import sys
import os
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from berthe import Surface, Pattern, Group, Text
from berthe.pattern_generators import SASHIKO_PATTERNS, sashiko_pattern

# ── Layout ────────────────────────────────────────────────────────────────────
TILE   = 40       # mm per tile (square)
COLS   = 6        # tiles per row
PAD    = 4        # mm gap between tiles
LABEL  = 6        # mm reserved below each tile for the name
N      = 8        # pattern density (cells across)

names  = list(SASHIKO_PATTERNS.keys())
rows   = (len(names) + COLS - 1) // COLS
step   = TILE + PAD
width  = COLS * step + PAD
height = rows * (step + LABEL) + PAD

axi = Surface(width=width, height=height)

for i, name in enumerate(names):
    col = i % COLS
    row = i // COLS

    ox = PAD + col * step
    oy = PAD + row * (step + LABEL)

    # Generate pattern in [0,1]², mapped to TILE×TILE, translated to (ox, oy)
    x, y = sashiko_pattern(name, n=N)
    pat = Pattern((x, y), width=TILE, height=TILE, translate=np.array([ox, oy]))
    path = pat.getPath()

    grp = Group(name=f'pat_{name}')
    grp.add(path)

    # Label centred below the tile
    lx = ox + TILE / 2.0
    ly = oy + TILE + LABEL * 0.65
    grp.add( Text(name, (lx, ly), scale=0.07, align='center') )

    axi.add(grp)

axi.toSVG('sashiko_patterns.svg')
print(f"Saved sashiko_patterns.svg  ({len(names)} patterns, {COLS}×{rows} grid)")
