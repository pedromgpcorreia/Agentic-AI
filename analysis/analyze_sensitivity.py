"""Analysis of task 6: do the conclusions of task 5 survive the modelling choices?

Reads results/sensitivity/runs.csv (experiments/run_sensitivity.py) and writes
results/sensitivity/tables/summary.csv and results/sensitivity/figures/sensitivity.png.
All comparisons are paired by seed against fixed_1.00 of the same variant.

For each variant:
  * DIGI share at month 28 (ANACOM: 3.2 %) and after 10 years at list prices;
  * change in each incumbent's own profit when it alone cuts to 0.90 (a positive value
    means that keeping the list price is not a best response);
  * change in the incumbents' joint profit and mean price multiplier with the bandit.

Usage (repository root):  python analysis/analyze_sensitivity.py [results folder]
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IN = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else f"{ROOT}/results/sensitivity"
FIG, TAB = f"{IN}/figures", f"{IN}/tables"
os.makedirs(FIG, exist_ok=True)
os.makedirs(TAB, exist_ok=True)

OPS = ["MEO", "NOS", "Vodafone"]
BASE = {"MEO": 42.49, "NOS": 42.49, "Vodafone": 40.50}
COL = {"MEO": "#2a78d6", "NOS": "#eb6834", "Vodafone": "#1a9e77", "DIGI": "#7a3fbf"}
INK2, GRID = "#52514e", "#e4e3df"
LABELS = {"base": "Calibrated model", "kappa_0.10": "Quality spread κ = 0.10",
          "kappa_0.30": "Quality spread κ = 0.30", "exit_0.3%": "Exits 0.3 %/month",
          "exit_1%": "Exits 1 %/month", "contracted_50%": "Initially contracted 50 %",
          "contracted_90%": "Initially contracted 90 %", "discount_17.8%": "Renewal discount 17.8 %",
          "lock_in": "Full lock-in (no early exit)", "margin_60%": "Margin 60 %"}
plt.rcParams.update({
    "font.family": "DejaVu Serif", "font.size": 7.5, "axes.titlesize": 8, "axes.labelsize": 7.5,
    "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 7, "figure.dpi": 150,
    "savefig.dpi": 600, "axes.edgecolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.5, "axes.spines.top": False,
    "axes.spines.right": False, "lines.linewidth": 1.4, "legend.frameon": False,
    "axes.titlelocation": "left",
})


def ci(x):
    x = np.asarray(x, float)
    h = stats.t.ppf(0.975, len(x) - 1) * x.std(ddof=1) / np.sqrt(len(x))
    return x.mean(), x.mean() - h, x.mean() + h


def paired_pct(g, ref, col):
    g = g.set_index("seed").loc[ref.index]
    return ci((g[col] - ref[col]) / ref[col] * 100)


runs = pd.read_csv(f"{IN}/runs.csv")
variants = [v for v in LABELS if v in set(runs.variant)]
rows = []
for v in variants:
    r = runs[runs.variant == v]
    ref = r[r.scenario == "fixed_1.00"].set_index("seed")
    band = r[r.scenario == "bandit"]
    row = {"variant": v, "label": LABELS[v], "seeds": len(ref),
           "digi_m28_pct": ref.share_DIGI_m28.mean() * 100,
           "digi_10y_list_pct": ref.share_DIGI_end.mean() * 100,
           "digi_10y_bandit_pct": band.share_DIGI_end.mean() * 100}
    for o in OPS:
        m, lo, hi = paired_pct(r[r.scenario == f"solo_{o}_0.90"], ref, f"profit_{o}")
        row.update({f"solo_{o}_pct": m, f"solo_{o}_lo": lo, f"solo_{o}_hi": hi})
    m, lo, hi = paired_pct(band, ref, "profit_incumbents")
    row.update({"bandit_joint_pct": m, "bandit_joint_lo": lo, "bandit_joint_hi": hi})
    row["bandit_multiplier"] = np.mean([(band[f"price_{o}_mean"] / BASE[o]).mean() for o in OPS])
    row["list_price_not_equilibrium"] = any(row[f"solo_{o}_lo"] > 0 for o in OPS)
    rows.append(row)
tab = pd.DataFrame(rows).set_index("variant")
tab.to_csv(f"{TAB}/summary.csv")

# ---------------------------------------------------------------- figure
fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.2), sharey=True,
                         gridspec_kw={"width_ratios": [1.3, 1]})
y = np.arange(len(variants))[::-1]
for j, o in enumerate(OPS):
    off = (j - 1) * 0.22
    m = tab[f"solo_{o}_pct"].values
    axes[0].errorbar(m, y + off, xerr=[m - tab[f"solo_{o}_lo"].values, tab[f"solo_{o}_hi"].values - m],
                     fmt="o", ms=3, color=COL[o], elinewidth=0.8, label=o)
axes[0].axvline(0, color=INK2, lw=0.8)
axes[0].set(xlabel="Own profit, alone at 0.90 (% vs list)",
            title="Cutting alone: profitable if > 0")
axes[0].set_yticks(y, [LABELS[v] for v in variants])
axes[0].legend(loc="lower right")
m = tab.bandit_joint_pct.values
axes[1].errorbar(m, y, xerr=[m - tab.bandit_joint_lo.values, tab.bandit_joint_hi.values - m],
                 fmt="o", ms=3.5, color=COL["DIGI"], elinewidth=0.8)
for yi, (mi, mult) in enumerate(zip(m, tab.bandit_multiplier.values)):
    axes[1].annotate(f"×{mult:.2f}", (mi, y[yi]), xytext=(5, 3), textcoords="offset points",
                     fontsize=6, color=INK2)
axes[1].axvline(0, color=INK2, lw=0.8)
axes[1].set(xlabel="Joint incumbent profit (% vs list)",
            title="Learned prices (× = mean price multiplier)")
fig.tight_layout(pad=0.4)
fig.savefig(f"{FIG}/sensitivity.png", bbox_inches="tight", pad_inches=0.03)
plt.close(fig)

pd.set_option("display.width", 200)
print(tab[["digi_m28_pct", "digi_10y_list_pct", "digi_10y_bandit_pct", "solo_MEO_pct", "solo_NOS_pct",
           "solo_Vodafone_pct", "bandit_joint_pct", "bandit_joint_lo", "bandit_joint_hi",
           "bandit_multiplier", "list_price_not_equilibrium"]].round(2).to_string())
