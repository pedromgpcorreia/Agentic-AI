"""ORIGINAL MODEL: Consumer Choice (Jager & Wang), implemented in Python with Mesa (tasks 1 and 2).

Self-contained file: the model, the simulations of the report and the interface are all
in this file. It needs no other file of the project.

What it does
    1. Opens the model's interface in the browser (Mesa SolaraViz, the equivalent of the
       NetLogo interface): the consumers in their friendship network, coloured by product,
       and the plots of the outputs, with Reset / Play / Step buttons and sliders. The
       defaults are the baseline of the report.
    2. When you press Enter in the terminal, closes the interface and runs every simulation
       of the report for this model, with the same parameters and random seeds, so the
       printed numbers are those of the report: the baseline (1000 runs x 2000 ticks,
       Tables 7 and 8) and the sensitivity analysis of norm_influence, quality_blue and
       exploration (100 runs per value x 1000 ticks, Tables 9 to 11).
    Results are printed and saved to original_model_full_output.txt, next to this file.

Requirements
    Python 3.12 or later (required by Mesa 3.5). Install once:
        python -m pip install "mesa[viz,network]>=3.5,<4" "ipyvue<3" "ipyvuetify<3" numpy pandas scipy matplotlib

How to run
    VS Code: open this file, select the Python interpreter where the requirements are
    installed and press Run.
    Terminal, from the folder of this file:
        python original_model_full.py                    # interface, then the simulations
        python original_model_full.py --interface-only   # only the interface
        python original_model_full.py --no-interface     # only the simulations

Time
    The simulations use all CPU cores: about 6 minutes on 8 cores.

Original NetLogo model: Copyright 2024 Uri Wilensky, CC BY-NC-SA 3.0 (Jager & Wang, 2024;
basic model by M. A. Janssen).
"""
import math
import os
import socket
import subprocess
import sys
import time
import warnings
from decimal import ROUND_HALF_UP, Decimal
from multiprocessing import Pool

import mesa
import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
UNDER_SOLARA = "solara.server" in sys.modules     # True when this file is the interface page


# ============================================================================ the model
# Python/Mesa 3 implementation of the NetLogo Models Library model "Consumer Choice".
# The rules follow the NetLogo code line by line. Product 0 is orange, product 1 is blue.
ORANGE, BLUE = 0, 1


class Consumer(mesa.Agent):
    """A consumer who uses one of two products and has friends."""

    def __init__(self, model, choice, pos):
        super().__init__(model)
        # product in use: 0 orange, 1 blue
        self.choice = choice
        # total utility of each product
        self.utilities = [1.0, 0.0] if choice == ORANGE else [0.0, 1.0]
        # probability of keeping the product (habit)
        self.satisfaction = model.satisfaction(choice)
        # remembered quality of each product
        self.personal_experience = [0.0, 0.0]
        # location, used only to build the network
        self.pos = pos
        # linked consumers (social network)
        self.friends = []

    def consume(self):
        """Keep the product, explore the other, or choose by utility."""
        if self.random.random() < self.satisfaction:
            pass                               # habit: keep the product
        elif self.random.random() < self.model.exploration:
            self.choice = 1 - self.choice      # explore the other product
        elif self.utilities[ORANGE] != self.utilities[BLUE]:
            self.choice = (ORANGE if self.utilities[ORANGE]
                           > self.utilities[BLUE] else BLUE)
        self.satisfaction = self.model.satisfaction(self.choice)

    def update_utilities(self):
        """Combine own experience, friends' information and the norm."""
        m = self.model
        for option in (ORANGE, BLUE):
            # 1. own experience: only the product in use is updated
            if self.choice == option:
                self.personal_experience[option] = m.quality[option]
            # 2. information exchange: a friend who uses the product
            #    reports its current quality
            neighbor_info = 0.0
            if (self.random.random() <= m.information_exchange
                    and any(f.choice == option for f in self.friends)):
                neighbor_info = m.quality[option]
            # 3. social norm: share of friends who use the product
            norm_util = 0.0
            if self.friends:
                users = sum(f.choice == option for f in self.friends)
                norm_util = users / len(self.friends)
            # 4. total utility: norm-based and product utility
            prod_util = (self.personal_experience[option]
                         + neighbor_info) / 2
            self.utilities[option] = (
                m.norm_influence * norm_util
                + (1 - m.norm_influence) * prod_util)


