#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import numpy as np


# This code is adapted from Paul Butler great Surface Projection tutorial
# https://bitaesthetics.com/posts/surface-projection.html and PenKit https://github.com/paulgb/penkit/

def stripes_pattern(num_lines=10, resolution=50, offset=0, zigzag=False):
    x_min = 0.0
    x_max = 1.0
    y_min = 0.0
    y_max = 1.0
    
    resolution = int(resolution)
    resolution_unit = 1.0 / resolution
    resolution_offset = offset * resolution_unit
    x_min = x_min + resolution_offset
    x_max = (x_max-resolution_unit) + resolution_offset

    lines_unit = 1.0 / num_lines
    lines_offset = offset * lines_unit
    y_min = y_min + lines_offset
    y_max = (y_max-lines_unit) + lines_offset

    # np.meshgrid is a handy way to generate a grid of points. It
    # returns a pair of matrices, which we will flatten into arrays.
    # For the x-coordinates, we put a nan value at the end so that when
    # we flatten them there is a separater between each horizontal line.
    x, y = np.meshgrid(
        np.hstack( [np.linspace(x_min, x_max, resolution), np.nan] ),
        np.linspace(y_min, y_max, num_lines),
    )

    if zigzag:
        line = 0
        for each in x:
            if line%2 == 1:
                # each = np.flipud(each)
                x[line] = np.flipud(each)
            line += 1
    
    # For coordinates where the x value is nan, set the y value to nan
    # as well. nan coordinates represent breaks in the path, indicating
    # here that the pen should be raised between each horizontal line.
    y[np.isnan(x)] = np.nan
    return x.flatten(), y.flatten()


def grid_pattern(num_h_lines=10, num_v_lines=10, resolution=50):
    x_h, y_h = stripes_pattern(num_h_lines, resolution)
    y_v, x_v = stripes_pattern(num_v_lines, resolution)
    return np.concatenate([x_h, x_v]), np.concatenate([y_h, y_v])


def dashes_pattern(dash_x, dash_y, num_lines=10, resolution=10):
    x_min = 0.0
    x_max = 1.0
    y_min = 0.0
    y_max = 1.0

    resolution = int(resolution)
    num_lines = int(num_lines)

    offsets_x = np.tile(dash_x, resolution)
    offsets_y = np.tile(dash_y, num_lines)

    x, y = np.meshgrid(
        np.linspace(x_min, x_max, dash_x.size * resolution) + offsets_x,
        np.linspace(y_min, y_max, dash_y.size * num_lines) + offsets_y, 
    )

    return x.flatten(), y.flatten()


def crosses_pattern(resolution=10):
    resolution = int(resolution)
    offset = (1.0/resolution)

    dash_x = np.array([ offset*0.5, 0.0, -offset*0.5, np.nan ])
    dash_y = np.array([ np.nan, 0.0, np.nan, np.nan ])

    x_h, y_h = dashes_pattern(dash_x, dash_y, resolution, resolution)  
    y_v, x_v = dashes_pattern(dash_x, dash_y, resolution, resolution)
    return np.concatenate([x_h, x_v]), np.concatenate([y_h, y_v])


def spiral_pattern(spirals=6.0, ccw=False, offset=0.0, resolution=1000):
    """Makes a pattern consisting of a spiral from the origin.
    Args:
        spirals (float): the number of rotations to make
        ccw (bool): make spirals counter-clockwise (default is clockwise)
        offset (float): if non-zero, spirals start offset by this amount
        resolution (int): number of midpoints along the spiral
    Returns:
        A pattern.
    """
    dist = np.sqrt(np.linspace(0., 1., resolution))
    if ccw:
        direction = 1.
    else:
        direction = -1.
    angle = dist * spirals * np.pi * 2. * direction
    spiral_pattern = (
        (np.cos(angle) * dist / 2.) + 0.5,
        (np.sin(angle) * dist / 2.) + 0.5
    )
    return spiral_pattern


