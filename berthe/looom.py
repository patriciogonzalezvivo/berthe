"""
looom.py — Looom animation SVG parser and frame extractor.

Looom (https://www.iorama.studio/looom) exports animations as SVG files where:
  - A <style> block uses CSS custom properties to define per-thread animation
    parameters (speed, timeOffset, playMode, latched, stroke colour, etc.).
  - Each thread is a ``<g class="thread">`` containing numbered
    ``<g class="frame">`` children.
  - At runtime, CSS ``@keyframes`` cycles through the frames using ``opacity``.

This module re-implements that logic in pure Python so that a single static
frame can be extracted and rasterised to PNG for PDF portfolio embedding.

Public API
----------
is_looom_svg(path)
    Quick check: does this SVG look like a Looom animation file?

looom_frame_to_png(svg_path, output_path, *, frame=None, time=0.0,
                   margin_frac=0.10, width=800)
    Full pipeline: parse → select frame → compute tight viewBox → render PNG
    via Inkscape.

The two wrapfig keys recognised inside ``:::wrapfig`` blocks::

    frame: 0        # explicit frame index (takes priority over time:)
    time:  2.5      # time in seconds (default 0.0 when neither is given)
"""

from __future__ import annotations

import math
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------

def is_looom_svg(path) -> bool:
    """Return ``True`` if *path* looks like a Looom animation SVG file."""
    try:
        head = Path(path).read_text(encoding='utf-8', errors='replace')[:4096]
        return '#looom' in head and 'class="weave"' in head
    except OSError:
        return False


# ---------------------------------------------------------------------------
# CSS parsing helpers
# ---------------------------------------------------------------------------

_BOOL_KEYS = frozenset({'visible', 'latched', 'masked', 'pressureEnabled'})


def _coerce(name: str, val: str):
    """Convert a CSS value string to an appropriate Python type."""
    if name in _BOOL_KEYS:
        return val.strip() == '1'
    try:
        return float(val)
    except ValueError:
        return val.strip()


def _parse_css_threads(css_text: str) -> Dict[str, Dict]:
    """Return a dict of thread-id → options parsed from Looom CSS.

    Handles both CSS custom properties (``--speed:6;``) and regular
    properties (``stroke:#D8484D;``) inside each thread rule block.
    """
    threads: Dict[str, Dict] = {}
    rule_re    = re.compile(r'#(\w+)\s*\{([^}]+)\}', re.DOTALL)
    custom_re  = re.compile(r'--(\w+)\s*:\s*([^;]+);')
    regular_re = re.compile(
        r'(?<!-)(?<!\w)'
        r'(stroke|fill|stroke-opacity|fill-opacity|stroke-width'
        r'|stroke-linecap|stroke-linejoin)'
        r'\s*:\s*([^;]+);'
    )

    for m in rule_re.finditer(css_text):
        rule_id = m.group(1)
        body    = m.group(2)

        # Only process thread rules: t0, t0a, t1, t1a, …
        if not re.match(r'^t\d', rule_id):
            continue

        opts: Dict = {}
        for cm in custom_re.finditer(body):
            opts[cm.group(1)] = _coerce(cm.group(1), cm.group(2))
        for pm in regular_re.finditer(body):
            opts[pm.group(1)] = pm.group(2).strip()

        threads[rule_id] = opts

    return threads


# ---------------------------------------------------------------------------
# 2-D affine matrix helpers
# ---------------------------------------------------------------------------
# Representation: [a, b, c, d, e, f]  →  the column-major matrix
#
#   ┌ a  c  e ┐       x' = a·x + c·y + e
#   │ b  d  f │   →   y' = b·x + d·y + f
#   └ 0  0  1 ┘

MatrixT = List[float]


def _mat_identity() -> MatrixT:
    return [1.0, 0.0, 0.0, 1.0, 0.0, 0.0]


def _mat_multiply(m1: MatrixT, m2: MatrixT) -> MatrixT:
    """Return m1 × m2  (apply m2 first, then m1)."""
    a1, b1, c1, d1, e1, f1 = m1
    a2, b2, c2, d2, e2, f2 = m2
    return [
        a1 * a2 + c1 * b2,
        b1 * a2 + d1 * b2,
        a1 * c2 + c1 * d2,
        b1 * c2 + d1 * d2,
        a1 * e2 + c1 * f2 + e1,
        b1 * e2 + d1 * f2 + f1,
    ]


