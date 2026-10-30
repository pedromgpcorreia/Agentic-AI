"""Analysis of phases 3-4 (fixed prices vs learned prices).

Reads results/pricing/ (experiments/run_pricing.py) and writes figures to
results/pricing/figures and tables to results/pricing/tables.
All comparisons are paired by seed (common random numbers).

Usage (repository root):  python analysis/analyze_pricing.py [results folder]
"""
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IN = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else f"{ROOT}/results/pricing"
FIG, TAB = f"{IN}/figures", f"{IN}/tables"
os.makedirs(FIG, exist_ok=True)
os.makedirs(TAB, exist_ok=True)

OPS = ["MEO", "NOS", "Vodafone"]
BASE = {"MEO": 42.49, "NOS": 42.49, "Vodafone": 40.50}
COL = {"MEO": "#2a78d6", "NOS": "#eb6834", "Vodafone": "#1a9e77", "DIGI": "#7a3fbf"}
INK2, GRID = "#52514e", "#e4e3df"
MAIN = "bandit_e0.10_a0.2"
ENTRY = 12
plt.rcParams.update({
    "font.family": "DejaVu Serif", "font.size": 7.5, "axes.titlesize": 8, "axes.labelsize": 7.5,
    "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 7, "figure.dpi": 150,
    "savefig.dpi": 600, "axes.edgecolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.5, "axes.spines.top": False,
    "axes.spines.right": False, "lines.linewidth": 1.4, "legend.frameon": False,
    "axes.titlelocation": "left",
})
W = 4.8


def ci(x):
    x = np.asarray(x, float)
    h = stats.t.ppf(0.975, len(x) - 1) * x.std(ddof=1) / np.sqrt(len(x))
    return x.mean(), x.mean() - h, x.mean() + h


def save(fig, name):
    fig.tight_layout(pad=0.4)
    fig.savefig(f"{FIG}/{name}.png", bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)


runs = pd.read_csv(f"{IN}/runs.csv")
series = pd.read_csv(f"{IN}/series.csv.gz")
log = pd.read_csv(f"{IN}/bandit_log.csv.gz")
summary = {}

# ---------------------------------------------------------------- table 1: all scenarios
metrics = ["profit_incumbents"] + [f"profit_{o}" for o in OPS] + ["share_DIGI_end",
                                                                  "avg_price_paid_end", "switches_year"]
rows = []
for sc, g in runs.groupby("scenario"):
    r = {"scenario": sc, "n": len(g)}
    for mtr in metrics:
        m, lo, hi = ci(g[mtr])
        r[mtr], r[mtr + "_lo"], r[mtr + "_hi"] = m, lo, hi
    rows.append(r)
tab = pd.DataFrame(rows).set_index("scenario")
tab.to_csv(f"{TAB}/scenarios.csv")

# ---------------------------------------------------------------- table 2: paired differences
ref = runs[runs.scenario == "fixed_1.00"].set_index("seed")
diff_rows = []
for sc, g in runs.groupby("scenario"):
    g = g.set_index("seed").loc[ref.index]
    r = {"scenario": sc}
    for o in OPS + ["incumbents"]:
        d = (g[f"profit_{o}"] - ref[f"profit_{o}"]) / ref[f"profit_{o}"] * 100
        m, lo, hi = ci(d)
        p = stats.ttest_1samp(d, 0).pvalue if d.std() > 0 else np.nan
        r.update({f"dprofit_{o}_pct": m, f"dprofit_{o}_lo": lo, f"dprofit_{o}_hi": hi,
                  f"p_{o}": p})
    diff_rows.append(r)
diff = pd.DataFrame(diff_rows).set_index("scenario")
diff.to_csv(f"{TAB}/paired_vs_fixed_1.00.csv")

# ---------------------------------------------------------------- best responses
br = {}
for o in OPS:
    br[o] = {x: float(diff.loc[f"solo_{o}_{x:.2f}", f"dprofit_{o}_pct"]) for x in (0.90, 0.80)}
summary["unilateral_cut_own_profit_change_pct"] = br

# ---------------------------------------------------------------- figure 1: DIGI share
fig, ax = plt.subplots(figsize=(W, 2.3))
for sc, lab, ls in [("no_entry", "No entry (NOWO)", ":"), ("fixed_1.00", "Fixed list prices", "-"),
                    ("fixed_0.90", "Fixed, all at 0.90", "--"), (MAIN, "Learned prices (bandit)", "-")]:
    s = series[series.scenario == sc]
    ax.plot(s.month, s.share_DIGI * 100, ls, label=lab,
            color=COL["DIGI"] if sc == MAIN else INK2 if sc != "fixed_0.90" else "#999")
