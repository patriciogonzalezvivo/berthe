#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Bitmap — a raster-image element for placement in a Berthe Surface.

``scale``  = scalar multiplier of the natural image size at 96 DPI
             (1 px = 0.264583 mm).  ``scale=1.0`` → natural size, ``scale=0.5``
             → half, etc.  Use ``pos`` + ``align`` to choose which corner/edge
             of the image is anchored at ``pos``.

Supported exports
-----------------
toSVG   Image data is base64-encoded and embedded inline (self-contained SVG).
toPNG   Image is rasterised with PIL and composited via cairocffi.
toTeX   Emits a TikZ ``\\node`` containing ``\\includegraphics``.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import base64
import copy
import math
import os

from .Element import Element

# Mapping from Berthe align names to TikZ anchor names
_ALIGN_TO_TIKZ = {
    'top_left':     'north west',
    'top_right':    'north east',
    'bottom_left':  'south west',
    'bottom_right': 'south east',
    'center':       'center',
    'top':          'north',
    'bottom':       'south',
    'left':         'west',
    'right':        'east',
}

# Vertical flip map for TikZ anchor names (used when flip_y=True)
_TIKZ_FLIP_Y = {
    'north west': 'south west',
    'north east': 'south east',
    'south west': 'north west',
    'south east': 'north east',
    'north':      'south',
    'south':      'north',
    'center':     'center',
    'west':       'west',
    'east':       'east',
}