def hex_pattern(grid_size = 10, resolution=50):
    """Makes a pattern consisting on a grid of hexagons.
    Args:
        grid_size (int): the number of hexagons along each dimension of the grid
        resolution (int): the number of midpoints along the line of each hexagon
    
    Returns:
        A pattern.
    """
    grid_x, grid_y = np.meshgrid(
        np.arange(grid_size),
        np.arange(grid_size)
    )
    ROOT_3_OVER_2 = np.sqrt(3) / 2
    ONE_HALF = 0.5
    
    grid_x = (grid_x * np.sqrt(3) + (grid_y % 2) * ROOT_3_OVER_2).flatten()
    grid_y = grid_y.flatten() * 1.5
    
    grid_points = grid_x.shape[0]
    
    x_offsets = np.interp(np.arange(4 * resolution),
        np.arange(4) * resolution, [
            ROOT_3_OVER_2,
            0.,
            -ROOT_3_OVER_2,
            -ROOT_3_OVER_2,
        ])
    y_offsets = np.interp(np.arange(4 * resolution),
        np.arange(4) * resolution, [
            -ONE_HALF,
            -1.,
            -ONE_HALF,
            ONE_HALF
        ])
    
    tmx = 4 * resolution
    x_t = np.tile(grid_x, (tmx, 1)) + x_offsets.reshape((tmx, 1))
    y_t = np.tile(grid_y, (tmx, 1)) + y_offsets.reshape((tmx, 1))
    
    x_t = np.vstack([x_t, np.tile(np.nan, (1, grid_x.size))])
    y_t = np.vstack([y_t, np.tile(np.nan, (1, grid_y.size))])

    return x_t.flatten('F'), y_t.flatten('F')


# ─────────────────────────────────────────────────────────────────────────────
# SASHIKO PATTERNS
# Traditional Japanese sashiko stitch patterns.
# Each function returns (x, y) numpy arrays in [0, 1]² (normalised tile space).
# ─────────────────────────────────────────────────────────────────────────────

def _sashiko_arc(cx, cy, r, t0=0.0, t1=2.0 * np.pi, steps=48):
    """Circular arc as (x, y) arrays with a trailing nan pen-up."""
    t = np.linspace(t0, t1, steps)
    return (np.append(cx + r * np.cos(t), np.nan),
            np.append(cy + r * np.sin(t), np.nan))


def _sashiko_seg(x0, y0, x1, y1):
    """Single line segment with trailing nan."""
    return np.array([x0, x1, np.nan]), np.array([y0, y1, np.nan])


def _sashiko_cat(*pairs):
    """Concatenate any number of (x, y) pairs into one."""
    return (np.concatenate([p[0] for p in pairs]),
            np.concatenate([p[1] for p in pairs]))


# Cohen-Sutherland clip constants
_CS_INSIDE = 0
_CS_LEFT   = 1
_CS_RIGHT  = 2
_CS_BOTTOM = 4
_CS_TOP    = 8


def _sashiko_outcode(x, y, xmin=0.0, xmax=1.0, ymin=0.0, ymax=1.0):
    code = _CS_INSIDE
    if x < xmin:
        code |= _CS_LEFT
    elif x > xmax:
        code |= _CS_RIGHT
    if y < ymin:
        code |= _CS_BOTTOM
    elif y > ymax:
        code |= _CS_TOP
    return code


def _sashiko_clip_segment(x0, y0, x1, y1, xmin=0.0, xmax=1.0, ymin=0.0, ymax=1.0):
    """Cohen-Sutherland line-clip. Returns clipped (x0,y0,x1,y1) or None."""
    code0 = _sashiko_outcode(x0, y0, xmin, xmax, ymin, ymax)
    code1 = _sashiko_outcode(x1, y1, xmin, xmax, ymin, ymax)
    while True:
        if not (code0 | code1):     # both inside
            return x0, y0, x1, y1
        if code0 & code1:           # both outside same region
            return None
        code_out = code0 if code0 else code1
        if code_out & _CS_TOP:
            x = x0 + (x1 - x0) * (ymax - y0) / (y1 - y0)
            y = ymax
        elif code_out & _CS_BOTTOM:
            x = x0 + (x1 - x0) * (ymin - y0) / (y1 - y0)
            y = ymin
        elif code_out & _CS_RIGHT:
            y = y0 + (y1 - y0) * (xmax - x0) / (x1 - x0)
            x = xmax
        else:  # LEFT
            y = y0 + (y1 - y0) * (xmin - x0) / (x1 - x0)
            x = xmin
        if code_out == code0:
            x0, y0 = x, y
            code0 = _sashiko_outcode(x0, y0, xmin, xmax, ymin, ymax)
        else:
            x1, y1 = x, y
            code1 = _sashiko_outcode(x1, y1, xmin, xmax, ymin, ymax)