ax.scatter([19, 25, 28], [2.8, 3.0, 3.2], color="k", s=10, zorder=5, label="ANACOM")
ax.axvline(ENTRY, color=GRID, lw=1)
ax.set(xlabel="Month (0 = Nov. 2023)", ylabel="NOWO/DIGI share (%)")
ax.legend(ncol=2)
save(fig, "digi_share")

# ---------------------------------------------------------------- figure 2: learned prices
fig, axes = plt.subplots(1, 2, figsize=(W, 2.2), gridspec_kw={"width_ratios": [1.4, 1]})
s = series[series.scenario == MAIN]
for o in OPS:
    axes[0].plot(s.month, s[f"price_{o}"] / BASE[o], color=COL[o], label=o)
axes[0].axvline(ENTRY, color=GRID, lw=1)
axes[0].set(xlabel="Month", ylabel="Mean price / list price", ylim=(0.78, 1.02))
axes[0].legend()
late = log[(log.scenario == MAIN) & (log.month > ENTRY + 60)]
freq = late.groupby("operator").new_arm.value_counts(normalize=True).unstack().reindex(OPS)
arms = sorted(freq.columns, reverse=True)
bottom = np.zeros(len(OPS))
shades = ["#1a1a1a", "#52514e", "#8a8985", "#bdbcb8", "#e4e3df"]
for a, c in zip(arms, shades):
    axes[1].bar(OPS, freq[a].values * 100, bottom=bottom, color=c, label=f"{a:.2f}")
    bottom += freq[a].values * 100
axes[1].set(ylabel="Share of decisions, years 6-10 (%)")
axes[1].legend(title="Arm", fontsize=6, title_fontsize=6, loc="upper left", bbox_to_anchor=(1, 1))
axes[1].grid(axis="x")
save(fig, "learned_prices")

# ---------------------------------------------------------------- figure 3: profit by scenario
fig, ax = plt.subplots(figsize=(W, 2.3))
levels = [1.00, 0.95, 0.90, 0.85, 0.80]
for o in OPS:
    ys = [tab.loc[f"fixed_{x:.2f}", f"profit_{o}"] / 1e3 for x in levels]
    ax.plot(levels, ys, "o-", color=COL[o], ms=3, label=f"{o}, fixed (all equal)")
    m, lo, hi = tab.loc[MAIN, [f"profit_{o}", f"profit_{o}_lo", f"profit_{o}_hi"]] / 1e3
    pm = s[f"price_{o}"].iloc[ENTRY + 1:].mean() / BASE[o]
    ax.errorbar([pm], [m], yerr=[[m - lo], [hi - m]], fmt="*", color=COL[o], ms=7)
ax.invert_xaxis()
ax.set(xlabel="Price multiplier of the incumbents (* = bandit, at its mean multiplier)",
       ylabel="Cumulative profit, 10 years (EUR k)")
ax.legend(fontsize=6)
save(fig, "profit_by_scenario")

# ---------------------------------------------------------------- sensitivity (epsilon, alpha)
sens = tab[tab.index.str.startswith("bandit")][["profit_incumbents", "share_DIGI_end",
                                                 "avg_price_paid_end"]].copy()
sens["mean_multiplier"] = [
    np.mean([series[series.scenario == sc][f"price_{o}"].iloc[ENTRY + 1:].mean() / BASE[o]
             for o in OPS]) for sc in sens.index]
sens.to_csv(f"{TAB}/bandit_sensitivity.csv")

summary["scenarios"] = tab[["profit_incumbents", "share_DIGI_end", "avg_price_paid_end"]].round(3).to_dict()
summary["bandit_sensitivity"] = sens.round(3).to_dict()
summary["paired_incumbents_pct"] = diff[["dprofit_incumbents_pct", "dprofit_incumbents_lo",
                                         "dprofit_incumbents_hi"]].round(2).to_dict()
json.dump(summary, open(f"{TAB}/summary.json", "w"), indent=1)
print(tab[["profit_incumbents", "profit_MEO", "profit_NOS", "profit_Vodafone", "share_DIGI_end",
           "avg_price_paid_end"]].round(3).to_string())
print(diff[[c for c in diff.columns if c.startswith("dprofit") and c.endswith("pct")]].round(2).to_string())
print(sens.round(3).to_string())
print(json.dumps(br, indent=1))
