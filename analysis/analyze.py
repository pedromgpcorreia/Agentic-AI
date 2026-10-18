"""Statistical analysis of the Consumer Choice experiments.

Uses only the outputs of the model: number of orange consumers, number of blue
consumers and consumer clustering. Writes figures to results/figures and tables to
results/tables.

Usage (from the repository root):  python analysis/analyze.py
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = f"{ROOT}/data"
FIG = f"{ROOT}/results/figures"
TAB = f"{ROOT}/results/tables"
os.makedirs(FIG, exist_ok=True)
os.makedirs(TAB, exist_ok=True)

N_CONSUMERS = 100
T_REF = 1000                       # reference horizon for the statistics
ORANGE, BLUE, CLUST = "#eb6834", "#2a78d6", "#1a1a1a"
INK2, GRID = "#52514e", "#e4e3df"
plt.rcParams.update({
    "font.family": "DejaVu Serif", "font.size": 7.5, "axes.titlesize": 8, "axes.labelsize": 7.5,
    "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 7, "figure.dpi": 150,
    "savefig.dpi": 600, "axes.edgecolor": INK2, "axes.labelcolor": "#1a1a1a",
    "xtick.color": INK2, "ytick.color": INK2, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.5, "axes.spines.top": False, "axes.spines.right": False,
    "lines.linewidth": 1.4, "legend.frameon": False, "axes.titlelocation": "left",
})
W = 4.8                            # figure width in inches (LNCS text width: 122 mm)
SUMMARY = {}


def describe(x):
    x = np.asarray(x, float)
    half = stats.t.ppf(0.975, len(x) - 1) * x.std(ddof=1) / np.sqrt(len(x))
    return {"n": len(x), "mean": x.mean(), "sd": x.std(ddof=1), "ci95_low": x.mean() - half,
            "ci95_high": x.mean() + half, "median": np.median(x), "p5": np.percentile(x, 5),
            "p95": np.percentile(x, 95), "min": x.min(), "max": x.max()}


def save(fig, name):
    fig.tight_layout(pad=0.4)
    fig.savefig(f"{FIG}/{name}.png", bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)


# =====================================================================
# Baseline
# =====================================================================
def baseline():
    d = pd.read_csv(f"{DATA}/baseline.csv.gz")
    d["orange_share"] = d.orange / N_CONSUMERS
    d["blue_share"] = d.blue / N_CONSUMERS
    runs = d.run.nunique()

    # Table: statistics of the three outputs at the reference horizon
    fin = d[d.tick == T_REF]
    rows = {"Orange market share": describe(fin.orange_share),
            "Blue market share": describe(fin.blue_share),
            "Consumer clustering": describe(fin.clustering)}
    tab = pd.DataFrame(rows).T
    tab.round(3).to_csv(f"{TAB}/baseline_tick{T_REF}.csv")
    SUMMARY["baseline"] = {k: {a: float(b) for a, b in v.items()} for k, v in rows.items()}

    # outcome of the market, read from the market shares
    s = fin.orange_share
    SUMMARY["baseline_outcomes"] = {
        "runs": int(runs),
        "pct_runs_orange_majority": float((s > 0.5).mean() * 100),
        "pct_runs_blue_majority": float((s < 0.5).mean() * 100),
        "pct_runs_tie": float((s == 0.5).mean() * 100),
        "pct_runs_one_product_ge_90pct": float(((s >= 0.9) | (s <= 0.1)).mean() * 100),
        "pct_runs_share_between_40_60": float(((s >= 0.4) & (s <= 0.6)).mean() * 100),
        "pct_runs_one_product_100pct": float(((s == 1) | (s == 0)).mean() * 100),
    }

    # Horizon check: mean outputs at several ticks
    hz = []
    for t in [0, 100, 250, 500, 750, 1000, 1500, 2000]:
        g = d[d.tick == t]
        hz.append({"tick": t, "clustering_mean": g.clustering.mean(),
                   "clustering_sd": g.clustering.std(ddof=1),
                   "orange_share_mean": g.orange_share.mean(),
                   "orange_share_sd": g.orange_share.std(ddof=1)})
    hz = pd.DataFrame(hz)
    hz.round(4).to_csv(f"{TAB}/baseline_horizon.csv", index=False)
    SUMMARY["baseline_horizon"] = hz.round(4).to_dict(orient="records")

    # ---- Figure 1: time series and distribution ----
    fig, axs = plt.subplots(1, 3, figsize=(W, 1.75))
    order = fin.sort_values("orange_share").run.values
    for r, a in zip(order[[int(0.05 * runs), runs // 2, int(0.95 * runs)]], [0.35, 0.65, 1.0]):
        x = d[(d.run == r) & (d.tick <= T_REF)]
        axs[0].plot(x.tick, x.orange_share, color=ORANGE, alpha=a, linewidth=0.9)
    axs[0].set(title="(a) Three runs", xlabel="tick", ylabel="orange share", ylim=(0, 1))
    g = d[d.tick <= T_REF].groupby("tick")
    for col, color, lab in [("clustering", CLUST, "clustering"), ("orange_share", ORANGE, "orange share")]:
        axs[1].fill_between(g[col].mean().index, g[col].quantile(0.05), g[col].quantile(0.95),
                            color=color, alpha=0.13, linewidth=0)
        axs[1].plot(g[col].mean().index, g[col].mean(), color=color, label=lab)
    axs[1].set(title="(b) Mean, P5–P95", xlabel="tick", ylim=(0, 1))
    axs[1].legend(loc="lower right")
    axs[2].hist(fin.orange_share, bins=np.linspace(0, 1, 11), color=ORANGE, edgecolor="white", linewidth=1)
    axs[2].set(title=f"(c) Tick {T_REF}", xlabel="orange share", ylabel="runs")
    save(fig, "fig1_baseline")

    # ---- Figure 2: number of runs (precision of the estimates) ----
    rng = np.random.default_rng(0)
    ns = np.unique(np.round(np.logspace(1, np.log10(runs), 25)).astype(int))
    fig, axs = plt.subplots(1, 2, figsize=(W, 1.7))
    conv = []
    for ax, col, color, lab in [(axs[0], "orange_share", ORANGE, "orange share"),
                                (axs[1], "clustering", CLUST, "clustering")]:
        x = fin[col].values[rng.permutation(runs)]
        means = [x[:n].mean() for n in ns]
        half = [stats.t.ppf(0.975, n - 1) * x[:n].std(ddof=1) / np.sqrt(n) for n in ns]
        ax.fill_between(ns, np.array(means) - half, np.array(means) + half, color=color, alpha=0.15, linewidth=0)
        ax.plot(ns, means, color=color)
        ax.set_xscale("log")
        ax.set(title=f"({'a' if col == 'orange_share' else 'b'}) {lab.capitalize()}", ylabel="mean (95% CI)",
               xlabel="number of runs")
        conv += [{"output": col, "runs": int(n), "mean": m, "ci95_halfwidth": h} for n, m, h in zip(ns, means, half)]
    save(fig, "fig2_number_of_runs")
    pd.DataFrame(conv).round(4).to_csv(f"{TAB}/baseline_number_of_runs.csv", index=False)
    SUMMARY["ci_halfwidth_at_100_runs"] = {c["output"]: c["ci95_halfwidth"] for c in conv if c["runs"] == 100}
    SUMMARY["ci_halfwidth_at_all_runs"] = {c["output"]: c["ci95_halfwidth"] for c in conv if c["runs"] == runs}


# =====================================================================
# Sensitivity analysis
# =====================================================================
LABEL = {"norm_influence": "norm-influence", "quality_blue": "quality-blue",
         "exploration": "exploration"}


def sensitivity(name, fig_no):
    d = pd.read_csv(f"{DATA}/{name}.csv.gz")
    d["orange_share"] = d.orange / N_CONSUMERS
    rows = []
    for v, g in d.groupby(name):
        o, c = describe(g.orange_share), describe(g.clustering)
        rows.append({name: v, "runs": len(g),
                     "orange_mean": o["mean"], "orange_sd": o["sd"], "orange_p5": o["p5"], "orange_p95": o["p95"],
                     "clustering_mean": c["mean"], "clustering_sd": c["sd"],
                     "clustering_ci95_low": c["ci95_low"], "clustering_ci95_high": c["ci95_high"]})
    tab = pd.DataFrame(rows)
    tab.round(3).to_csv(f"{TAB}/sensitivity_{name}.csv", index=False)
    SUMMARY[f"sensitivity_{name}"] = tab.round(4).to_dict(orient="records")

    vals = sorted(d[name].unique())
    fig, axs = plt.subplots(1, 2, figsize=(W, 1.75))
    bp = axs[0].boxplot([d[d[name] == v].orange_share for v in vals], positions=range(len(vals)),
                        widths=0.55, patch_artist=True, showfliers=True,
                        flierprops=dict(marker=".", markersize=2, markeredgecolor=INK2),
                        medianprops=dict(color="#1a1a1a", linewidth=1),
                        whiskerprops=dict(color=INK2, linewidth=0.7), capprops=dict(color=INK2, linewidth=0.7))
    for b in bp["boxes"]:
        b.set(facecolor=ORANGE, alpha=0.55, edgecolor=INK2, linewidth=0.6)
    axs[0].set_xticks(range(len(vals)), [f"{v:g}" for v in vals])
    axs[0].set(title="(a) Orange share", xlabel=LABEL[name], ylim=(-0.03, 1.03))
    axs[1].errorbar(range(len(vals)), tab.clustering_mean,
                    yerr=[tab.clustering_mean - tab.clustering_ci95_low, tab.clustering_ci95_high - tab.clustering_mean],
                    color=CLUST, marker="o", markersize=3, capsize=2, linewidth=1)
    axs[1].set_xticks(range(len(vals)), [f"{v:g}" for v in vals])
    axs[1].set(title="(b) Clustering (mean, 95% CI)", xlabel=LABEL[name], ylim=(0.4, 1.02))
    if name == "norm_influence":
        for ax in axs:
            ax.tick_params(axis="x", labelsize=6.5)
    save(fig, f"fig{fig_no}_sensitivity_{name}")


if __name__ == "__main__":
    baseline()
    for i, n in enumerate(["norm_influence", "quality_blue", "exploration"], start=3):
        if os.path.exists(f"{DATA}/{n}.csv.gz"):
            sensitivity(n, i)
    json.dump(SUMMARY, open(f"{TAB}/summary.json", "w"), indent=2, default=float)
    print(json.dumps(SUMMARY, indent=1, default=lambda o: round(float(o), 4))[:7000])