class ConsumerChoiceModel(mesa.Model):
    """Market with two competing products of changeable quality."""

    def __init__(self, num_consumers=100, avg_connections=5,
                 initial_pct_orange=50, norm_influence=0.15,
                 information_exchange=0.05, exploration=0.01,
                 quality_orange=0.5, quality_blue=0.5, rng=None):
        super().__init__(rng=rng)
        self.num_consumers = num_consumers
        self.norm_influence = norm_influence
        self.information_exchange = information_exchange
        self.exploration = exploration
        self.quality = [quality_orange, quality_blue]

        # consumers: random location in a 51 x 51 world and
        # random initial product
        for _ in range(num_consumers):
            pct = self.random.randrange(100)
            choice = ORANGE if pct < initial_pct_orange else BLUE
            pos = (self.random.uniform(-25.5, 25.5),
                   self.random.uniform(-25.5, 25.5))
            Consumer(self, choice, pos)
        self.consumers = list(self.agents)
        self.build_network(avg_connections)

        self.datacollector = mesa.DataCollector(model_reporters={
            "orange": lambda m: m.count_choice(ORANGE),
            "blue": lambda m: m.count_choice(BLUE),
            "clustering": lambda m: m.consumer_cluster(),
        })
        self.datacollector.collect(self)

    def satisfaction(self, choice):
        """Satisfaction grows with the log of quality: log10(1 + 9q)."""
        return math.log10(1 + 9 * self.quality[choice])

    def build_network(self, avg_connections):
        """Link a random consumer to its nearest unlinked consumer."""
        num_links = (avg_connections * self.num_consumers) / 2
        links = 0
        while links < num_links:
            a = self.random.choice(self.consumers)
            cands = [c for c in self.consumers
                     if c is not a and c not in a.friends]
            if not cands:
                continue
            d_min = min(math.dist(a.pos, c.pos) for c in cands)
            nearest = [c for c in cands
                       if math.dist(a.pos, c.pos) == d_min]
            target = self.random.choice(nearest)
            a.friends.append(target)
            target.friends.append(a)
            links += 1

    def step(self):
        self.agents.shuffle_do("consume")
        self.agents.shuffle_do("update_utilities")
        self.datacollector.collect(self)

    # ---- model outputs (the two plots of the NetLogo model) ----
    def count_choice(self, product):
        return sum(c.choice == product for c in self.consumers)

    def consumer_cluster(self):
        """Mean share of friends who use the consumer's product."""
        total = 0.0
        for c in self.consumers:
            if c.friends:
                same = sum(f.choice == c.choice for f in c.friends)
                total += same / len(c.friends)
        return total / self.num_consumers


# ============================================================================ experiments of the report
# Baseline: default values of the original model file
BASELINE = dict(num_consumers=100, avg_connections=5,
                initial_pct_orange=50, norm_influence=0.15,
                information_exchange=0.05, exploration=0.01,
                quality_orange=0.5, quality_blue=0.5)

# name: (parameter, values, runs per value, ticks, first seed)
EXPERIMENTS = {
    "baseline": (None, None, 1000, 2000, 0),
    "norm_influence": ("norm_influence", [round(0.1 * i, 1) for i in range(11)], 100, 1000, 100_000),
    "quality_blue": ("quality_blue", [0.3, 0.4, 0.45, 0.5, 0.55, 0.6, 0.7], 100, 1000, 200_000),
    "exploration": ("exploration", [0.0, 0.01, 0.05, 0.1, 0.2], 100, 1000, 300_000),
}
TICKS_SHOWN = (0, 100, 250, 500, 750, 1000, 1500, 2000)
OUT = []


def say(text=""):
    print(text, flush=True)
    OUT.append(text)


def r(x, d=3):
    """Round half up on the decimal value, as in the report (0.5065 -> 0.507)."""
    return str(Decimal(repr(round(float(x), 9))).quantize(Decimal(1).scaleb(-d), ROUND_HALF_UP))


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