def _mat_transform_point(m: MatrixT, x: float, y: float) -> Tuple[float, float]:
    a, b, c, d, e, f = m
    return (a * x + c * y + e, b * x + d * y + f)


def _parse_transform(transform_str: str) -> MatrixT:
    """Parse an SVG ``transform`` attribute value into a 6-element matrix."""
    if not transform_str or not transform_str.strip():
        return _mat_identity()

    m = _mat_identity()
    for match in re.finditer(r'(\w+)\(([^)]+)\)', transform_str):
        op   = match.group(1)
        args = [float(v) for v in re.split(r'[\s,]+', match.group(2).strip()) if v]

        if op == 'matrix':
            m = _mat_multiply(m, args[:6])

        elif op == 'translate':
            tx = args[0]
            ty = args[1] if len(args) > 1 else 0.0
            m = _mat_multiply(m, [1.0, 0.0, 0.0, 1.0, tx, ty])

        elif op == 'scale':
            sx = args[0]
            sy = args[1] if len(args) > 1 else sx
            m = _mat_multiply(m, [sx, 0.0, 0.0, sy, 0.0, 0.0])

        elif op == 'rotate':
            rad  = math.radians(args[0])
            cosa = math.cos(rad)
            sina = math.sin(rad)
            if len(args) >= 3:
                cx, cy = args[1], args[2]
                # Equivalent to: T(cx,cy) · R(θ) · T(-cx,-cy)
                rot = [
                    cosa, sina, -sina, cosa,
                    cx - cosa * cx + sina * cy,
                    cy - sina * cx - cosa * cy,
                ]
            else:
                rot = [cosa, sina, -sina, cosa, 0.0, 0.0]
            m = _mat_multiply(m, rot)

    return m


def _mat_to_transform_attr(m: MatrixT) -> str:
    """Return an SVG ``transform="matrix(…)"`` string, or ``''`` for identity."""
    identity = [1.0, 0.0, 0.0, 1.0, 0.0, 0.0]
    if all(abs(m[i] - identity[i]) < 1e-9 for i in range(6)):
        return ''
    a, b, c, d, e, f = m
    return f'matrix({a:.6g},{b:.6g},{c:.6g},{d:.6g},{e:.6g},{f:.6g})'


# ---------------------------------------------------------------------------
# Path bounding box
# ---------------------------------------------------------------------------

def _path_bbox(d: str, transform: MatrixT) -> Optional[Tuple[float, float, float, float]]:
    """Return ``(min_x, min_y, max_x, max_y)`` for all points in path *d*,
    with *transform* applied.

    Only ``M`` and ``L`` commands are recognised; these are the only commands
    Looom generates.
    """
    pts: List[Tuple[float, float]] = []

    # Looom paths look like: M348.35,-340.41L344.97,-340.46L...
    # Coordinates are separated by commas, possibly with spaces.
    coord_re = re.compile(
        r'([ML])\s*([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)'
        r'\s*[,\s]\s*'
        r'([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)'
    )
    for m in coord_re.finditer(d.upper()):
        x = float(m.group(2))
        y = float(m.group(3))
        tx, ty = _mat_transform_point(transform, x, y)
        pts.append((tx, ty))

    if not pts:
        return None

    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))


# ---------------------------------------------------------------------------
# Frame-index computation — matches looom-tools/src/looom-util.js exactly
# ---------------------------------------------------------------------------

def _wrap(value: float, from_: float, to: float) -> float:
    cycle = to - from_
    if cycle == 0.0:
        return to
    return value - cycle * math.floor((value - from_) / cycle)


def get_frame_index(thread_opts: Dict, time: float) -> int:
    """Return the frame index for *thread_opts* at *time* seconds.

    Implements the same logic as ``getFrameIndex()`` in looom-tools.
    """
    speed       = float(thread_opts.get('speed',      12))
    latched     = bool(thread_opts.get('latched',     False))
    time_offset = float(thread_opts.get('timeOffset', 0.0))
    play_mode   = int(float(thread_opts.get('playMode', 0)))
    n_frames    = int(thread_opts.get('_n_frames',    1))

    if n_frames <= 0:
        return 0

    # playMode 3 = random; default to frame 0 for static extraction
    if play_mode == 3:
        return 0

    interval_ms = 1000.0 / speed
    time_ms     = round(time * 1000.0 / interval_ms) * interval_ms
    elapsed     = 0.0 if latched else (time_ms / 1000.0) + (time_offset / 1000.0)

    if play_mode in (0, 1):
        play_direction = 1 if play_mode == 0 else -1
    else:
        # ping-pong (playMode == 2)
        cur = _wrap(speed * elapsed, 0.0, float(n_frames) * 2.0)
        play_direction = 1 if cur > n_frames else -1

    cur_frame_real = _wrap(speed * elapsed * play_direction, 0.0, float(n_frames))
    cur_frame      = max(0, min(int(math.floor(cur_frame_real)), n_frames - 1))
    return cur_frame


