"""Task 6: one-at-a-time sensitivity of the main conclusions to the modelling choices.

Each variant changes one parameter of the calibrated model (consumer_choice/calibrated.py);
the other parameters, including the brand constants, are not re-calibrated. For each
variant the scenarios behind the conclusions of task 5 are run with common random numbers:
  * fixed_1.00      : the three incumbents keep the list price (reference);
  * solo_OP_0.90    : only OP cuts to 0.90 x list price (is a unilateral cut profitable?);
  * bandit          : each incumbent learns its price (epsilon 0.10, alpha 0.2, every 3 months).

Variants (docs/registo_decisoes.md, pending list):
  kappa 0.10 / 0.30 (quality from complaints), exit rate 0.3 % / 1 % per month,
  initial contracted 50 % / 90 %, renewal discount 17.8 %, full lock-in instead of the
  legal penalty, margin 60 %.

Usage (repository root):  python experiments/run_sensitivity.py [quick] [--out DIR]
Output: results/sensitivity/runs.csv (quick: results/sensitivity_quick/), one row per run.
"""
import os
import sys
import warnings
from multiprocessing import Pool

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
warnings.filterwarnings("ignore")
from consumer_choice.calibrated import CALIBRATED  # noqa: E402
from consumer_choice.learning import BanditPricePolicy, FixedPricePolicy  # noqa: E402
from consumer_choice.telecom import TelecomMarketModel  # noqa: E402

MONTHS = 132                      # 12 months before the entry + 10 years after
ENTRY = 12
OPS = ["MEO", "NOS", "Vodafone", "DIGI"]
QUICK = "quick" in sys.argv
SEEDS = range(4000, 4002 if QUICK else 4020)
OUT = (sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv
       else "results/sensitivity_quick" if QUICK else "results/sensitivity")

# quality q = 0.80 - kappa * ln(r), r = complaints relative to the incumbents' mean
# (docs/model_v2_spec.md, 4.2); r is recovered from the qualities with kappa = 0.20
BASE_KAPPA = 0.20
BASE_QUALITIES = (0.848, 0.784, 0.776, 0.572)
BASE_DIGI = (0.572, 0.756)


def quality(q, kappa):
    return 0.80 - kappa * (0.80 - q) / BASE_KAPPA


def kappa_params(kappa):
    return dict(qualities=tuple(round(quality(q, kappa), 4) for q in BASE_QUALITIES),
                digi_quality_start=round(quality(BASE_DIGI[0], kappa), 4),
                digi_quality_end=round(quality(BASE_DIGI[1], kappa), 4))


VARIANTS = {
    "base": {},
    "kappa_0.10": kappa_params(0.10),
    "kappa_0.30": kappa_params(0.30),
    "exit_0.3%": dict(exit_rate=0.003),
    "exit_1%": dict(exit_rate=0.010),
    "contracted_50%": dict(initial_contracted=0.5),
    "contracted_90%": dict(initial_contracted=0.9),
    "discount_17.8%": dict(renewal_discount=0.178),
    "lock_in": dict(exit_rule="lock"),
    "margin_60%": dict(margin=0.60),
}


def scenarios():
    sc = {"fixed_1.00": ("fixed", (1.0, 1.0, 1.0))}
    for i, op in enumerate(OPS[:3]):
        mult = [1.0, 1.0, 1.0]
        mult[i] = 0.90
        sc[f"solo_{op}_0.90"] = ("fixed", tuple(mult))
    sc["bandit"] = ("bandit",)
    return sc


def run(args):
    variant, name, pol, seed = args
    warnings.filterwarnings("ignore")
    m = TelecomMarketModel(entry_tick=ENTRY, rng=seed, **dict(CALIBRATED, **VARIANTS[variant]))
    if pol[0] == "fixed":
        m.price_policy = FixedPricePolicy(pol[1])
    else:
        m.price_policy = BanditPricePolicy(seed=seed)
    for _ in range(MONTHS):
        m.step()
    df = m.datacollector.get_model_vars_dataframe()
    post = df.iloc[ENTRY + 1:]
    row = {"variant": variant, "scenario": name, "seed": seed,
           "share_DIGI_m28": df.share_DIGI.iloc[28],
           "share_DIGI_end": post.share_DIGI.iloc[-12:].mean(),
           "pct_contracted_end": post.pct_contracted.iloc[-12:].mean()}
    for op in OPS:
        row[f"profit_{op}"] = post[f"profit_{op}"].sum()          # cumulative, after entry
        row[f"price_{op}_mean"] = post[f"price_{op}"].mean()
    row["profit_incumbents"] = sum(row[f"profit_{op}"] for op in OPS[:3])
    return row


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    jobs = [(v, n, p, seed) for v in VARIANTS for n, p in scenarios().items() for seed in SEEDS]
    rows = []
    with Pool(None) as pool:
        for i, row in enumerate(pool.imap(run, jobs, chunksize=2)):
            rows.append(row)
            if i % 50 == 0:
                print(i, "/", len(jobs), row["variant"], row["scenario"], flush=True)
    pd.DataFrame(rows).to_csv(f"{OUT}/runs.csv", index=False)
    print(pd.DataFrame(rows).groupby(["variant", "scenario"])[
        ["profit_incumbents", "share_DIGI_m28", "share_DIGI_end"]].mean().round(3).to_string())
