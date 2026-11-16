"""Shared plotting style for all data figures (engineering/IEEE-like look).
Full box frame, inward ticks on all four sides, minor ticks, dashed major grid,
Times-metric serif font, solid lines with filled markers, framed legends.
Figures are drawn at their printed size, so font sizes are true point sizes."""
import matplotlib.pyplot as plt

# Same three colours and markers as Fig. 9 (blue / orange / green)
BLUE, ORANGE, GREEN, PURPLE = "#1f77b4", "#ff7f0e", "#2ca02c", "#7b4fb3"
INK, GREY = "#000000", "#555555"
MARKERS = ["o", "s", "^", "D"]


def apply():
    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["Liberation Serif", "Times New Roman", "Times", "DejaVu Serif"],
        "mathtext.fontset": "stix",
        "font.size": 8.5, "axes.labelsize": 8.5, "axes.titlesize": 9,
        "xtick.labelsize": 8, "ytick.labelsize": 8, "legend.fontsize": 7.5,
        # frame and ticks
        "axes.linewidth": 0.8, "axes.edgecolor": INK, "axes.labelcolor": INK,
        "axes.spines.top": True, "axes.spines.right": True,
        "xtick.direction": "in", "ytick.direction": "in",
        "xtick.top": True, "ytick.right": True,
        "xtick.minor.visible": True, "ytick.minor.visible": True,
        "xtick.major.size": 3.5, "ytick.major.size": 3.5,
        "xtick.minor.size": 1.8, "ytick.minor.size": 1.8,
        "xtick.major.width": 0.7, "ytick.major.width": 0.7,
        "xtick.color": INK, "ytick.color": INK,
        # grid
        "axes.grid": True, "axes.grid.which": "major", "grid.color": "#b0b0b0",
        "grid.linestyle": "--", "grid.linewidth": 0.45, "grid.alpha": 0.8, "axes.axisbelow": True,
        # lines and markers
        "lines.linewidth": 1.4, "lines.markersize": 4.2,
        "lines.markeredgewidth": 0.6, "lines.markeredgecolor": "white",
        # legend
        "legend.frameon": True, "legend.framealpha": 0.95, "legend.edgecolor": "#808080",
        "legend.fancybox": False, "legend.borderpad": 0.35, "legend.handlelength": 1.8,
        "legend.labelspacing": 0.3,
        # hatch and output
        "hatch.linewidth": 0.5, "savefig.dpi": 300, "savefig.bbox": "tight", "savefig.pad_inches": 0.02,
    })


def no_minor_y(ax):
    """For categorical (bar) axes."""
    ax.tick_params(axis="y", which="minor", left=False, right=False)