# ---------------------------------------------------------------------------
# Looom SVG parser
# ---------------------------------------------------------------------------

_SVG_NS  = 'http://www.w3.org/2000/svg'
_NS_PFX  = f'{{{_SVG_NS}}}'


class LoomSVG:
    """Parsed representation of a Looom animation SVG file."""

    def __init__(self, path):
        self.path  = Path(path)
        self._text = self.path.read_text(encoding='utf-8')
        self._parse()

    # ------------------------------------------------------------------
    def _parse(self):
        # 1. Extract CSS and parse thread options
        style_m   = re.search(r'<style[^>]*>(.*?)</style>', self._text, re.DOTALL | re.IGNORECASE)
        css_text  = style_m.group(1) if style_m else ''
        self._thread_css = _parse_css_threads(css_text)

        # 2. Parse XML structure.
        #    Strip the XML declaration so ElementTree doesn't trip on encoding.
        xml_text = re.sub(r'<\?xml[^?]*\?>', '', self._text, count=1)
        try:
            root = self._et_root = __import__('xml.etree.ElementTree', fromlist=['fromstring']).fromstring(xml_text)
        except Exception as exc:
            raise ValueError(f"Could not parse Looom SVG: {self.path}") from exc

        # 3. viewBox / dimensions
        vb_str = root.get('viewBox', '0 0 800 600')
        vb_vals = [float(v) for v in re.split(r'[\s,]+', vb_str.strip()) if v]
        self.vb_x, self.vb_y, self.vb_w, self.vb_h = vb_vals
        self.viewBox = vb_str

        # 4. Find weave group (works with or without namespace prefix)
        weave_g = (
            root.find(f'.//{_NS_PFX}g[@class="weave"]') or
            root.find('.//g[@class="weave"]')
        )
        if weave_g is None:
            self.threads = []
            self.weave_transform = _mat_identity()
            self.weave_id = 'w0'
            return

        self.weave_transform = _parse_transform(weave_g.get('transform', ''))
        self.weave_id        = weave_g.get('id', 'w0')

        # 5. Parse threads and frames
        self.threads: List[Dict] = []

        for thread_g in weave_g:
            cls = thread_g.get('class', '')
            if 'thread' not in cls:
                continue

            tid  = thread_g.get('id', '')
            opts = dict(self._thread_css.get(tid, {}))

            frames: List[Dict] = []
            for frame_g in thread_g:
                fcls = frame_g.get('class', '')
                if 'frame' not in fcls:
                    continue

                fid_raw = frame_g.get('id', '')
                fnum_m  = re.search(r'\d+', fid_raw)
                # frame_idx not needed beyond ordering; list order is canonical
                frame_transform = _parse_transform(frame_g.get('transform', ''))

                paths: List[Dict] = []
                for child in frame_g:
                    tag = child.tag.replace(_NS_PFX, '')
                    if tag == 'path':
                        paths.append({
                            'd':         child.get('d', ''),
                            'transform': _parse_transform(child.get('transform', '')),
                        })

                frames.append({
                    'transform': frame_transform,
                    'paths':     paths,
                })

            opts['_n_frames'] = len(frames)
            self.threads.append({
                'id':        tid,
                'opts':      opts,
                'transform': _parse_transform(thread_g.get('transform', '')),
                'frames':    frames,
            })


# ---------------------------------------------------------------------------
# Static SVG builder
# ---------------------------------------------------------------------------

