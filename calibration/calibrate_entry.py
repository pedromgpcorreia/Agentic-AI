"""Post-entry calibration: grid over norm_influence (w) and exploration (e).

For each grid point:
  1. re-calibrate the brand constants so that the market without DIGI is stable;
  2. run the model with the DIGI entry and compare the DIGI share with ANACOM data
     (months 19, 25, 28 = Q2 2025, Q4 2025, Q1 2026: 2.8%, 3.0%, 3.2%).

Usage (repository root):  python calibration/calibrate_entry.py [fine | delta10]
Output: results/v2/calibration_entry.csv (or calibration_entry_fine.csv, calibration_entry_delta10.csv)

delta10 (decided 29/10, 19:22): renewal discount back to 10 %; the 70 % under contract is only
the starting point and the contracted share evolves with the consumers' decisions.
initial_renewed = 0.48 = fixed point with delta 10 % (share of renewals among the contracts
signed in months 24-72 without entry).
"""
import os
import sys
import warnings
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
warnings.filterwarnings("ignore")
from consumer_choice.telecom import TelecomMarketModel  # noqa: E402

TARGET_SHARES = np.array([41.8, 35.0, 20.6, 2.6]) / 100
DIGI_TARGETS = {19: 0.028, 25: 0.030, 28: 0.032}
GRID_W = [0.10, 0.15, 0.25, 0.40]
GRID_E = [0.0025, 0.005, 0.01, 0.02]
OUTFILE = "results/v2/calibration_entry.csv"
if len(sys.argv) > 1 and sys.argv[1] == "fine":          # second, finer grid around the best point
    GRID_W = [0.08, 0.10, 0.12, 0.13]
    GRID_E = [0.01, 0.02, 0.03, 0.05]
    OUTFILE = "results/v2/calibration_entry_fine.csv"
DELTA, RHO = 0.178, 0.0
if len(sys.argv) > 1 and sys.argv[1] == "delta10":
    GRID_W = [0.08, 0.10, 0.12]
    GRID_E = [0.005, 0.01, 0.02, 0.03]
    OUTFILE = "results/v2/calibration_entry_delta10.csv"
    DELTA, RHO = 0.10, 0.48
COLS = ["share_MEO", "share_NOS", "share_Vodafone", "share_DIGI"]


def pre_entry(args):
    w, e, asc, seed = args
    warnings.filterwarnings("ignore")
    m = TelecomMarketModel(entry_tick=None, norm_influence=w, exploration=e,
                           brand_constants=asc, renewal_discount=DELTA, initial_renewed=RHO,
                           rng=seed)
    for _ in range(24):
        m.step()
    return m.datacollector.get_model_vars_dataframe()[COLS].iloc[12:].mean().values


def with_entry(args):
    w, e, asc, seed = args
    warnings.filterwarnings("ignore")
    m = TelecomMarketModel(norm_influence=w, exploration=e, brand_constants=asc,
                           renewal_discount=DELTA, initial_renewed=RHO, rng=seed)
    for _ in range(30):
        m.step()
    df = m.datacollector.get_model_vars_dataframe()
    churn = df.switches.iloc[1:13].sum() / df.population.iloc[1:13].mean()     # pre-entry, per year
    end = df.switch_at_contract_end.iloc[1:].sum()
    ended = end + df.renewal_offers.iloc[1:].sum()
    return [df.share_DIGI.iloc[t] for t in DIGI_TARGETS] + [churn, end / max(1, ended)]


if __name__ == "__main__":
    rows = []
    os.makedirs("results/v2", exist_ok=True)
    with Pool(None) as pool:
        for w in GRID_W:
            for e in GRID_E:
                asc = np.array([0.0, 0.029, 0.013, -0.089])
                for it in range(4):                       # brand constants for this (w, e)
                    shares = np.mean(pool.map(pre_entry, [(w, e, list(asc), s) for s in range(2000, 2012)]), axis=0)
                    asc = asc + 0.35 * (TARGET_SHARES - shares)
                    asc = asc - asc[0]
                res = np.array(pool.map(with_entry, [(w, e, list(asc), s) for s in range(3000, 3024)]))
                digi = res[:, :3].mean(0)
                err = np.sqrt(np.mean((digi - np.array(list(DIGI_TARGETS.values()))) ** 2))
                row = {"norm_influence": w, "exploration": e,
                       "asc_NOS": asc[1], "asc_VOD": asc[2], "asc_NOWO_DIGI": asc[3],
                       "digi_m19": digi[0], "digi_m25": digi[1], "digi_m28": digi[2],
                       "rmse_pp": err * 100, "churn_year": res[:, 3].mean(),
                       "exit_at_contract_end": res[:, 4].mean()}
                rows.append(row)
                print({k: round(v, 4) for k, v in row.items()}, flush=True)
                pd.DataFrame(rows).to_csv(OUTFILE, index=False)
