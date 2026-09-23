"""
Shared figure palette + typography for the CAC manuscript, matching the
CONSORT flowchart (Figure 1): grey data / salmon process / teal output,
serif (Times) type. Imported by scripts 22 and 25 so all six figures agree.
"""
import matplotlib

INK, MUT, LINE = "#1a1a1a", "#555555", "#333333"
# data / neutral
GREY_F, GREY_S, GREY_E = "#ededed", "#c2c5ca", "#d6d6d6"
# process / WARM accent = muted dusty rose  (SALM_* names kept for back-compat)
SALM_F, SALM_S, SALM_E, WARM_TX = "#f1e0e3", "#b27b86", "#e3c7cd", "#8a5560"
# output / COOL accent = muted slate blue   (TEAL_* names kept for back-compat)
TEAL_F, TEAL_S, TEAL_E, COOL_TX = "#dfe5ec", "#5c7997", "#c7d3df", "#3d5674"


def apply():
    matplotlib.rcParams.update({
        "font.family": "serif",
        "font.serif": ["Times New Roman", "DejaVu Serif"],
        "text.color": INK,
        "axes.edgecolor": LINE,
        "axes.labelcolor": INK,
        "xtick.color": INK,
        "ytick.color": INK,
        "axes.titlecolor": INK,
    })