def run_baseline(args):
    """One run of the original model; outputs at the ticks shown in the report."""
    warnings.filterwarnings("ignore")
    params, seed, ticks = args
    m = ConsumerChoiceModel(rng=seed, **params)
    for _ in range(ticks):
        m.step()
    df = m.datacollector.get_model_vars_dataframe()
    return {t: (df.orange[t] / 100, df.clustering[t]) for t in TICKS_SHOWN if t <= ticks}


def simulations():
    say("Original Consumer Choice model: simulations of the report (tasks 1 and 2)\n")
    _, _, runs, ticks, seed0 = EXPERIMENTS["baseline"]
    res = pool_map(run_baseline, [(BASELINE, s, ticks) for s in range(seed0, seed0 + runs)], "baseline")
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
        var, values, runs, ticks, seed0 = EXPERIMENTS[name]
        jobs = [(dict(BASELINE, **{var: v}), s, ticks) for v in values for s in range(seed0, seed0 + runs)]
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


# ============================================================================ the interface (SolaraViz)
ORANGE_C, BLUE_C = "#eb6834", "#2a78d6"


def build_page():
    """Mesa's browser interface: sliders and Reset / Play / Step on the left, network and plots."""
    import solara
    from matplotlib.collections import LineCollection
    from matplotlib.figure import Figure
    from mesa.visualization import SolaraViz

    class LiveConsumerChoiceModel(ConsumerChoiceModel):
        """Original model with the random seed as an interface parameter."""

        def __init__(self, seed=1, **params):
            super().__init__(rng=int(seed), **params)

    def make_safe_plot_component(measures, post_process=None, xlabel="Step"):
        """Plot that copies the data first, so it is safe while the model is stepping."""
        def SafePlot(model):
            data = model.datacollector.model_vars
            cols = {m: list(data.get(m, [])) for m in measures}
            n = min((len(v) for v in cols.values()), default=0)
            df = pd.DataFrame({m: v[:n] for m, v in cols.items()})
            fig = Figure(figsize=(6, 3), layout="constrained")
            ax = fig.subplots()
            for m, colour in measures.items():
                ax.plot(df.index, df[m], color=colour, label=m)
            ax.set_xlabel(xlabel)
            if post_process is not None:
                post_process(ax)
            return solara.FigureMatplotlib(fig, format="png", dpi=72)
        return SafePlot

    def NetworkView(model):
        """Consumers at their positions, coloured by product, with friendship links."""
        fig = Figure(figsize=(6, 6))
        ax = fig.subplots()
        consumers = list(model.consumers)            # snapshot: the model may be stepping
        segs = [(c.pos, f.pos) for c in consumers for f in list(c.friends) if id(c) < id(f)]
        ax.add_collection(LineCollection(segs, colors="#d0d0d0", linewidths=0.7, zorder=1))
        ax.scatter([c.pos[0] for c in consumers], [c.pos[1] for c in consumers], s=60,
                   c=[ORANGE_C if c.choice == ORANGE else BLUE_C for c in consumers],
                   zorder=2, edgecolors="white", linewidths=0.5)
        ax.set_xlim(-26.5, 26.5)
        ax.set_ylim(-26.5, 26.5)
        ax.set_aspect("equal")
        ax.set_xticks([])
        ax.set_yticks([])
        n = len(consumers)
        orange = sum(c.choice == ORANGE for c in consumers)
        ax.set_title(f"Tick {model.steps} - orange {orange}, blue {n - orange} - "
                     f"clustering {model.consumer_cluster():.3f}", fontsize=9, loc="left")
        return solara.FigureMatplotlib(fig, format="png", dpi=72)

    def HowTo(model):
        return solara.Markdown("**After changing a slider, press Reset**: the change applies to a new run. "
                               "The defaults are the baseline of the report.")

    def label_counts(ax):
        ax.set_ylabel("consumers")
        ax.legend(fontsize=7)

    def label_clustering(ax):
        ax.set_ylabel("clustering")
        ax.set_ylim(0, 1)

    model_params = {
        "num_consumers": {"type": "SliderInt", "value": BASELINE["num_consumers"],
                          "label": "Number of consumers", "min": 10, "max": 300, "step": 10},
        "avg_connections": {"type": "SliderInt", "value": BASELINE["avg_connections"],
                            "label": "Average connections", "min": 1, "max": 10, "step": 1},
        "initial_pct_orange": {"type": "SliderInt", "value": BASELINE["initial_pct_orange"],
                               "label": "Initial % orange", "min": 0, "max": 100, "step": 1},
        "norm_influence": {"type": "SliderFloat", "value": BASELINE["norm_influence"],
                           "label": "Norm influence (w)", "min": 0.0, "max": 1.0, "step": 0.05},
        "information_exchange": {"type": "SliderFloat", "value": BASELINE["information_exchange"],
                                 "label": "Information exchange", "min": 0.0, "max": 1.0, "step": 0.05},
        "exploration": {"type": "SliderFloat", "value": BASELINE["exploration"],
                        "label": "Exploration", "min": 0.0, "max": 0.2, "step": 0.01},
        "quality_orange": {"type": "SliderFloat", "value": BASELINE["quality_orange"],
                           "label": "Quality orange", "min": 0.0, "max": 1.0, "step": 0.05},
        "quality_blue": {"type": "SliderFloat", "value": BASELINE["quality_blue"],
                         "label": "Quality blue", "min": 0.0, "max": 1.0, "step": 0.05},
        "seed": {"type": "SliderInt", "value": 1, "label": "Random seed", "min": 1, "max": 100, "step": 1},
    }
    counts = make_safe_plot_component({"orange": ORANGE_C, "blue": BLUE_C}, label_counts, "Tick")
    clustering = make_safe_plot_component({"clustering": "#1a1a1a"}, label_clustering, "Tick")
    return SolaraViz(
        LiveConsumerChoiceModel(**BASELINE),
        components=[(NetworkView, 0), counts, clustering, (HowTo, 0)],
        model_params=model_params,
        name="Consumer Choice - original model",
        play_interval=100,
        render_interval=1,
    )


