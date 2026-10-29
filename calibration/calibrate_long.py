"""Long-run calibration of the market without DIGI, for the chosen (w, e) = (0.10, 0.02).

Why: the first calibrations averaged a short window (months 12-36). Over 60 months the
shares still drifted (MEO +5 pp) and the average price paid fell from EUR 41.7 to 37.1,
because all initial contracts were priced at the list price. This script finds the
values that make the market without entry stationary over 72 months:

  * brand constants (ASC): mean shares over months 24-72 = ANACOM Q3 2024 shares;
  * renewal discount (delta): mean contracted share over months 24-72 = 0.70;
  * initial_renewed (rho): share of the initial contracts that are renewals, set to the
    share of renewals among the contracts signed in months 24-72 (fixed point).

Then it checks the DIGI trajectory with the new values (48 seeds).
Usage (repository root):  python calibration/calibrate_long.py
Output: results/v2/calibration_long.json
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
DIGI_TARGETS = {19: 0.028, 25: 0.030, 28: 0.032}
W, E = 0.10, 0.02
MONTHS, WINDOW, SEEDS, ITER, ETA = 72, 24, 12, 8, 0.35
COLS = ["share_MEO", "share_NOS", "share_Vodafone", "share_DIGI"]


def run(args):
    asc, delta, rho, seed = args
    warnings.filterwarnings("ignore")
    m = TelecomMarketModel(entry_tick=None, norm_influence=W, exploration=E,
                           brand_constants=asc, renewal_discount=delta,
                           initial_renewed=rho, rng=seed)
    for _ in range(MONTHS):
        m.step()
    d = m.datacollector.get_model_vars_dataframe().iloc[WINDOW:]
    new_contracts = d.renewals.sum() + d.switches.sum() + d.entries.sum()
    return (d[COLS].mean().values, d.pct_contracted.mean(), d.renewals.sum() / new_contracts,
            d.avg_price_paid.iloc[:12].mean(), d.avg_price_paid.iloc[-12:].mean())


def with_entry(args):
    asc, delta, rho, seed = args
    warnings.filterwarnings("ignore")
    m = TelecomMarketModel(norm_influence=W, exploration=E, brand_constants=asc,
                           renewal_discount=delta, initial_renewed=rho, rng=seed)
    for _ in range(30):
        m.step()
    df = m.datacollector.get_model_vars_dataframe()
    return [df.share_DIGI.iloc[t] for t in DIGI_TARGETS]


if __name__ == "__main__":
    asc, delta, rho = np.array([0.0, 0.0280, 0.0168, -0.0837]), 0.178, 0.9
    log = []
    with Pool(None) as pool:
        for it in range(ITER):
            res = pool.map(run, [(list(asc), delta, rho, s) for s in range(1000, 1000 + SEEDS)])
            shares = np.mean([r[0] for r in res], axis=0)
            contracted = np.mean([r[1] for r in res])
            renewed = np.mean([r[2] for r in res])
            log.append({"iter": it, "asc": asc.round(4).tolist(), "delta": round(delta, 4),
                        "rho": round(rho, 3), "shares": shares.round(4).tolist(),
                        "contracted": round(contracted, 3), "renewed_share": round(renewed, 3),
                        "price_paid_m24_36": round(np.mean([r[3] for r in res]), 2),
                        "price_paid_m60_72": round(np.mean([r[4] for r in res]), 2)})
            print(log[-1], flush=True)
            asc = asc + ETA * (TARGET - shares)
            asc = asc - asc[0]
            delta = delta + 0.15 * (0.70 - contracted)
            rho = renewed
        digi = np.array(pool.map(with_entry, [(list(asc), delta, rho, s) for s in range(3000, 3048)]))
    mean = digi.mean(0)
    rmse = float(np.sqrt(np.mean((mean - np.array(list(DIGI_TARGETS.values()))) ** 2)) * 100)
    out = {"norm_influence": W, "exploration": E, "brand_constants": asc.round(4).tolist(),
           "renewal_discount": round(delta, 4), "initial_renewed": round(rho, 3),
           "digi_m19_m25_m28": mean.round(4).tolist(),
           "digi_sd": digi.std(0).round(4).tolist(), "rmse_pp": round(rmse, 3), "log": log}
    os.makedirs("results/v2", exist_ok=True)
    json.dump(out, open("results/v2/calibration_long.json", "w"), indent=1)
    print({k: v for k, v in out.items() if k != "log"})
