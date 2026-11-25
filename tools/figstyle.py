"""Shared matplotlib style for course figures, so every chart reads as one system.

    from tools.figstyle import apply, SERIES, SEQUENTIAL, DIVERGING, STATUS, INK, save

    apply()
    fig, ax = plt.subplots(figsize=(7, 3.6))
    ax.plot(x, y, color=SERIES[0], label="causal window")
    save(fig, "labs/<unit>/figures/<name>.svg")

Rules the style cannot enforce (follow them in the figure script):
  * Pick the form from the data's job; a single number is a sentence or a table, not a chart.
  * Categorical colours are taken from SERIES in order, never cycled past 8, and a colour stays
    with its entity across every figure of a lesson (e.g. "leaky" is always SERIES[1]).
  * One y-axis per chart. Two measures of different scale -> two panels.
  * Magnitude uses SEQUENTIAL (one hue, light to dark); signed values use DIVERGING.
  * STATUS colours mean good / warning / serious / critical only, and always carry a text label.
  * With two or more series show a legend; with four or fewer also label the series directly.
  * Text is INK["primary"/"secondary"/"muted"], never the series colour.
  * Every figure has a title stating the takeaway, axis labels with units, and the plotted
    numbers are also available in the lesson as a table or in a CSV next to the figure.
  * State SYNTHETIC in the title or caption when the data is synthetic.
"""
from __future__ import annotations

from pathlib import Path

SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
SEQUENTIAL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
DIVERGING = ["#184f95", "#6da7ec", "#f0efec", "#ec835a", "#d03b3b"]  # cool - neutral - warm
STATUS = {"good": "#0ca30c", "warning": "#fab219", "serious": "#ec835a", "critical": "#d03b3b"}
INK = {"primary": "#0b0b0b", "secondary": "#52514e", "muted": "#898781",
       "grid": "#e1e0d9", "axis": "#c3c2b7", "surface": "#fcfcfb"}


def apply() -> None:
    """Set rcParams. Call once at the top of a figure script (uses the Agg backend)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from cycler import cycler

    plt.rcParams.update({
        "figure.facecolor": INK["surface"], "axes.facecolor": INK["surface"],
        "savefig.facecolor": INK["surface"], "figure.dpi": 110, "savefig.bbox": "tight",
        "font.size": 10, "axes.titlesize": 11, "axes.titleweight": "bold", "axes.titlelocation": "left",
        "axes.labelcolor": INK["secondary"], "text.color": INK["primary"],
        "axes.edgecolor": INK["axis"], "axes.linewidth": 0.8,
        "axes.spines.top": False, "axes.spines.right": False,
        "xtick.color": INK["muted"], "ytick.color": INK["muted"],
        "xtick.labelcolor": INK["secondary"], "ytick.labelcolor": INK["secondary"],
        "axes.grid": True, "grid.color": INK["grid"], "grid.linewidth": 0.6, "axes.axisbelow": True,
        "lines.linewidth": 2.0, "lines.markersize": 6, "patch.linewidth": 0,
        "legend.frameon": False, "legend.fontsize": 9,
        "axes.prop_cycle": cycler(color=SERIES),
        "svg.hashsalt": "course", "svg.fonttype": "path",  # deterministic, font-independent SVG
    })


def save(fig, path: str | Path) -> Path:
    """Save as SVG (default) or PNG by extension, creating the directory. Returns the path."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, metadata={"Date": None} if path.suffix == ".svg" else None)
    import matplotlib.pyplot as plt
    plt.close(fig)
    return path