def open_interface():
    """Serves this file as a Solara page, opens it in the browser and waits for Enter."""
    import importlib.util
    import webbrowser
    print("\n=== Original model: interface ===")
    if importlib.util.find_spec("solara") is None:
        print('The interface needs Mesa\'s visualization packages: python -m pip install '
              '"mesa[viz,network]>=3.5,<4" "ipyvue<3" "ipyvuetify<3". Continuing without it.')
        return

    def port_open(p):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            return s.connect_ex(("127.0.0.1", p)) == 0

    port = 8765
    while port_open(port):
        port += 1
    proc = subprocess.Popen([sys.executable, "-m", "solara", "run", os.path.abspath(__file__),
                             "--port", str(port), "--no-open"], cwd=HERE)
    for _ in range(240):                                  # up to 2 minutes for the first start
        if proc.poll() is not None or port_open(port):
            break
        time.sleep(0.5)
    if proc.poll() is not None:
        print(f"The interface did not start (solara exit code {proc.returncode}). Continuing without it.")
        return
    time.sleep(1.5)
    url = f"http://localhost:{port}"
    webbrowser.open(url)
    print(f"The interface is open in the browser: {url}")
    print("Use Reset, Play / Pause and Step on the left; change the sliders and press Reset.")
    try:
        input("\nPress Enter here to close the interface and continue... ")
    except (EOFError, KeyboardInterrupt):
        pass
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


# ============================================================================ entry points
if UNDER_SOLARA:                     # loaded by `solara run` (the interface page)
    page = build_page()
elif __name__ == "__main__":         # run by `python original_model_full.py`
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = sys.argv[1:]
    if "--no-interface" not in args:
        open_interface()
    if "--interface-only" not in args:
        print()
        start = time.time()
        simulations()
        say(f"\nDone in {(time.time() - start) / 60:.1f} minutes.")
        with open(os.path.join(HERE, "original_model_full_output.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(OUT) + "\n")
        print("Saved to original_model_full_output.txt")