def sashiko_clip_to_unit(x, y, xmin=0.0, xmax=1.0, ymin=0.0, ymax=1.0):
    """Clip a NaN-delimited polyline array to the rectangle [xmin,xmax]×[ymin,ymax].

    Each NaN-delimited run of points is walked as consecutive segments;
    each segment is Cohen-Sutherland clipped.  Clipped endpoints are inserted
    and pen-up NaNs are added between disconnected pieces.
    """
    out_x, out_y = [], []
    nan_mask = np.isnan(x) | np.isnan(y)
    indices = np.where(nan_mask)[0]
    prev = 0
    runs = []
    for idx in indices:
        if idx > prev:
            runs.append((prev, idx))
        prev = idx + 1
    if prev < len(x):
        runs.append((prev, len(x)))

    for start, end in runs:
        xs = x[start:end]
        ys = y[start:end]
        if len(xs) < 2:
            continue
        for i in range(len(xs) - 1):
            result = _sashiko_clip_segment(xs[i], ys[i], xs[i+1], ys[i+1], xmin, xmax, ymin, ymax)
            if result is None:
                continue
            cx0, cy0, cx1, cy1 = result
            if (out_x and not np.isnan(out_x[-1])
                    and abs(out_x[-1] - cx0) < 1e-9
                    and abs(out_y[-1] - cy0) < 1e-9):
                out_x.append(cx1)
                out_y.append(cy1)
            else:
                if out_x and not np.isnan(out_x[-1]):
                    out_x.append(np.nan)
                    out_y.append(np.nan)
                out_x += [cx0, cx1]
                out_y += [cy0, cy1]
        if out_x and not np.isnan(out_x[-1]):
            out_x.append(np.nan)
            out_y.append(np.nan)

    if not out_x:
        return np.array([np.nan]), np.array([np.nan])
    return np.array(out_x, dtype=np.float64), np.array(out_y, dtype=np.float64)


def pat_hito_mezashi(n=12, aspect=1.0):
    """Hitomezashi — offset running-stitch grid."""
    unit = 1.0 / n
    half = unit * 0.5
    segs = []
    n_rows = int(n * aspect) + 2
    for i in range(n_rows):
        y = i * unit
        if y > aspect + unit:
            break
        off = half if (i % 2 == 1) else 0.0
        x = off
        while x <= 1.0 + 1e-9:
            segs.append(_sashiko_seg(x, y, min(x + half, 1.0), y))
            x += unit
    for j in range(n + 1):
        x = j * unit
        off = half if (j % 2 == 1) else 0.0
        y = off
        while y <= aspect + 1e-9:
            segs.append(_sashiko_seg(x, y, x, min(y + half, aspect)))
            y += unit
    return _sashiko_cat(*segs)


def pat_shippo(n=5, r_ratio=0.58, steps=40, aspect=1.0):
    """Shippo-tsunagi — Seven Treasures overlapping circle grid."""
    unit = 1.0 / n
    r = unit * r_ratio
    n_rows = int(n * aspect) + 2
    segs = [
        _sashiko_arc(col * unit + unit * 0.5, row * unit + unit * 0.5, r, steps=steps)
        for row in range(-1, n_rows)
        for col in range(-1, n + 1)
    ]
    return _sashiko_cat(*segs)


def pat_asa_no_ha(n=4, aspect=1.0):
    """Asa-no-ha — hemp-leaf: hexagonal lattice with centre+midpoint spokes."""
    dx = 1.0 / n
    r  = dx * 2.0 / 3.0
    dy = r * np.sqrt(3)
    n_cols = n + 3
    n_rows = int(aspect / dy) + 3
    hex_a = np.radians([0, 60, 120, 180, 240, 300])
    vx = r * np.cos(hex_a)
    vy = r * np.sin(hex_a)
    segs = []
    for col in range(-1, n_cols):
        xc = col * dx
        y_off = dy * 0.5 if (col % 2 == 1) else 0.0
        for row in range(-1, n_rows):
            yc = row * dy + y_off
            for k in range(6):
                ax, ay = xc + vx[k], yc + vy[k]
                bx, by = xc + vx[(k+1) % 6], yc + vy[(k+1) % 6]
                mx, my = (ax + bx) * 0.5, (ay + by) * 0.5
                segs.append(_sashiko_seg(xc, yc, ax, ay))
                segs.append(_sashiko_seg(ax, ay, mx, my))
    return _sashiko_cat(*segs)


def pat_seigaiha(n=5, steps=36, aspect=1.0):
    """Seigaiha — overlapping arc scales (blue ocean waves)."""
    unit = 1.0 / n
    r = unit * 0.6
    row_h = unit * 0.75
    rows = int(aspect / row_h) + 2
    segs = []
    for row in range(-1, rows + 1):
        cy = row * row_h
        off = 0.5 * unit if (row % 2 == 1) else 0.0
        for col in range(-1, n + 2):
            cx = col * unit + off
            segs.append(_sashiko_arc(cx, cy, r, t0=np.pi, t1=2.0 * np.pi, steps=steps))
    return _sashiko_cat(*segs)