def _build_static_svg(looom: LoomSVG, time: float = 0.0,
                       frame_override: Optional[int] = None,
                       viewbox_override: Optional[Tuple[float, float, float, float]] = None) -> str:
    """Build a static (non-animated) SVG showing only the frame at *time*.

    Args:
        looom:            Parsed :class:`LoomSVG` instance.
        time:             Time in seconds (used when *frame_override* is ``None``).
        frame_override:   Force all threads to this frame index.
        viewbox_override: ``(x, y, w, h)`` to use as the SVG viewBox; when
                          ``None`` the original viewBox is kept.

    Returns:
        SVG document as a string.
    """
    if viewbox_override:
        vx, vy, vw, vh = viewbox_override
        vb_attr = f'{vx:.4f} {vy:.4f} {vw:.4f} {vh:.4f}'
    else:
        vb_attr = looom.viewBox

    lines = [f'<svg viewBox="{vb_attr}" xmlns="http://www.w3.org/2000/svg">']

    wt = _mat_to_transform_attr(looom.weave_transform)
    wt_attr = f' transform="{wt}"' if wt else ''
    lines.append(f'  <g id="{looom.weave_id}"{wt_attr}>')

    for thread in looom.threads:
        opts          = thread['opts']
        visible       = opts.get('visible', True)
        stroke_op     = float(opts.get('stroke-opacity',  opts.get('strokeOpacity',  1.0)))
        fill_op       = float(opts.get('fill-opacity',    opts.get('fillOpacity',    0.0)))

        if not visible or (stroke_op <= 0.0 and fill_op <= 0.0):
            continue

        frames = thread['frames']
        if not frames:
            continue

        if frame_override is not None:
            fidx = max(0, min(frame_override, len(frames) - 1))
        else:
            fidx = get_frame_index(opts, time)

        frame = frames[fidx]

        # Stroke / fill attributes
        stroke   = opts.get('stroke',          'black')
        stroke_w = opts.get('stroke-width',    opts.get('strokeWidth',    1))
        linecap  = opts.get('stroke-linecap',  opts.get('strokeLinecap',  'round'))
        linejoin = opts.get('stroke-linejoin', opts.get('strokeLinejoin', 'round'))

        tt = _mat_to_transform_attr(thread['transform'])
        ft = _mat_to_transform_attr(frame['transform'])

        tt_attr = f' transform="{tt}"' if tt else ''
        lines.append(
            f'    <g id="{thread["id"]}"{tt_attr}'
            f' stroke="{stroke}"'
            f' stroke-width="{stroke_w}"'
            f' stroke-opacity="{stroke_op}"'
            f' fill="none"'
            f' fill-opacity="{fill_op}"'
            f' stroke-linecap="{linecap}"'
            f' stroke-linejoin="{linejoin}">'
        )

        ft_attr = f' transform="{ft}"' if ft else ''
        lines.append(f'      <g{ft_attr}>')

        for path in frame['paths']:
            d  = path['d']
            pt = _mat_to_transform_attr(path['transform'])
            if pt:
                lines.append(f'        <path transform="{pt}" d="{d}"/>')
            else:
                lines.append(f'        <path d="{d}"/>')

        lines.append('      </g>')
        lines.append('    </g>')

    lines.append('  </g>')
    lines.append('</svg>')
    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Bounding-box computation
# ---------------------------------------------------------------------------

def compute_bbox(looom: LoomSVG, time: float = 0.0,
                 frame_override: Optional[int] = None
                 ) -> Optional[Tuple[float, float, float, float]]:
    """Return ``(min_x, min_y, max_x, max_y)`` in SVG canvas space.

    All transforms (weave → thread → frame → path) are applied before
    computing the bounding box.  Non-visible threads are skipped.
    """
    min_x = min_y =  math.inf
    max_x = max_y = -math.inf
    found = False

    for thread in looom.threads:
        opts      = thread['opts']
        visible   = opts.get('visible', True)
        stroke_op = float(opts.get('stroke-opacity', opts.get('strokeOpacity', 1.0)))
        fill_op   = float(opts.get('fill-opacity',   opts.get('fillOpacity',   0.0)))

        if not visible or (stroke_op <= 0.0 and fill_op <= 0.0):
            continue

        frames = thread['frames']
        if not frames:
            continue

        if frame_override is not None:
            fidx = max(0, min(frame_override, len(frames) - 1))
        else:
            fidx = get_frame_index(opts, time)

        frame = frames[fidx]

        # Accumulated transform: weave → thread → frame → path
        wt_x_tt = _mat_multiply(looom.weave_transform, thread['transform'])
        wt_x_ft = _mat_multiply(wt_x_tt, frame['transform'])

        for path in frame['paths']:
            full_m = _mat_multiply(wt_x_ft, path['transform'])
            bbox   = _path_bbox(path['d'], full_m)
            if bbox is None:
                continue
            found = True
            min_x = min(min_x, bbox[0])
            min_y = min(min_y, bbox[1])
            max_x = max(max_x, bbox[2])
            max_y = max(max_y, bbox[3])

    if not found:
        return None
    return (min_x, min_y, max_x, max_y)


