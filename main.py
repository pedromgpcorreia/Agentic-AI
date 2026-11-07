"""Runs every simulation of the report and prints its results (single entry point).

What it does
    Runs the original and the new model with the same parameters and random seeds as the
    report, so the printed numbers are the ones in the report:
      Part 1  original Consumer Choice model (tasks 1 and 2): baseline, 1000 runs x 2000
              ticks, and sensitivity of norm_influence, quality_blue and exploration, 100
              runs per value x 1000 ticks (tables 7 to 11)
      Part 2  new model, DIGI's entry with learning incumbents (tasks 3 to 5): 23 price
              scenarios x 30 runs x 132 months, 12 before the entry and 10 years after it
              (calibration, tables 15 and 16, learned prices)
      Part 3  sensitivity analysis of the new model (task 6): base and 9 variants x 5
              scenarios x 20 runs (table 17)

Files it needs
    Only the project folder as delivered, with main.py at its top level. All paths are
    relative to this file, so the folder can be anywhere on the computer:
        main.py
        consumer_choice/   the models: model.py (original), telecom.py, learning.py and
                           calibrated.py (new)
        experiments/       scenario definitions reused here: run_experiments.py,
                           run_pricing.py and run_sensitivity.py
    It reads no data files and writes only main_output.txt, next to this file. The folders
    data/ and results/ are not needed and are not changed.

Requirements
    Python 3.12 or later (required by Mesa 3.5) and the packages in requirements.txt:
        pip install -r requirements.txt

How to run
    VS Code: open the project folder (File > Open Folder), select the Python interpreter
    where the requirements are installed, open main.py and press Run.
    Terminal, from the project folder:
        python main.py            # all three parts
        python main.py 2          # only part 2
        python main.py 1 3        # parts 1 and 3

Time
    All CPU cores are used. On 8 cores the three parts take about 7, 6 and 7 minutes. The
    progress of each part is shown while it runs.
"""
import os
import sys
import time
import warnings
from decimal import ROUND_HALF_UP, Decimal
from multiprocessing import Pool

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")    # minus signs on Windows consoles

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats  # noqa: E402

from consumer_choice.model import ConsumerChoiceModel  # noqa: E402
from experiments import run_experiments, run_pricing, run_sensitivity  # noqa: E402

OPS = ("MEO", "NOS", "Vodafone")
LIST_PRICE = {"MEO": 42.49, "NOS": 42.49, "Vodafone": 40.50}
ANACOM = {19: 2.8, 25: 3.0, 28: 3.2}            # NOWO/DIGI share (%), ANACOM
TICKS_SHOWN = (0, 100, 250, 500, 750, 1000, 1500, 2000)
OUT = []


def say(text=""):
    print(text, flush=True)
    OUT.append(text)


def r(x, d=3):
    """Round half up on the decimal value, as in the report (0.5065 -> 0.507)."""
    return str(Decimal(repr(round(float(x), 9))).quantize(Decimal(1).scaleb(-d), ROUND_HALF_UP))


def sg(x, d=1):
    return ("+" if x >= 0 else "−") + r(abs(x), d)


def ci(x):
    x = np.asarray(x, float)
    h = stats.t.ppf(0.975, len(x) - 1) * x.std(ddof=1) / np.sqrt(len(x))
    return x.mean(), x.mean() - h, x.mean() + h


def table(header, rows):
    w = [max(len(str(c)) for c in col) for col in zip(header, *rows)]
    for k, row in enumerate([header] + rows):
        say("  " + "  ".join(str(c).ljust(w[j]) if j == 0 else str(c).rjust(w[j])
                             for j, c in enumerate(row)))
        if k == 0:
            say("  " + "  ".join("-" * n for n in w))


