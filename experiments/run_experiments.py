"""Baseline and sensitivity experiments (Mesa batch_run).

Usage, from the repository root:
    python experiments/run_experiments.py            # all experiments
    python experiments/run_experiments.py baseline   # one experiment

Outputs are written to data/ as compressed CSV files. Each run has a
fixed seed, so the results are reproducible.
"""
import os
import sys

import pandas as pd
from mesa.batchrunner import batch_run

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from consumer_choice import ConsumerChoiceModel  # noqa: E402

OUT = os.path.join(ROOT, "data")
PROCESSES = None          # None = all CPU cores

# Baseline: default values of the original model file
BASELINE = dict(num_consumers=100, avg_connections=5,
                initial_pct_orange=50, norm_influence=0.15,
                information_exchange=0.05, exploration=0.01,
                quality_orange=0.5, quality_blue=0.5)

# name: (parameter, values, runs per value, ticks, first seed,
#        record every tick?)
EXPERIMENTS = {
    "baseline": (None, None, 1000, 2000, 0, True),
    "norm_influence": ("norm_influence",
                       [round(0.1 * i, 1) for i in range(11)],
                       100, 1000, 100_000, False),
    "quality_blue": ("quality_blue",
                     [0.3, 0.4, 0.45, 0.5, 0.55, 0.6, 0.7],
                     100, 1000, 200_000, False),
    "exploration": ("exploration", [0.0, 0.01, 0.05, 0.1, 0.2],
                    100, 1000, 300_000, False),
}


def run(name):
    var, values, runs, ticks, seed0, every_tick = EXPERIMENTS[name]
    params = dict(BASELINE)
    if var is not None:
        params[var] = values
    results = batch_run(ConsumerChoiceModel, parameters=params,
                        rng=list(range(seed0, seed0 + runs)),
                        max_steps=ticks,
                        data_collection_period=1 if every_tick else -1,
                        number_processes=PROCESSES,
                        display_progress=False)
    df = pd.DataFrame(results)
    df = df.rename(columns={"iteration": "run", "Step": "tick"})
    keys = ["run", "tick"] + ([var] if var else [])
    df = df[keys + ["orange", "blue", "clustering"]].sort_values(keys)
    os.makedirs(OUT, exist_ok=True)
    df.to_csv(os.path.join(OUT, f"{name}.csv.gz"), index=False,
              float_format="%.6g")
    print(f"{name}: {df.run.nunique()} runs, {len(df)} rows")


if __name__ == "__main__":
    for name in (sys.argv[1:] or EXPERIMENTS):
        run(name)