def pat_sayagata(n=4, aspect=1.0):
    """Sayagata — Buddhist fret / interlocked key pattern."""
    unit = 1.0 / n
    q = unit / 4.0
    n_rows = int(n * aspect) + 1
    segs = []
    for row in range(n_rows):
        for col in range(n):
            ox, oy = col * unit, row * unit
            segs += [
                _sashiko_seg(ox,        oy + q,    ox + 3*q, oy + q),
                _sashiko_seg(ox + 3*q,  oy + q,    ox + 3*q, oy + 3*q),
                _sashiko_seg(ox + 3*q,  oy + 3*q,  ox + unit, oy + 3*q),
                _sashiko_seg(ox + q,    oy,        ox + q,   oy + 2*q),
                _sashiko_seg(ox + q,    oy + 2*q,  ox + 2*q, oy + 2*q),
                _sashiko_seg(ox + 2*q,  oy + 2*q,  ox + 2*q, oy + unit),
            ]
    return _sashiko_cat(*segs)


def pat_nowaki(n=12, angle=45, aspect=1.0):
    """Nowaki — diagonal parallel field-grass lines."""
    n_lines = int(n * max(1.0, aspect) * 2) + 4
    angle_r = np.radians(angle)
    cos_a, sin_a = np.cos(angle_r), np.sin(angle_r)
    cx_c, cy_c = 0.5, aspect * 0.5
    segs = []
    for i in range(n_lines):
        t = i / (n_lines - 1)
        perp_len = max(1.0, aspect) * np.sqrt(2)
        offset = (t - 0.5) * perp_len
        length = 2.0 * max(1.0, aspect) * np.sqrt(2)
        px = cx_c - sin_a * offset
        py = cy_c + cos_a * offset
        x0 = px - cos_a * length
        y0 = py - sin_a * length
        x1 = px + cos_a * length
        y1 = py + sin_a * length
        segs.append(_sashiko_seg(x0, y0, x1, y1))
    return _sashiko_cat(*segs)


def pat_kikko(n=5, aspect=1.0):
    """Kikko — tortoiseshell hexagonal grid."""
    dx = 1.0 / n
    r  = dx / np.sqrt(3)
    dy = 1.5 * r
    n_cols = n + 3
    n_rows = int(aspect / dy) + 3
    angles = np.linspace(np.pi / 6, np.pi / 6 + 2 * np.pi, 7)
    cos_a  = np.cos(angles)
    sin_a  = np.sin(angles)
    segs = []
    for row in range(-1, n_rows):
        y_center = row * dy
        x_offset = dx * 0.5 if (row % 2 == 1) else 0.0
        for col in range(-1, n_cols):
            cx = col * dx + x_offset
            vx = np.append(cx + r * cos_a, np.nan)
            vy = np.append(y_center + r * sin_a, np.nan)
            segs.append((vx, vy))
    return _sashiko_cat(*segs)


def pat_yabane(n=8, res=60, aspect=1.0):
    """Yabane — arrow-feather chevron rows."""
    unit = 1.0 / n
    n_rows = int(n * aspect) + 2
    segs = []
    for row in range(n_rows):
        y_base = row * unit
        t = np.linspace(0.0, 1.0, res * 2 + 1)
        ys = y_base + unit * 0.5 * (1.0 - 2.0 * np.abs(t - 0.5))
        segs.append((np.append(t, np.nan), np.append(ys, np.nan)))
    return _sashiko_cat(*segs)


def pat_kagome(n=6, aspect=1.0):
    """Kagome — bamboo-basket weave: interlocked hexagons + triangles."""
    r   = 1.0 / (n * 2.0)
    dx  = r * 3.0
    dy  = r * np.sqrt(3)
    n_cols = int(1.0 / dx) + 3
    n_rows = int(aspect / dy) + 3
    hex_a = np.radians([0, 60, 120, 180, 240, 300])
    vx = r * np.cos(hex_a)
    vy = r * np.sin(hex_a)
    segs = []
    for col in range(-1, n_cols):
        xc = col * dx
        y_off = dy * 0.5 if (col % 2 == 1) else 0.0
        for row in range(-1, n_rows):
            yc = row * dy + y_off
            hx = np.append(xc + vx, xc + vx[0])
            hy = np.append(yc + vy, yc + vy[0])
            segs.append((np.append(hx, np.nan), np.append(hy, np.nan)))
            for k in range(6):
                ax, ay = xc + vx[k], yc + vy[k]
                bx, by = xc + vx[(k+1) % 6], yc + vy[(k+1) % 6]
                ex = ax + bx - xc
                ey = ay + by - yc
                segs.append(_sashiko_seg(ax, ay, ex, ey))
                segs.append(_sashiko_seg(bx, by, ex, ey))
    return _sashiko_cat(*segs)