# ---------------------------------------------------------------------------
# Main public entry point
# ---------------------------------------------------------------------------

def looom_frame_to_png(
    svg_path,
    output_path,
    *,
    frame: Optional[int] = None,
    time: float = 0.0,
    margin_frac: float = 0.10,
    width: int = 800,
) -> bool:
    """Extract a single frame from a Looom SVG and save it as a PNG.

    Steps:
      1. Parse the Looom SVG.
      2. Determine which frame to use (explicit *frame* index or *time*-based).
      3. Compute the tight bounding box of all visible paths.
      4. Add a proportional margin around that bounding box.
      5. Build a static SVG with the computed viewBox.
      6. Rasterise with Inkscape to PNG at *width* pixels wide.

    Args:
        svg_path:    Path to the source Looom SVG file.
        output_path: Destination PNG path.
        frame:       Frame index to extract.  Takes priority over *time*.
                     ``None`` → use *time*.
        time:        Time in seconds used to compute per-thread frame
                     indices when *frame* is ``None``.
        margin_frac: Fractional margin added around the drawing content,
                     relative to the larger of content width / height.
                     0.10 = 10 % margin on every side.
        width:       Output PNG width in pixels.

    Returns:
        ``True`` on success, ``False`` on failure.
    """
    looom = LoomSVG(svg_path)

    # ------------------------------------------------------------------ #
    # 1.  Compute tight bounding box                                       #
    # ------------------------------------------------------------------ #
    bbox = compute_bbox(looom, time=time, frame_override=frame)
    if bbox is None:
        print(f"  [looom] No visible paths in {svg_path}; falling back to viewBox.")
        bbox = (looom.vb_x, looom.vb_y,
                looom.vb_x + looom.vb_w, looom.vb_y + looom.vb_h)

    bx_min, by_min, bx_max, by_max = bbox
    content_w = bx_max - bx_min
    content_h = by_max - by_min

    if content_w <= 0 or content_h <= 0:
        print(f"  [looom] Degenerate bbox for {svg_path}; using viewBox.")
        bbox = (looom.vb_x, looom.vb_y,
                looom.vb_x + looom.vb_w, looom.vb_y + looom.vb_h)
        bx_min, by_min, bx_max, by_max = bbox
        content_w = bx_max - bx_min
        content_h = by_max - by_min

    # ------------------------------------------------------------------ #
    # 2.  Add margin                                                       #
    # ------------------------------------------------------------------ #
    margin   = max(content_w, content_h) * margin_frac
    vb_x     = bx_min - margin
    vb_y     = by_min - margin
    vb_w     = content_w + 2.0 * margin
    vb_h     = content_h + 2.0 * margin

    # ------------------------------------------------------------------ #
    # 3.  Build static SVG with new viewBox                                #
    # ------------------------------------------------------------------ #
    static_svg = _build_static_svg(
        looom,
        time=time,
        frame_override=frame,
        viewbox_override=(vb_x, vb_y, vb_w, vb_h),
    )

    # ------------------------------------------------------------------ #
    # 4.  Rasterise via Inkscape                                           #
    # ------------------------------------------------------------------ #
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    height = max(1, int(round(width * vb_h / vb_w))) if vb_w > 0 else width

    tmp_fd, tmp_svg = tempfile.mkstemp(suffix='.svg')
    try:
        with os.fdopen(tmp_fd, 'w', encoding='utf-8') as fh:
            fh.write(static_svg)

        result = subprocess.run(
            [
                'inkscape',
                '--export-type=png',
                f'--export-width={width}',
                f'--export-height={height}',
                f'--export-filename={output_path}',
                tmp_svg,
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0 or not output_path.exists():
            print(f"  [looom] inkscape failed (rc={result.returncode}):\n"
                  f"          {result.stderr.strip()}")
            return False

        print(f"  [looom] → {output_path}  ({width}×{height} px)")
        return True

    except FileNotFoundError:
        print("  [looom] inkscape not found; cannot rasterise Looom SVG frames.")
        return False
    except subprocess.TimeoutExpired:
        print(f"  [looom] inkscape timed out converting {svg_path}.")
        return False
    except Exception as exc:
        print(f"  [looom] Unexpected error converting {svg_path}: {exc}")
        return False
    finally:
        try:
            os.unlink(tmp_svg)
        except OSError:
            pass
