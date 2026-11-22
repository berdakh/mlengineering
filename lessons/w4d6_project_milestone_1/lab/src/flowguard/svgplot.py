"""A tiny, dependency-free SVG writer for report figures. Given to you; you do not need to edit it.

Why not matplotlib? The report step must run anywhere the package runs (CI, a container) and must be
byte-for-byte reproducible. Hand-written SVG with fixed number formatting is both. The colours are
the course palette (tools/figstyle.py).

    interval_plot(rows, path, title=..., xlabel=..., band=(-0.05, 0.05))

``rows``: list of dicts with ``label``, ``estimate``, ``lo``, ``hi`` (numbers). The figure draws one
horizontal interval per row, a dot at the estimate, a vertical line at zero and an optional shaded
band. It writes ``path`` and returns it.
"""
from __future__ import annotations

from html import escape
from pathlib import Path

SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
INK = {"primary": "#0b0b0b", "secondary": "#52514e", "muted": "#898781", "grid": "#e1e0d9",
       "axis": "#c3c2b7", "surface": "#fcfcfb", "band": "#ecebe6"}


def _f(x: float) -> str:
    return f"{x:.2f}"


def _ticks(lo: float, hi: float, n: int = 6) -> list[float]:
    raw = (hi - lo) / n
    step = next(m * 10.0 ** e for e in range(-6, 7) for m in (1, 2, 2.5, 5) if m * 10.0 ** e >= raw)
    k, out = int(lo // step), []
    while k * step <= hi + 1e-12:
        t = round(k * step, 10)
        if t >= lo - 1e-12:
            out.append(0.0 if abs(t) < 1e-12 else t)
        k += 1
    return out


def interval_plot(rows: list[dict], path: str | Path, title: str, xlabel: str,
                  band: tuple[float, float] | None = None, width: int = 720) -> Path:
    if not rows:
        raise ValueError("no rows to plot")
    left, right, top, row_h = 190, 210, 46, 34
    height = top + row_h * len(rows) + 56
    values = [v for r in rows for v in (r["lo"], r["hi"], r["estimate"])] + [0.0]
    if band:
        values += list(band)
    lo, hi = min(values), max(values)
    pad = (hi - lo) * 0.08 or 0.1
    lo, hi = lo - pad, hi + pad
    plot_w = width - left - right
    x = lambda v: left + (v - lo) / (hi - lo) * plot_w  # noqa: E731
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
           f'viewBox="0 0 {width} {height}" font-family="Inter, Helvetica, Arial, sans-serif" font-size="12">',
           f'<rect width="{width}" height="{height}" fill="{INK["surface"]}"/>',
           f'<text x="12" y="24" font-size="14" font-weight="700" fill="{INK["primary"]}">{escape(title)}</text>']
    y0, y1 = top - 6, top + row_h * len(rows) - 6
    for t in _ticks(lo, hi):
        out.append(f'<line x1="{_f(x(t))}" y1="{y0}" x2="{_f(x(t))}" y2="{y1}" stroke="{INK["grid"]}" stroke-width="0.6"/>')
        out.append(f'<text x="{_f(x(t))}" y="{y1 + 16}" text-anchor="middle" fill="{INK["secondary"]}">{t:g}</text>')
    if band:
        out.append(f'<rect x="{_f(x(band[0]))}" y="{y0}" width="{_f(x(band[1]) - x(band[0]))}" '
                   f'height="{y1 - y0}" fill="{INK["band"]}"/>')
    out.append(f'<line x1="{_f(x(0))}" y1="{y0}" x2="{_f(x(0))}" y2="{y1}" stroke="{INK["axis"]}" stroke-width="1"/>')
    for i, r in enumerate(rows):
        y = top + row_h * i + row_h / 2 - 6
        c = SERIES[i % len(SERIES)]
        out.append(f'<text x="{left - 10}" y="{_f(y + 4)}" text-anchor="end" fill="{INK["primary"]}">{escape(str(r["label"]))}</text>')
        out.append(f'<line x1="{_f(x(r["lo"]))}" y1="{_f(y)}" x2="{_f(x(r["hi"]))}" y2="{_f(y)}" stroke="{c}" '
                   f'stroke-width="3" stroke-linecap="round"/>')
        out.append(f'<circle cx="{_f(x(r["estimate"]))}" cy="{_f(y)}" r="5" fill="{c}" stroke="{INK["surface"]}" stroke-width="1.5"/>')
        out.append(f'<text x="{_f(x(hi) + 10)}" y="{_f(y + 4)}" fill="{INK["secondary"]}">'
                   f'{r["estimate"]:+.3f} [{r["lo"]:+.3f}, {r["hi"]:+.3f}]</text>')
    out.append(f'<text x="{_f(left + plot_w / 2)}" y="{y1 + 36}" text-anchor="middle" fill="{INK["secondary"]}">{escape(xlabel)}</text>')
    out.append("</svg>")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(out) + "\n")
    return path
