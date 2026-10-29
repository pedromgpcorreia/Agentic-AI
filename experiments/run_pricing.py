"""Phases 3-4: fixed-price scenarios (reference) and learned prices (bandit, task 5).

All runs use the calibrated parameters (consumer_choice/calibrated.py) and common
random numbers: seed s is used in every scenario, so differences between scenarios
are not due to different random draws.

Scenarios (prices of the incumbents from the DIGI entry, month 12):
  * no_entry          : DIGI never enters, list prices (counterfactual);
  * fixed_X           : the three incumbents at X x list price, X in ARMS;
  * solo_OP_X         : only OP cuts to X, the others keep the list price
                        (is keeping the list price a best response?);
  * bandit_e{eps}_a{alpha}: each incumbent learns its price (epsilon-greedy bandit).

Usage (repository root):  python experiments/run_pricing.py [quick]
Outputs in results/pricing/: runs.csv (one row per run), series.csv.gz (monthly means),
bandit_log.csv.gz (one row per pricing decision).
"""
import os
import sys
import warnings
from multiprocessing import Pool

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
warnings.filterwarnings("ignore")
from consumer_choice.calibrated import CALIBRATED  # noqa: E402
from consumer_choice.learning import ARMS, BanditPricePolicy, FixedPricePolicy  # noqa: E402
from consumer_choice.telecom import TelecomMarketModel  # noqa: E402

MONTHS = 132                      # 12 months before the entry + 10 years after
ENTRY = 12
OPS = ["MEO", "NOS", "Vodafone", "DIGI"]
QUICK = len(sys.argv) > 1 and sys.argv[1] == "quick"
SEEDS = range(4000, 4004 if QUICK else 4030)


def scenarios():
    sc = {"no_entry": dict(entry=False, policy=None)}
    for x in ARMS:
        sc[f"fixed_{x:.2f}"] = dict(policy=("fixed", (x, x, x)))
    for i, op in enumerate(OPS[:3]):
        for x in (0.90, 0.80):
            mult = [1.0, 1.0, 1.0]
            mult[i] = x
            sc[f"solo_{op}_{x:.2f}"] = dict(policy=("fixed", tuple(mult)))
    for eps in (0.05, 0.10, 0.20):
        for alpha in (0.1, 0.2, 0.4):
            if QUICK and (eps, alpha) != (0.10, 0.2):
                continue
            sc[f"bandit_e{eps:.2f}_a{alpha:.1f}"] = dict(policy=("bandit", eps, alpha))
    return sc


def run(args):
    name, spec, seed = args
    warnings.filterwarnings("ignore")
    m = TelecomMarketModel(entry_tick=ENTRY if spec.get("entry", True) else None,
                           rng=seed, **CALIBRATED)
    pol = spec["policy"]
    if pol and pol[0] == "fixed":
        m.price_policy = FixedPricePolicy(pol[1])
    elif pol and pol[0] == "bandit":
        m.price_policy = BanditPricePolicy(epsilon=pol[1], alpha=pol[2])
    for _ in range(MONTHS):
        m.step()
    df = m.datacollector.get_model_vars_dataframe()
    df["scenario"], df["seed"], df["month"] = name, seed, range(len(df))
    post = df.iloc[ENTRY + 1:]
    row = {"scenario": name, "seed": seed}
    for op in OPS:
        row[f"profit_{op}"] = post[f"profit_{op}"].sum()          # cumulative, after entry
        row[f"share_{op}_end"] = post[f"share_{op}"].iloc[-12:].mean()
        row[f"price_{op}_mean"] = post[f"price_{op}"].mean()
    row["profit_incumbents"] = sum(row[f"profit_{op}"] for op in OPS[:3])
    row["avg_price_paid_end"] = post.avg_price_paid.iloc[-12:].mean()
    row["switches_year"] = post.switches.sum() / (len(post) / 12) / post.population.mean()
    log = None
    if pol and pol[0] == "bandit":
        log = pd.DataFrame(m.price_policy.log)
        log["scenario"], log["seed"] = name, seed
    return row, df, log


if __name__ == "__main__":
    out = "results/pricing"
    os.makedirs(out, exist_ok=True)
    jobs = [(n, s, seed) for n, s in scenarios().items() for seed in SEEDS]
    rows, series, logs = [], [], []
    with Pool(None) as pool:
        for i, (row, df, log) in enumerate(pool.imap(run, jobs, chunksize=2)):
            rows.append(row)
            series.append(df)
            if log is not None:
                logs.append(log)
            if i % 50 == 0:
                print(i, "/", len(jobs), row["scenario"], flush=True)
    pd.DataFrame(rows).to_csv(f"{out}/runs.csv", index=False)
    s = pd.concat(series)
    s.groupby(["scenario", "month"]).mean(numeric_only=True).drop(columns="seed").to_csv(
        f"{out}/series.csv.gz")
    pd.concat(logs).to_csv(f"{out}/bandit_log.csv.gz", index=False)
    print(pd.DataFrame(rows).groupby("scenario")[
        ["profit_incumbents", "profit_MEO", "profit_NOS", "profit_Vodafone",
         "share_DIGI_end", "avg_price_paid_end"]].mean().round(3).to_string())
