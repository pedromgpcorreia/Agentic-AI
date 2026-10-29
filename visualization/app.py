"""Browser interface of the telecom model with Mesa's own visualization (SolaraViz).

This is the Mesa equivalent of the NetLogo interface: sliders and Reset / Play / Step
buttons on the left, the consumers' network and the plots on the right, in a web page.

Install once:   python -m pip install "mesa[viz]>=3.5,<4"
Run:            solara run visualization/app.py      (repository root; opens http://localhost:8765)

The window version without a browser is visualization/live.py (only needs matplotlib).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import solara  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
from mesa.visualization import SolaraViz, make_plot_component  # noqa: E402

from consumer_choice.calibrated import CALIBRATED  # noqa: E402
from consumer_choice.learning import BanditPricePolicy, FixedPricePolicy  # noqa: E402
from consumer_choice.telecom import TelecomMarketModel  # noqa: E402

COLORS = ["#2a78d6", "#eb6834", "#1a9e77", "#7a3fbf"]
NOWO_COLOR = "#9a9a9a"
POLICIES = ["List prices", "Learned (bandit)", "All at 0.90"]
ANACOM = {19: 2.8, 25: 3.0, 28: 3.2}           # DIGI/NOWO share (%), ANACOM


class LiveTelecomModel(TelecomMarketModel):
    """Calibrated model with the price policy chosen in the interface."""

    def __init__(self, norm_influence=0.10, exploration=0.03, entry_tick=12,
                 policy=POLICIES[0], seed=1):
        params = dict(CALIBRATED, norm_influence=norm_influence, exploration=exploration)
        if abs(norm_influence - CALIBRATED["norm_influence"]) > 1e-9:
            params.pop("brand_constants")      # constants were calibrated for w = 0.10
        super().__init__(entry_tick=int(entry_tick), rng=int(seed), **params)
        if policy == POLICIES[1]:
            self.price_policy = BanditPricePolicy()
        elif policy == POLICIES[2]:
            self.price_policy = FixedPricePolicy((0.9, 0.9, 0.9))


def network_figure(model):
    """Consumers at their positions, coloured by operator, with friendship links."""
    fig = Figure(figsize=(6, 6))
    ax = fig.subplots()
    segs = [(c.pos, f.pos) for c in model.consumers for f in c.friends if id(c) < id(f)]
    ax.add_collection(LineCollection(segs, colors="#d8d7d3", linewidths=0.4, zorder=1))
    colours = [COLORS[c.choice] if (c.choice < 3 or model.digi_entered) else NOWO_COLOR
               for c in model.consumers]
    ax.scatter([c.pos[0] for c in model.consumers], [c.pos[1] for c in model.consumers],
               s=12, c=colours, zorder=2, edgecolors="white", linewidths=0.3)
    ax.set_xlim(-26.5, 26.5)
    ax.set_ylim(-26.5, 26.5)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    name3 = "DIGI" if model.digi_entered else "NOWO"
    ax.set_title(f"Month {model.steps} - population {len(model.consumers)} - "
                 f"blue MEO, orange NOS, green Vodafone, "
                 f"{'purple' if model.digi_entered else 'grey'} {name3}", fontsize=8, loc="left")
    return fig


def NetworkView(model):
    return solara.FigureMatplotlib(network_figure(model), format="png")


def anacom_points(ax):
    ax.scatter([t for t in ANACOM], [v / 100 for v in ANACOM.values()], color="k", s=12,
               zorder=5, label="ANACOM (DIGI)")
    ax.set_ylabel("market share")
    ax.legend(fontsize=7)


model_params = {
    "norm_influence": {"type": "SliderFloat", "value": 0.10, "label": "Norm influence (w)",
                       "min": 0.0, "max": 0.5, "step": 0.01},
    "exploration": {"type": "SliderFloat", "value": 0.03, "label": "Exploration",
                    "min": 0.0, "max": 0.1, "step": 0.005},
    "entry_tick": {"type": "SliderInt", "value": 12, "label": "DIGI entry (month)",
                   "min": 0, "max": 36, "step": 1},
    "policy": {"type": "Select", "value": POLICIES[0], "values": POLICIES,
               "label": "Incumbents' prices after entry"},
    "seed": {"type": "SliderInt", "value": 1, "label": "Random seed",
             "min": 1, "max": 100, "step": 1},
}

shares = make_plot_component(
    {"share_MEO": COLORS[0], "share_NOS": COLORS[1], "share_Vodafone": COLORS[2],
     "share_DIGI": COLORS[3]}, post_process=anacom_points)
prices = make_plot_component(
    {"price_MEO": COLORS[0], "price_NOS": COLORS[1], "price_Vodafone": COLORS[2],
     "price_DIGI": COLORS[3]})
contracts = make_plot_component("pct_contracted")

page = SolaraViz(
    LiveTelecomModel(),
    components=[(NetworkView, 0), shares, prices, contracts],
    model_params=model_params,
    name="Consumer Choice - DIGI entry",
    play_interval=150,
)