def pat_tatewaku(n=8, waves=3, res=80, aspect=1.0):
    """Tatewaku — rising-steam sinusoidal parallel lines."""
    unit = 1.0 / n
    amplitude = unit * 0.3
    t = np.linspace(0.0, aspect, max(res, int(res * aspect)))
    segs = []
    for col in range(n + 1):
        x0 = col * unit
        phase = np.pi if (col % 2 == 1) else 0.0
        xs = np.append(x0 + amplitude * np.sin((t / aspect) * waves * 2 * np.pi + phase), np.nan)
        ys = np.append(t, np.nan)
        segs.append((xs, ys))
    return _sashiko_cat(*segs)


def pat_renga(n=6, aspect=1.0):
    """Renga — brick/running-bond: offset rows of 2:1 rectangles."""
    bw = 1.0 / n
    bh = bw * 0.5
    n_rows = int(aspect / bh) + 2
    segs = []
    for row in range(-1, n_rows):
        y   = row * bh
        off = bw * 0.5 if (row % 2 == 1) else 0.0
        n_bricks = n + 2
        for col in range(-1, n_bricks):
            x = col * bw + off
            segs += [
                _sashiko_seg(x,      y,      x + bw, y),
                _sashiko_seg(x + bw, y,      x + bw, y + bh),
                _sashiko_seg(x + bw, y + bh, x,      y + bh),
                _sashiko_seg(x,      y + bh, x,      y),
            ]
    return _sashiko_cat(*segs)


def pat_hishi(n=8, aspect=1.0):
    """Hishi — diamond lattice: diagonal crosshatch at ±45°."""
    unit = 1.0 / n
    segs = []
    for k in range(-(n + 2), int(aspect * n) + n + 3):
        c = k * unit
        t0, t1 = max(0.0, -c), min(1.0, aspect - c)
        if t0 < t1:
            segs.append(_sashiko_seg(t0, t0 + c, t1, t1 + c))
    for k in range(-2, int((1.0 + aspect) * n) + 4):
        c = k * unit
        t0, t1 = max(0.0, c - aspect), min(1.0, c)
        if t0 < t1:
            segs.append(_sashiko_seg(t0, c - t0, t1, c - t1))
    return _sashiko_cat(*segs)


def pat_uroko(n=6, aspect=1.0):
    """Uroko — fish-scale pattern: rows of downward-pointing equilateral triangles."""
    unit = 1.0 / n
    h = unit * np.sqrt(3) / 2
    row_step = h * 0.75
    n_rows = int(aspect / row_step) + 3
    segs = []
    for row in range(-1, n_rows):
        y_base = row * row_step
        off = (unit * 0.5) if (row % 2 == 1) else 0.0
        for col in range(-1, n + 2):
            x_left = col * unit + off
            bx1, by1 = x_left,              y_base
            bx2, by2 = x_left + unit,       y_base
            ax,  ay  = x_left + unit * 0.5, y_base + h
            segs += [_sashiko_seg(bx1, by1, bx2, by2),
                     _sashiko_seg(bx2, by2, ax,  ay),
                     _sashiko_seg(ax,  ay,  bx1, by1)]
    return _sashiko_cat(*segs)


def pat_komezashi(n=8, aspect=1.0):
    """Komezashi — rice stitch: four-directional asterisk marks at every grid node."""
    unit = 1.0 / n
    r = unit * 0.38
    n_rows = int(n * aspect) + 2
    segs = []
    for i in range(-1, n_rows):
        for j in range(-1, n + 2):
            cx, cy = j * unit, i * unit
            for a in [0.0, np.pi / 4, np.pi / 2, 3 * np.pi / 4]:
                dx, dy = np.cos(a) * r, np.sin(a) * r
                segs.append(_sashiko_seg(cx - dx, cy - dy, cx + dx, cy + dy))
    return _sashiko_cat(*segs)


def pat_matsukawabishi(n=5, aspect=1.0):
    """Matsukawabishi — pine-bark diamond: staggered overlapping diamond grid."""
    unit = 1.0 / n
    dw = unit
    dh = unit * 0.65
    row_step = dh * 1.4
    n_rows = int(aspect / row_step) + 3
    segs = []
    for row in range(-2, n_rows):
        yc = row * row_step
        off = dw if (row % 2 == 1) else 0.0
        for col in range(-1, n + 2):
            xc = col * 2 * dw + off
            segs += [_sashiko_seg(xc, yc - dh, xc + dw, yc),
                     _sashiko_seg(xc + dw, yc, xc, yc + dh),
                     _sashiko_seg(xc, yc + dh, xc - dw, yc),
                     _sashiko_seg(xc - dw, yc, xc, yc - dh)]
    return _sashiko_cat(*segs)


