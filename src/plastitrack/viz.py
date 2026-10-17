"""Shared chart colors + matplotlib style, so notebook figures and the app look the same.

Palette: colorblind-validated categorical order (fixed, never cycled) and a single-hue
blue ramp for ordered magnitudes like plastic level.
"""
import matplotlib as mpl

CATEGORICAL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]

# plastic level is ordinal -> sequential light-to-dark blue
LEVEL_COLORS = {"none": "#b7d3f6", "low": "#6da7ec", "medium": "#2a78d6", "high": "#104281"}

# plastic type is identity -> categorical slots in fixed order
TYPE_COLORS = {"none": "#b5b4ad", "PET": CATEGORICAL[0], "HDPE": CATEGORICAL[1], "PP": CATEGORICAL[2],
               "film": CATEGORICAL[3], "mixed_other": CATEGORICAL[6]}

SURFACE = "#fcfcfb"
TEXT = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
GRID = "#e4e3df"


def apply_style():
    """Recessive axes and grid, thin marks, readable text."""
    mpl.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "axes.edgecolor": GRID, "axes.labelcolor": TEXT_SECONDARY, "axes.titlecolor": TEXT,
        "axes.titlesize": 13, "axes.titleweight": "bold", "axes.titlelocation": "left",
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
        "xtick.color": TEXT_SECONDARY, "ytick.color": TEXT_SECONDARY,
        "font.size": 11, "legend.frameon": False,
        "axes.prop_cycle": mpl.cycler(color=CATEGORICAL),
    })
