"""Browser interface of the telecom model with Mesa's own visualization (SolaraViz).

This is the Mesa equivalent of the NetLogo interface: sliders and Reset / Play / Step
buttons on the left, the consumers' network and the plots on the right, in a web page.

Install once:   python -m pip install "mesa[viz,network]>=3.5,<4" "ipyvue<3" "ipyvuetify<3"
Run:            solara run visualization/app.py      (repository root; opens http://localhost:8765)

The window version without a browser is visualization/live.py (only needs matplotlib).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import solara  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
from mesa.visualization import SolaraViz  # noqa: E402

import inspect  # noqa: E402

from consumer_choice.calibrated import CALIBRATED  # noqa: E402
from consumer_choice.learning import BanditPricePolicy, FixedPricePolicy  # noqa: E402
from consumer_choice.telecom import TelecomMarketModel  # noqa: E402
from visualization.safe_plot import make_safe_plot_component  # noqa: E402

COLORS = ["#2a78d6", "#eb6834", "#1a9e77", "#7a3fbf"]
NOWO_COLOR = "#9a9a9a"
POLICIES = ["List prices", "Learned (bandit)", "All at 0.90"]
ANACOM = {19: 2.8, 25: 3.0, 28: 3.2}           # DIGI/NOWO share (%), ANACOM


class LiveTelecomModel(TelecomMarketModel):
    """Calibrated model with the price policy chosen in the interface."""

    def __init__(self, norm_influence=0.10, exploration=CALIBRATED["exploration"], entry_tick=12,
                 policy=POLICIES[0], seed=1):
        params = dict(CALIBRATED, norm_influence=norm_influence, exploration=exploration)
        if abs(norm_influence - CALIBRATED["norm_influence"]) > 1e-9:
            params.pop("brand_constants")      # constants were calibrated for w = 0.10
        super().__init__(entry_tick=int(entry_tick), rng=int(seed), **params)
        if policy == POLICIES[1]:
            self.price_policy = BanditPricePolicy(seed=int(seed))
        elif policy == POLICIES[2]:
            self.price_policy = FixedPricePolicy((0.9, 0.9, 0.9))


def network_figure(model):
    """Consumers at their positions, coloured by operator, with friendship links."""
    fig = Figure(figsize=(6, 6))
    ax = fig.subplots()
    consumers = list(model.consumers)            # snapshot: the model may be stepping
    segs = [(c.pos, f.pos) for c in consumers for f in list(c.friends) if id(c) < id(f)]
    ax.add_collection(LineCollection(segs, colors="#d8d7d3", linewidths=0.4, zorder=1))
    colours = [COLORS[c.choice] if (c.choice < 3 or model.digi_entered) else NOWO_COLOR
               for c in consumers]
    ax.scatter([c.pos[0] for c in consumers], [c.pos[1] for c in consumers],
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
    return solara.FigureMatplotlib(network_figure(model), format="png", dpi=72)


def anacom_points(ax):
    ax.scatter([t for t in ANACOM], [v / 100 for v in ANACOM.values()], color="k", s=12,
               zorder=5, label="ANACOM (DIGI)")
    ax.set_ylabel("market share")
    ax.legend(fontsize=7)


def dash_nos(ax):
    """MEO and NOS share the same list price: dash NOS so that MEO stays visible."""
    for line in ax.get_lines():
        if line.get_label() == "price_NOS":
            line.set_linestyle("--")
    ax.set_ylabel("list price (EUR/month)")
    ax.legend(fontsize=7)


def label_contracts(ax):
    ax.set_ylabel("share under contract")


# fixed parameters of the report, shown in the page and not changeable from it
_DEF = {k: v.default for k, v in inspect.signature(TelecomMarketModel.__init__).parameters.items()
        if v.default is not inspect.Parameter.empty}
_DEF.update(CALIBRATED)
_BANDIT = {k: v.default for k, v in inspect.signature(BanditPricePolicy.__init__).parameters.items()
           if v.default is not inspect.Parameter.empty}


def _pct(x):
    return f"{x * 100:g}%"


def FixedParameters(model):
    d = _DEF
    ops = " / ".join(d["names"])
    rows = [
        ("Households at the start (minimum)", f"{d['num_consumers']} ({d['min_consumers']})"),
        ("Average connections (friends)", d["avg_connections"]),
        ("Information exchange", d["information_exchange"]),
        (f"Initial shares {ops}", " / ".join(f"{x:g}%" for x in d["initial_shares"]) + " (ANACOM, Q3 2024)"),
        (f"List prices {ops}", " / ".join(f"€{x:.2f}" for x in d["prices"])),
        (f"Quality {ops}", " / ".join(f"{x:.3f}" for x in d["qualities"]) + " (ANACOM complaints)"),
        ("Brand constants", " / ".join(f"{x:+.4f}" for x in d["brand_constants"]) + " (calibrated)"),
        ("Price weight", f"{model.price_weight:.4f} (from the norm weight, Confraria et al.)"),
        ("Contract length incumbents / DIGI", f"{d['contract_months'][0]} / {d['digi_contract']} months"),
        ("Households under contract at the start", _pct(d["initial_contracted"])),
        ("Initial contracts that are renewals", _pct(d["initial_renewed"])),
        ("Renewal discount", _pct(d["renewal_discount"])),
        ("Cost of commitment (mean, spread)", f"€{d['commit_cost_mean']:.2f}/month, ±{_pct(d['commit_cost_spread'])}"),
        ("Early exit", "penalty of Lei 16/2022" if d["exit_rule"] == "penalty" else d["exit_rule"]),
        ("DIGI price", f"€{d['digi_price']:.2f}/month"),
        ("DIGI quality", f"{d['digi_quality_start']:.3f} → {d['digi_quality_end']:.3f} in {d['digi_maturation']} months"),
        ("Exits / net growth of households", f"{_pct(d['exit_rate'])} per month / {_pct(d['net_growth_year'])} per year"),
        ("Margin of the incumbents", _pct(d["margin"])),
        ("Bandit (learned prices)", f"ε = {_BANDIT['epsilon']}, α = {_BANDIT['alpha']}, decision every "
                                    f"{_BANDIT['period']} months, arms × " + ", ".join(f"{a:.2f}" for a in _BANDIT["arms"])),
    ]
    table = "\n".join(f"| {k} | {v} |" for k, v in rows)
    return solara.Markdown(
        "**Fixed parameters of the report** (not changeable here; see Sect. 4 of the report)\n\n"
        "| Parameter | Value |\n|---|---|\n" + table)


model_params = {
    "norm_influence": {"type": "SliderFloat", "value": 0.10, "label": "Norm influence (w)",
                       "min": 0.0, "max": 0.5, "step": 0.01},
    "exploration": {"type": "SliderFloat", "value": CALIBRATED["exploration"], "label": "Exploration",
                    "min": 0.0, "max": 0.1, "step": 0.005},
    "entry_tick": {"type": "SliderInt", "value": 12, "label": "DIGI entry (month)",
                   "min": 0, "max": 36, "step": 1},
    "policy": {"type": "Select", "value": POLICIES[0], "values": POLICIES,
               "label": "Incumbents' prices after entry"},
    "seed": {"type": "SliderInt", "value": 1, "label": "Random seed",
             "min": 1, "max": 100, "step": 1},
}

shares = make_safe_plot_component(
    {"share_MEO": COLORS[0], "share_NOS": COLORS[1], "share_Vodafone": COLORS[2],
     "share_DIGI": COLORS[3]}, post_process=anacom_points, xlabel="Month")
prices = make_safe_plot_component(
    {"price_MEO": COLORS[0], "price_NOS": COLORS[1], "price_Vodafone": COLORS[2],
     "price_DIGI": COLORS[3]}, post_process=dash_nos, xlabel="Month")
contracts = make_safe_plot_component("pct_contracted", post_process=label_contracts, xlabel="Month")

page = SolaraViz(
    LiveTelecomModel(),
    components=[(NetworkView, 0), shares, prices, contracts, (FixedParameters, 0)],
    model_params=model_params,
    name="Consumer Choice - DIGI entry",
    play_interval=100,
    render_interval=1,
)