def pat_kanoko(n=5, rings=3, aspect=1.0):
    """Kanoko — fawn-spot: concentric diamond rings tiled on a square grid."""
    unit = 1.0 / n
    n_rows = int(n * aspect) + 2
    segs = []
    for i in range(-1, n_rows):
        for j in range(-1, n + 2):
            cx = (j + 0.5) * unit
            cy = (i + 0.5) * unit
            for ring in range(1, rings + 1):
                s = ring * unit / (2 * (rings + 0.5))
                segs += [_sashiko_seg(cx, cy - s, cx + s, cy),
                         _sashiko_seg(cx + s, cy, cx, cy + s),
                         _sashiko_seg(cx, cy + s, cx - s, cy),
                         _sashiko_seg(cx - s, cy, cx, cy - s)]
    return _sashiko_cat(*segs)


def pat_bishamon_kikko(n=5, aspect=1.0):
    """Bishamon-kikko — tortoiseshell with 3D cube subdivision."""
    dx = 1.0 / n
    r  = dx / np.sqrt(3)
    dy = 1.5 * r
    n_cols = n + 3
    n_rows = int(aspect / dy) + 3
    hex_a = np.radians([30, 90, 150, 210, 270, 330])
    vx = r * np.cos(hex_a)
    vy = r * np.sin(hex_a)
    segs = []
    for row in range(-1, n_rows):
        yc = row * dy
        x_off = dx * 0.5 if (row % 2 == 1) else 0.0
        for col in range(-1, n_cols):
            cx = col * dx + x_off
            hx = np.append(cx + vx, cx + vx[0])
            hy = np.append(yc + vy, yc + vy[0])
            segs.append((np.append(hx, np.nan), np.append(hy, np.nan)))
            for vi in [0, 2, 4]:
                segs.append(_sashiko_seg(cx, yc, cx + vx[vi], yc + vy[vi]))
    return _sashiko_cat(*segs)


def pat_juji(n=8, aspect=1.0):
    """Juji — cross pattern: disconnected + shaped stitches on a square grid."""
    unit = 1.0 / n
    arm = unit * 0.35
    n_rows = int(n * aspect) + 2
    segs = []
    for i in range(-1, n_rows):
        for j in range(-1, n + 2):
            cx, cy = (j + 0.5) * unit, (i + 0.5) * unit
            segs.append(_sashiko_seg(cx - arm, cy, cx + arm, cy))
            segs.append(_sashiko_seg(cx, cy - arm, cx, cy + arm))
    return _sashiko_cat(*segs)


def pat_raimon(n=4, turns=3, aspect=1.0):
    """Raimon — thunder fret: square-spiral motif tiled on a grid."""
    unit = 1.0 / n
    n_rows = int(n * aspect) + 2
    segs = []
    for row in range(-1, n_rows):
        for col in range(-1, n + 2):
            cx = (col + 0.5) * unit
            cy = (row + 0.5) * unit
            m = unit / (2 * (turns + 1))
            pts_x = [cx - turns * m]
            pts_y = [cy - turns * m]
            for i in range(turns, 0, -1):
                r = i * m
                pts_x += [cx + r, cx + r, cx - r, cx - r]
                pts_y += [cy - r, cy + r, cy + r, cy - (i - 1) * m]
                if i > 1:
                    pts_x.append(cx - (i - 1) * m)
                    pts_y.append(cy - (i - 1) * m)
            pts_x.append(np.nan)
            pts_y.append(np.nan)
            segs.append((np.array(pts_x), np.array(pts_y)))
    return _sashiko_cat(*segs)


def pat_nanamezashi(n=10, aspect=1.0):
    """Nanamezashi — diagonal running-stitch grid: offset short dashes at ±45°."""
    unit = 1.0 / n
    half = unit * 0.5
    segs = []
    for k in range(-(n + 2), int(aspect * n) + n + 3):
        c = k * unit
        off = half if (k % 2 == 1) else 0.0
        x_lo, x_hi = max(0.0, -c), min(1.0, aspect - c)
        if x_lo >= x_hi:
            continue
        t = off + np.floor((x_lo - off) / unit) * unit
        while t <= x_hi - 1e-9:
            t0, t1 = max(t, x_lo), min(t + half, x_hi)
            if t1 > t0 + 1e-12:
                segs.append(_sashiko_seg(t0, t0 + c, t1, t1 + c))
            t += unit
    for k in range(-2, int((1.0 + aspect) * n) + 3):
        c = k * unit
        off = half if (k % 2 == 1) else 0.0
        x_lo, x_hi = max(0.0, c - aspect), min(1.0, c)
        if x_lo >= x_hi:
            continue
        t = off + np.floor((x_lo - off) / unit) * unit
        while t <= x_hi - 1e-9:
            t0, t1 = max(t, x_lo), min(t + half, x_hi)
            if t1 > t0 + 1e-12:
                segs.append(_sashiko_seg(t0, c - t0, t1, c - t1))
            t += unit
    return _sashiko_cat(*segs)


