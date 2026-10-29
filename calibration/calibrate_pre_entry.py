"""Pre-entry calibration: brand constants and renewal discount such that, without DIGI,
the market stays at the observed shares (ANACOM, Q3 2024) and the contracted share stays
at its initial value.

Usage (repository root):  python calibration/calibrate_pre_entry.py
"""
import json
import os
import sys
import warnings
from multiprocessing import Pool

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
warnings.filterwarnings("ignore")
from consumer_choice.telecom import TelecomMarketModel  # noqa: E402

TARGET = np.array([41.8, 35.0, 20.6, 2.6]) / 100
MONTHS, SEEDS, ITER, ETA = 36, 16, 8, 0.35


def run(args):
    asc, delta, seed = args
    warnings.filterwarnings("ignore")
    m = TelecomMarketModel(entry_tick=None, brand_constants=asc, renewal_discount=delta, rng=seed)
    for _ in range(MONTHS):
        m.step()
    df = m.datacollector.get_model_vars_dataframe()
    shares = df[["share_MEO", "share_NOS", "share_Vodafone", "share_DIGI"]].iloc[MONTHS // 2:].mean().values
    return shares, df.pct_contracted.iloc[MONTHS // 2:].mean()


def evaluate(asc, delta, pool):
    res = pool.map(run, [(list(asc), delta, s) for s in range(1000, 1000 + SEEDS)])
    return np.mean([r[0] for r in res], axis=0), np.mean([r[1] for r in res])


if __name__ == "__main__":
    asc, delta, log = np.array([0.0, 0.03, 0.04, -0.06]), 0.1777, []
    with Pool(None) as pool:
        for it in range(ITER):
            shares, contracted = evaluate(asc, delta, pool)
            err = TARGET - shares
            log.append({"iter": it, "asc": asc.round(4).tolist(), "delta": round(delta, 4),
                        "shares": shares.round(4).tolist(), "contracted": round(contracted, 3)})
            print(log[-1], flush=True)
            asc = asc + ETA * err
            asc = asc - asc[0]                         # MEO is the reference (constant 0)
            delta = delta + 0.15 * (0.70 - contracted)
    out = {"brand_constants": asc.round(4).tolist(), "renewal_discount": round(delta, 4), "log": log}
    os.makedirs("results/v2", exist_ok=True)
    json.dump(out, open("results/v2/calibration_pre_entry.json", "w"), indent=1)
    print(out["brand_constants"], out["renewal_discount"])
