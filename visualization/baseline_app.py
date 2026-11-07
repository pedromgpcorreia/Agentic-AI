"""Browser interface of the original Consumer Choice model with Mesa's own visualization (SolaraViz).

This is the Mesa equivalent of the NetLogo interface of the original model: sliders and
Reset / Play / Step buttons on the left; the consumers in their friendship network and the
plots of the outputs (orange and blue market shares, clustering) on the right.

Install once:   python -m pip install -r requirements.txt
Run:            python original_model.py            (opens this page, then runs the report's simulations)
     or only:   solara run visualization/baseline_app.py      (opens http://localhost:8765)

The defaults are the baseline parameters of the report.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import solara  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
from mesa.visualization import SolaraViz  # noqa: E402

from consumer_choice.model import ORANGE, ConsumerChoiceModel  # noqa: E402
from experiments.run_experiments import BASELINE  # noqa: E402
from visualization.safe_plot import make_safe_plot_component  # noqa: E402

ORANGE_C, BLUE_C = "#eb6834", "#2a78d6"


class LiveConsumerChoiceModel(ConsumerChoiceModel):
    """Original model with the random seed as an interface parameter."""

    def __init__(self, seed=1, **params):
        super().__init__(rng=int(seed), **params)


def network_figure(model):
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
    return fig


def NetworkView(model):
    return solara.FigureMatplotlib(network_figure(model), format="png", dpi=72)


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

counts = make_safe_plot_component({"orange": ORANGE_C, "blue": BLUE_C}, post_process=label_counts, xlabel="Tick")
clustering = make_safe_plot_component({"clustering": "#1a1a1a"}, post_process=label_clustering, xlabel="Tick")

page = SolaraViz(
    LiveConsumerChoiceModel(**BASELINE),
    components=[(NetworkView, 0), counts, clustering, (HowTo, 0)],
    model_params=model_params,
    name="Consumer Choice - original model",
    play_interval=100,
    render_interval=1,
)