def pat_hanabishi(n=5, aspect=1.0):
    """Hanabishi — flower-diamond: four elongated diamonds pinwheeled around a centre."""
    unit = 1.0 / n
    a  = unit * 0.48
    b  = unit * 0.18
    n_rows = int(n * aspect) + 2
    segs = []
    for row in range(-1, n_rows):
        for col in range(-1, n + 2):
            cx = (col + 0.5) * unit
            cy = (row + 0.5) * unit
            for angle in [0.0, np.pi / 4, np.pi / 2, 3 * np.pi / 4]:
                ca, sa = np.cos(angle), np.sin(angle)
                cb, sb = np.cos(angle + np.pi/2), np.sin(angle + np.pi/2)
                p0x, p0y = cx + a * ca,  cy + a * sa
                p1x, p1y = cx + b * cb,  cy + b * sb
                p2x, p2y = cx - a * ca,  cy - a * sa
                p3x, p3y = cx - b * cb,  cy - b * sb
                diamond_x = np.array([p0x, p1x, p2x, p3x, p0x, np.nan])
                diamond_y = np.array([p0y, p1y, p2y, p3y, p0y, np.nan])
                segs.append((diamond_x, diamond_y))
    return _sashiko_cat(*segs)


def pat_kaku_shippo(n=6, aspect=1.0):
    """Kaku-shippo — square seven-treasures: overlapping axis-aligned squares."""
    unit = 1.0 / n
    half = unit * 0.60
    n_rows = int(n * aspect) + 2
    segs = []
    for row in range(-1, n_rows):
        for col in range(-1, n + 2):
            cx = (col + 0.5) * unit
            cy = (row + 0.5) * unit
            l, r_, t, b = cx - half, cx + half, cy - half, cy + half
            segs += [
                _sashiko_seg(l, t, r_, t),
                _sashiko_seg(r_, t, r_, b),
                _sashiko_seg(r_, b, l, b),
                _sashiko_seg(l, b, l, t),
            ]
    return _sashiko_cat(*segs)


def pat_makai_kikko(n=5, aspect=1.0):
    """Makai-kikko — demon tortoiseshell: hexagons with inscribed hexagram."""
    dx = 1.0 / n
    r  = dx / np.sqrt(3)
    dy = 1.5 * r
    n_cols = n + 3
    n_rows = int(aspect / dy) + 3
    hex_a = np.radians([30, 90, 150, 210, 270, 330])
    vx = r * np.cos(hex_a)
    vy = r * np.sin(hex_a)
    segs = []
    for row in range(-1, n_rows):
        yc = row * dy
        x_off = dx * 0.5 if (row % 2 == 1) else 0.0
        for col in range(-1, n_cols):
            cx = col * dx + x_off
            hx = np.append(cx + vx, cx + vx[0])
            hy = np.append(yc + vy, yc + vy[0])
            segs.append((np.append(hx, np.nan), np.append(hy, np.nan)))
            t1x = np.array([cx+vx[0], cx+vx[2], cx+vx[4], cx+vx[0], np.nan])
            t1y = np.array([yc+vy[0], yc+vy[2], yc+vy[4], yc+vy[0], np.nan])
            segs.append((t1x, t1y))
            t2x = np.array([cx+vx[1], cx+vx[3], cx+vx[5], cx+vx[1], np.nan])
            t2y = np.array([yc+vy[1], yc+vy[3], yc+vy[5], yc+vy[1], np.nan])
            segs.append((t2x, t2y))
    return _sashiko_cat(*segs)


def pat_koekoek(n=8, aspect=1.0):
    """Koekoek — cuckoo-foot: three-pronged bird-track marks on a staggered grid."""
    unit = 1.0 / n
    arm  = unit * 0.42
    n_rows = int(n * aspect) + 2
    segs = []
    for i in range(-1, n_rows):
        cy  = (i + 0.5) * unit
        off = unit * 0.5 if (i % 2 == 1) else 0.0
        for j in range(-1, n + 2):
            cx = (j + 0.5) * unit + off
            segs.append(_sashiko_seg(cx, cy, cx, cy + arm))
            segs.append(_sashiko_seg(cx, cy, cx - arm * 0.7, cy - arm * 0.7))
            segs.append(_sashiko_seg(cx, cy, cx + arm * 0.7, cy - arm * 0.7))
    return _sashiko_cat(*segs)