class Bitmap(Element):
    """A raster-image element placed at a fixed position in the Surface.

    Parameters
    ----------
    filepath : str
        Path to the image file (PNG, JPEG, …).
    pos : (x, y)
        Anchor position in mm.
    align : str
        Which edge/corner of the image is anchored at *pos*.
        Values: ``'top_left'``, ``'top_right'``, ``'bottom_left'``,
        ``'bottom_right'``, ``'center'``, ``'top'``, ``'bottom'``,
        ``'left'``, ``'right'``.  Default: ``'top_left'``.
    scale : float
        Scalar multiplier applied to the natural image size at 96 DPI
        (1 px = 0.264583 mm).  ``scale=1.0`` renders the image at its actual
        pixel size; ``scale=0.5`` renders it at half that size, etc.
    rotate : float
        Rotation in degrees, CCW, applied about the anchor point.  Default 0.
    """

    def __init__(self, filepath, pos, **kwargs):
        self.align = kwargs.pop('align', 'top_left')
        # Element.__init__ pops and stores: scale, rotate, translate, color, …
        Element.__init__(self, **kwargs)

        self.filepath = filepath
        self.pos = tuple(pos)

        # Load the image once to read pixel dimensions.
        try:
            from PIL import Image as PILImage
            with PILImage.open(filepath) as img:
                self._px_w, self._px_h = img.size
        except Exception:
            self._px_w, self._px_h = 100, 100  # safe fallback

        self.aspect = self._px_h / self._px_w  # > 1 → portrait

        # scale is a scalar multiplier of the natural image size at 96 DPI
        # (1 px = 0.264583 mm).  scale=1.0 → natural size, scale=0.5 → half, etc.
        natural_width = self._px_w * 0.264583   # px → mm @ 96 DPI
        self.display_width  = natural_width * self.scale
        self.display_height = self.display_width * self.aspect

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _top_left(self):
        """Return the top-left (x, y) corner of the image in mm."""
        x, y = self.pos
        w, h = self.display_width, self.display_height
        a = self.align
        if   a in ('top_left',    'left'):   return x,           y
        elif a == 'top_right':               return x - w,       y
        elif a == 'bottom_left':             return x,           y - h
        elif a == 'bottom_right':            return x - w,       y - h
        elif a == 'center':                  return x - w / 2,   y - h / 2
        elif a == 'top':                     return x - w / 2,   y
        elif a == 'bottom':                  return x - w / 2,   y - h
        elif a == 'right':                   return x - w,       y - h / 2
        return x, y

    # ------------------------------------------------------------------
    # Element protocol
    # ------------------------------------------------------------------

    def getPoints(self):
        """Return the four corners of the bounding box (un-rotated)."""
        tx, ty = self._top_left()
        w, h = self.display_width, self.display_height
        return [(tx, ty), (tx + w, ty), (tx + w, ty + h), (tx, ty + h)]

    def getTransformed(self, func):
        """Return a new Bitmap with the anchor pos transformed by *func(x, y)*."""
        new = copy.copy(self)
        new.pos = func(*self.pos)
        return new

    # ------------------------------------------------------------------
    # SVG — inline base64 data URI
    # ------------------------------------------------------------------

    def getSVGElementString(self):
        tx, ty = self._top_left()
        w, h   = self.display_width, self.display_height

        # Embed the image as a base64 data URI for a self-contained SVG.
        try:
            with open(self.filepath, 'rb') as f:
                raw = f.read()
            ext  = os.path.splitext(self.filepath)[1].lower()
            mime = {'.png':  'image/png',  '.jpg':  'image/jpeg',
                    '.jpeg': 'image/jpeg', '.gif':  'image/gif',
                    '.bmp':  'image/bmp',  '.webp': 'image/webp'}.get(ext, 'image/png')
            b64  = base64.b64encode(raw).decode('ascii')
            href = f'data:{mime};base64,{b64}'
        except Exception:
            href = self.filepath  # fallback to a file-path reference

        cx = tx + w / 2
        cy = ty + h / 2

        attrs = (f'x="{tx:.4f}" y="{ty:.4f}" '
                 f'width="{w:.4f}" height="{h:.4f}" '
                 f'preserveAspectRatio="xMidYMid meet" ')

        if self.rotate:
            attrs += f'transform="rotate({self.rotate:.3f},{cx:.4f},{cy:.4f})" '

        # Include both href (SVG 2) and xlink:href (SVG 1.1 / Inkscape compat).
        return f'<image {attrs}href="{href}" xlink:href="{href}"/>\n'

    # ------------------------------------------------------------------
    # PNG — cairo compositing
    # ------------------------------------------------------------------

    def drawToCairo(self, dc, scale_factor, flip_y=False, surface_height=0):
        """Draw this bitmap onto a *cairocffi* context.

        Parameters
        ----------
        dc : cairocffi.Context
        scale_factor : float
            Pixels per mm for the whole Surface render.
        flip_y : bool
            When True the y-axis is flipped (SVG top-left → Cairo bottom-left).
        surface_height : float
            Surface height in mm; required when *flip_y* is True.
        """
        try:
            import cairocffi as cairo
            from PIL import Image as PILImage
            import numpy as np
        except ImportError:
            return

        tx, ty = self._top_left()
        if flip_y:
            ty = surface_height - ty - self.display_height

        px_w = max(1, int(round(self.display_width  * scale_factor)))
        px_h = max(1, int(round(self.display_height * scale_factor)))

        with PILImage.open(self.filepath) as img:
            img = img.resize((px_w, px_h), PILImage.LANCZOS).convert('RGBA')

        arr = np.array(img, dtype=np.uint8)

        # Cairo ARGB32 is BGRA with pre-multiplied alpha (little-endian).
        alpha_f = arr[:, :, 3:4].astype(np.float32) / 255.0
        bgra = np.empty_like(arr)
        bgra[:, :, 0] = (arr[:, :, 2] * alpha_f[:, :, 0]).astype(np.uint8)  # B
        bgra[:, :, 1] = (arr[:, :, 1] * alpha_f[:, :, 0]).astype(np.uint8)  # G
        bgra[:, :, 2] = (arr[:, :, 0] * alpha_f[:, :, 0]).astype(np.uint8)  # R
        bgra[:, :, 3] = arr[:, :, 3]                                          # A

        stride = px_w * 4
        img_surface = cairo.ImageSurface.create_for_data(
            bytearray(bgra.tobytes()), cairo.FORMAT_ARGB32, px_w, px_h, stride
        )

        dc.save()
        if self.rotate:
            cx_px = (tx + self.display_width  / 2) * scale_factor
            cy_px = (ty + self.display_height / 2) * scale_factor
            dc.translate(cx_px, cy_px)
            dc.rotate(-self.rotate * math.pi / 180.0)
            dc.translate(-cx_px, -cy_px)

        dc.set_source_surface(img_surface, tx * scale_factor, ty * scale_factor)
        dc.paint()
        dc.restore()

    # ------------------------------------------------------------------
    # TikZ / LaTeX
    # ------------------------------------------------------------------

    def getTeXString(self, flip_y=False, surface_height=0):
        """Return a TikZ ``\\node`` string that embeds ``\\includegraphics``."""
        anchor = _ALIGN_TO_TIKZ.get(self.align, 'north west')
        ax, ay = self.pos
        if flip_y:
            anchor = _TIKZ_FLIP_Y.get(anchor, anchor)
            ay = surface_height - ay

        rot_opt = f', rotate={self.rotate:.1f}' if self.rotate else ''
        return (
            f'  \\node[anchor={anchor}{rot_opt}] at ({ax:.4f}mm,{ay:.4f}mm) '
            f'{{\\includegraphics[width={self.display_width:.4f}mm]{{{self.filepath}}}}};\n'
        )