def pool_map(f, jobs, label):
    """Runs the jobs on all cores, in order, and shows the progress (not saved to the file)."""
    res, n, t = [], len(jobs), time.time()
    with Pool() as pool:
        for i, x in enumerate(pool.imap(f, jobs, chunksize=4), 1):
            res.append(x)
            if i % max(1, n // 10) == 0 or i == n:
                print(f"    {label}: {i} of {n} runs ({time.time() - t:.0f} s)", flush=True)
    return res


# ======================================================================== part 1
def run_baseline(args):
    """One run of the original model; outputs at the ticks shown in the report."""
    params, seed, ticks = args
    m = ConsumerChoiceModel(rng=seed, **params)
    for _ in range(ticks):
        m.step()
    df = m.datacollector.get_model_vars_dataframe()
    return {t: (df.orange[t] / 100, df.clustering[t]) for t in TICKS_SHOWN if t <= ticks}


def part1():
    say("PART 1. Original Consumer Choice model (tasks 1 and 2)\n")
    _, _, runs, ticks, seed0, _ = run_experiments.EXPERIMENTS["baseline"]
    res = pool_map(run_baseline, [(run_experiments.BASELINE, s, ticks) for s in range(seed0, seed0 + runs)],
                   "baseline")
    o = np.array([x[1000][0] for x in res])
    c = np.array([x[1000][1] for x in res])
    say(f"Table 7. Baseline outputs at tick 1000 ({runs} runs, seeds {seed0} to {seed0 + runs - 1}).")
    rows = []
    for name, x in [("Orange market share", o), ("Blue market share", 1 - o), ("Clustering", c)]:
        m, lo, hi = ci(x)
        rows.append([name, r(m), r(x.std(ddof=1)), f"{r(lo)} to {r(hi)}", r(np.median(x)),
                     r(np.percentile(x, 5), 2), r(np.percentile(x, 95), 2)])
    table(["Output", "Mean", "SD", "95% CI", "Median", "P5", "P95"], rows)
    say(f"  Runs with orange majority {(o > .5).mean() * 100:.1f}%, blue majority "
        f"{(o < .5).mean() * 100:.1f}%, ties {(o == .5).mean() * 100:.1f}%; shares between 0.40 and "
        f"0.60 in {((o >= .4) & (o <= .6)).mean() * 100:.0f}% of the runs.\n")
    say("Table 8. Mean and SD of the outputs over time (baseline).")
    rows = []
    for t in TICKS_SHOWN:
        ot = np.array([x[t][0] for x in res])
        ct = np.array([x[t][1] for x in res])
        rows.append([t, r(ct.mean()), r(ct.std(ddof=1)), r(ot.mean()), r(ot.std(ddof=1))])
    table(["Tick", "Clustering mean", "Clustering SD", "Orange mean", "Orange SD"], rows)
    for k, name in enumerate(["norm_influence", "quality_blue", "exploration"]):
        var, values, runs, ticks, seed0, _ = run_experiments.EXPERIMENTS[name]
        jobs = [(dict(run_experiments.BASELINE, **{var: v}), s, ticks)
                for v in values for s in range(seed0, seed0 + runs)]
        res = pool_map(run_baseline, jobs, name)
        say(f"\nTable {9 + k}. Outputs at tick 1000 as a function of {var} ({runs} runs per value).")
        rows = []
        for i, v in enumerate(values):
            part = res[i * runs:(i + 1) * runs]
            ov = np.array([x[1000][0] for x in part])
            cv = np.array([x[1000][1] for x in part])
            m, lo, hi = ci(cv)
            rows.append([f"{v:g}", r(ov.mean()), r(ov.std(ddof=1)), r(m), f"{r(lo)} to {r(hi)}"])
        table([var, "Orange mean", "Orange SD", "Clustering mean", "Clustering 95% CI"], rows)


# ======================================================================== part 2
def part2():
    say("\nPART 2. New model: DIGI entry and learning incumbents (tasks 3 to 5)\n")
    sc = run_pricing.scenarios()
    seeds = list(run_pricing.SEEDS)
    out = pool_map(run_pricing.run, [(n, s, seed) for n, s in sc.items() for seed in seeds], "price scenarios")
    runs = pd.DataFrame([o[0] for o in out])
    series = pd.concat([o[1] for o in out])
    logs = pd.concat([o[2] for o in out if o[2] is not None])
    ref = runs[runs.scenario == "fixed_1.00"].set_index("seed")

    def paired(name, col="profit_incumbents"):
        g = runs[runs.scenario == name].set_index("seed").loc[ref.index]
        return ci((g[col] - ref[col]) / ref[col] * 100)

    fx = series[series.scenario == "fixed_1.00"].groupby("month").mean(numeric_only=True)
    cal = {t: fx.share_DIGI[t] * 100 for t in ANACOM}
    rmse = np.sqrt(np.mean([(cal[t] - v) ** 2 for t, v in ANACOM.items()]))
    say(f"Calibration ({len(seeds)} runs, seeds {seeds[0]} to {seeds[-1]}): NOWO/DIGI share")
    table(["Month", "Model", "ANACOM"], [[t, f"{cal[t]:.1f}%", f"{v:.1f}%"] for t, v in ANACOM.items()])
    say(f"  RMSE {rmse:.2f} percentage points. Incumbents at month 28: "
        + ", ".join(f"{o} {fx[f'share_{o}'][28] * 100:.1f}%" for o in OPS) + "\n")

    say("Table 15. Joint profit of the incumbents over 10 years after the entry, % against all at "
        "list price (paired by seed), DIGI share in year 10, average price paid in year 10.")
    rows = []
    for name, lab in [("no_entry", "No entry"), ("fixed_1.00", "All at list price"),
                      ("bandit_e0.10_a0.2", "Learned, every 3 months"), ("bandit_p6", "Learned, every 6 months"),
                      ("bandit_p12", "Learned, every 12 months"), ("fixed_0.95", "All at x0.95"),
                      ("fixed_0.90", "All at x0.90"), ("fixed_0.85", "All at x0.85"), ("fixed_0.80", "All at x0.80")]:
        g = runs[runs.scenario == name]
        m, lo, hi = paired(name)
        rows.append([lab, "0.0" if name == "fixed_1.00" else sg(m),
                     "reference" if name == "fixed_1.00" else f"{sg(lo)} to {sg(hi)}",
                     "n/a" if name == "no_entry" else r(g.share_DIGI_end.mean() * 100, 1),
                     r(g.avg_price_paid_end.mean(), 2)])
    table(["Scenario", "Profit (%)", "95% CI", "DIGI (%)", "Price (EUR)"], rows)

    say("\nTable 16. Own profit of each incumbent over 10 years, % against all at list price (95% CI).")
    rows = []
    for o in OPS:
        cells = [o]
        for name in (f"solo_{o}_0.90", "fixed_0.90", f"solo_{o}_0.80"):
            m, lo, hi = paired(name, f"profit_{o}")
            cells.append(f"{sg(m)}% ({sg(lo)} to {sg(hi)})")
        rows.append(cells)
    table(["Incumbent", "Cuts alone to x0.90", "All cut to x0.90", "Cuts alone to x0.80"], rows)

    say("\nLearned prices (bandit, epsilon 0.1, alpha 0.2, decisions every 3 months)")
    late = logs[(logs.scenario == "bandit_e0.10_a0.2") & (logs.month > 72)]
    say("  List price chosen in years 6 to 10: " + ", ".join(
        f"{o} {(late[late.operator == o].new_arm == 1).mean() * 100:.0f}%" for o in OPS)
        + f"; {(late[~late.explored].new_arm == 1).mean() * 100:.0f}% of the decisions without exploration")
    rows = []
    for name in [n for n in sc if n.startswith("bandit")]:
        g = runs[runs.scenario == name]
        mult = np.mean([(g[f"price_{o}_mean"] / LIST_PRICE[o]).mean() for o in OPS])
        rows.append([name, sg(paired(name)[0]), r(mult, 2), r(g.share_DIGI_end.mean() * 100, 1)])
    table(["Bandit scenario", "Joint profit (%)", "Mean multiplier", "DIGI y10 (%)"], rows)


# ======================================================================== part 3
def part3():
    say("\nPART 3. Sensitivity analysis of the new model (task 6)\n")
    sc = run_sensitivity.scenarios()
    seeds = list(run_sensitivity.SEEDS)
    jobs = [(v, n, p, seed) for v in run_sensitivity.VARIANTS for n, p in sc.items() for seed in seeds]
    runs = pd.DataFrame(pool_map(run_sensitivity.run, jobs, "sensitivity"))
    say(f"Table 17. Sensitivity analysis ({len(seeds)} runs per scenario). Own profit of a solo cut to "
        "x0.90 and joint profit with learned prices, % against all at list price; DIGI share at "
        "month 28 (ANACOM 3.2%) and in year 10 with list prices.")
    rows = []
    for v in run_sensitivity.VARIANTS:
        g = runs[runs.variant == v]
        ref = g[g.scenario == "fixed_1.00"].set_index("seed")

        def paired(name, col):
            x = g[g.scenario == name].set_index("seed").loc[ref.index]
            return ci((x[col] - ref[col]) / ref[col] * 100)[0]

        rows.append([v] + [sg(paired(f"solo_{o}_0.90", f"profit_{o}")) for o in OPS]
                    + [sg(paired("bandit", "profit_incumbents")),
                       r(ref.share_DIGI_m28.mean() * 100, 1), r(ref.share_DIGI_end.mean() * 100, 1)])
    table(["Variant", "MEO solo", "NOS solo", "Vod. solo", "Learned", "DIGI m28", "DIGI y10"], rows)


if __name__ == "__main__":
    parts = [a for a in sys.argv[1:] if a in "123"] or ["1", "2", "3"]
    start = time.time()
    for p in parts:
        t = time.time()
        {"1": part1, "2": part2, "3": part3}[p]()
        say(f"  (part {p}: {time.time() - t:.0f} s)")
    say(f"\nDone in {(time.time() - start) / 60:.1f} minutes.")
    with open(os.path.join(ROOT, "main_output.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(OUT) + "\n")
    print("Saved to main_output.txt")