def pat_yamagata(n=8, aspect=1.0):
    """Yamagata — mountain-shape: stacked chevron rows forming sharp zigzags."""
    unit = 1.0 / n
    n_rows = int(n * aspect) + 2
    segs = []
    for row in range(n_rows):
        y_base = row * unit
        pts_x = []
        pts_y = []
        for col in range(-1, n + 2):
            x_peak = col * unit
            x_val  = x_peak + unit * 0.5
            pts_x += [x_peak, x_val]
            pts_y += [y_base, y_base + unit]
        pts_x.append(np.nan)
        pts_y.append(np.nan)
        segs.append((np.array(pts_x), np.array(pts_y)))
    return _sashiko_cat(*segs)


def pat_hana_shippo(n=6, steps=24, aspect=1.0):
    """Hana-shippo — flower seven-treasures: 4-petal flower grid."""
    unit = 1.0 / n
    r    = unit * 0.5
    n_rows = int(n * aspect) + 2
    segs = []
    for row in range(-1, n_rows):
        for col in range(-1, n + 2):
            cx = (col + 0.5) * unit
            cy = (row + 0.5) * unit
            segs.append(_sashiko_arc(cx, cy - r, r, t0=0,          t1=np.pi,        steps=steps))
            segs.append(_sashiko_arc(cx, cy + r, r, t0=np.pi,      t1=2*np.pi,      steps=steps))
            segs.append(_sashiko_arc(cx - r, cy, r, t0=np.pi*1.5,  t1=np.pi*2.5,    steps=steps))
            segs.append(_sashiko_arc(cx + r, cy, r, t0=np.pi*0.5,  t1=np.pi*1.5,    steps=steps))
    return _sashiko_cat(*segs)


def pat_asanoha_yae(n=3, aspect=1.0):
    """Asanoha-yae — double hemp-leaf: 8-pointed star on a square lattice."""
    unit = 1.0 / n
    r_out = unit * 0.48
    r_in  = unit * 0.22
    n_rows = int(n * aspect) + 2
    segs = []
    for row in range(-1, n_rows):
        for col in range(-1, n + 2):
            cx = (col + 0.5) * unit
            cy = (row + 0.5) * unit
            for k in range(8):
                angle = k * np.pi / 4
                segs.append(_sashiko_seg(cx, cy,
                                         cx + r_out * np.cos(angle),
                                         cy + r_out * np.sin(angle)))
            oct_x = np.array([cx + r_in * np.cos(k * np.pi / 4) for k in range(9)] + [np.nan])
            oct_y = np.array([cy + r_in * np.sin(k * np.pi / 4) for k in range(9)] + [np.nan])
            segs.append((oct_x, oct_y))
    return _sashiko_cat(*segs)


# ─────────────────────────────────────────────────────────────────────────────
# SASHIKO PATTERN REGISTRY
# ─────────────────────────────────────────────────────────────────────────────

SASHIKO_PATTERNS = {
    # ── Sparse: parallel lines, simple rows ──────────────────────────────────
    'nowaki':          pat_nowaki,
    'tatewaku':        pat_tatewaku,
    'yamagata':        pat_yamagata,
    'yabane':          pat_yabane,
    # ── Sparse marks: isolated motifs on a grid ───────────────────────────────
    'juji':            pat_juji,
    'koekoek':         pat_koekoek,
    'nanamezashi':     pat_nanamezashi,
    'hito_mezashi':    pat_hito_mezashi,
    # ── Low-medium: two-family lines, spaced curves ───────────────────────────
    'hishi':           pat_hishi,
    'komezashi':       pat_komezashi,
    'shippo':          pat_shippo,
    'hana_shippo':     pat_hana_shippo,
    'kanoko':          pat_kanoko,
    # ── Medium: single-element tessellations ──────────────────────────────────
    'seigaiha':        pat_seigaiha,
    'asanoha_yae':     pat_asanoha_yae,
    'hanabishi':       pat_hanabishi,
    'raimon':          pat_raimon,
    'uroko':           pat_uroko,
    'kikko':           pat_kikko,
    # ── Medium-dense: multi-segment cells, compound tilings ──────────────────
    'sayagata':        pat_sayagata,
    'renga':           pat_renga,
    'kaku_shippo':     pat_kaku_shippo,
    'matsukawabishi':  pat_matsukawabishi,
    # ── Dense: subdivided cells, layered geometry ─────────────────────────────
    'bishamon_kikko':  pat_bishamon_kikko,
    'kagome':          pat_kagome,
    'asa_no_ha':       pat_asa_no_ha,
    'makai_kikko':     pat_makai_kikko,
}


def sashiko_pattern(name, n=None, aspect=1.0):
    """Call the named sashiko pattern function, forwarding n and aspect where accepted."""
    import inspect
    fn = SASHIKO_PATTERNS[name]
    sig = inspect.signature(fn).parameters
    kwargs = {}
    if n is not None and 'n' in sig:
        kwargs['n'] = n
    if 'aspect' in sig:
        kwargs['aspect'] = aspect
    return fn(**kwargs)