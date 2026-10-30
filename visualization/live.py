"""Live view of the telecom model, in the style of the NetLogo interface.

Runs the real model (consumer_choice/telecom.py) month by month and draws:
  * left: the consumers at their positions, coloured by operator, with their friendship links;
  * right: market shares (with the ANACOM points for DIGI), prices and the share under contract.

Controls (bottom of the window):
  Setup        builds a new market with the slider values (like NetLogo "setup")
  Go / Pause   runs month after month (like NetLogo "go" forever)
  Step         advances one month (like "go once")
  sliders      norm influence (w), exploration (e), DIGI entry month, speed
  radio        price policy of MEO/NOS/Vodafone after the entry:
               list prices | learned prices (bandit, task 5) | all at 0.90

Usage (repository root):
  python visualization/live.py                    # interactive window
  python visualization/live.py --gif out.gif      # headless: save an animation (for slides)
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import warnings  # noqa: E402

warnings.filterwarnings("ignore")

import matplotlib  # noqa: E402

if "--gif" in sys.argv:
    matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402
from matplotlib.widgets import Button, RadioButtons, Slider  # noqa: E402

from consumer_choice.calibrated import CALIBRATED  # noqa: E402
from consumer_choice.learning import BanditPricePolicy, FixedPricePolicy  # noqa: E402
from consumer_choice.telecom import TelecomMarketModel  # noqa: E402

LABELS = ["MEO", "NOS", "Vodafone", "NOWO / DIGI"]
COLORS = ["#2a78d6", "#eb6834", "#1a9e77", "#7a3fbf"]
NOWO_COLOR = "#9a9a9a"
POLICIES = ["List prices", "Learned (bandit)", "All at 0.90"]
MONTHS_PT = ["Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct"]
ANACOM = {19: 2.8, 25: 3.0, 28: 3.2}       # DIGI/NOWO share (%), ANACOM Q2 2025, Q4 2025, Q1 2026


def month_label(t):
    return f"{MONTHS_PT[t % 12]} {2023 + (t + 10) // 12}"


class LiveView:
    def __init__(self, seed=1):
        self.seed = seed
        self.running = False
        self.fig = plt.figure(figsize=(13, 7.5))
        self.fig.canvas.manager.set_window_title("Consumer Choice - DIGI entry (live)") \
            if hasattr(self.fig.canvas, "manager") and self.fig.canvas.manager else None
        gs = self.fig.add_gridspec(3, 2, left=0.03, right=0.98, top=0.95, bottom=0.30,
                                   width_ratios=[1.15, 1], hspace=0.45, wspace=0.12)
        self.ax_net = self.fig.add_subplot(gs[:, 0])
        self.ax_share = self.fig.add_subplot(gs[0, 1])
        self.ax_price = self.fig.add_subplot(gs[1, 1])
        self.ax_contract = self.fig.add_subplot(gs[2, 1])
        self.build_controls()
        self.setup()

    # ---------------------------------------------------------------- controls
    def build_controls(self):
        f = self.fig
        self.s_w = Slider(f.add_axes([0.08, 0.15, 0.25, 0.025]), "norm w",
                          0.0, 0.5, valinit=CALIBRATED["norm_influence"], valstep=0.01)
        self.s_e = Slider(f.add_axes([0.08, 0.11, 0.25, 0.025]), "exploration",
                          0.0, 0.1, valinit=CALIBRATED["exploration"], valstep=0.005)
        self.s_entry = Slider(f.add_axes([0.08, 0.07, 0.25, 0.025]), "DIGI entry",
                              0, 36, valinit=12, valstep=1)
        self.s_speed = Slider(f.add_axes([0.08, 0.03, 0.25, 0.025]), "speed",
                              1, 10, valinit=6, valstep=1)
        self.radio = RadioButtons(f.add_axes([0.40, 0.03, 0.14, 0.15]), POLICIES, active=0)
        self.b_setup = Button(f.add_axes([0.60, 0.11, 0.08, 0.05]), "Setup")
        self.b_go = Button(f.add_axes([0.70, 0.11, 0.08, 0.05]), "Go / Pause")
        self.b_step = Button(f.add_axes([0.80, 0.11, 0.08, 0.05]), "Step")
        self.b_setup.on_clicked(lambda _: self.setup())
        self.b_go.on_clicked(lambda _: self.toggle())
        self.b_step.on_clicked(lambda _: self.step())
        self.info = f.text(0.60, 0.04, "", fontsize=9, family="monospace", va="bottom")
        f.text(0.60, 0.18, "Sliders and policy apply on Setup (as in NetLogo).", fontsize=8,
               color="#52514e")
        self.timer = f.canvas.new_timer(interval=100)
        self.timer.add_callback(self.tick)

    # ---------------------------------------------------------------- model
    def setup(self):
        self.running = False
        params = dict(CALIBRATED, norm_influence=float(self.s_w.val),
                      exploration=float(self.s_e.val))
        if abs(params["norm_influence"] - CALIBRATED["norm_influence"]) > 1e-9:
            params.pop("brand_constants")       # constants were calibrated for w = 0.10
        self.model = TelecomMarketModel(entry_tick=int(self.s_entry.val), rng=self.seed, **params)
        pol = self.radio.value_selected
        if pol == POLICIES[1]:
            self.model.price_policy = BanditPricePolicy(seed=self.seed)
        elif pol == POLICIES[2]:
            self.model.price_policy = FixedPricePolicy((0.9, 0.9, 0.9))
        self.seed += 1
        self.hist = {"t": [], "share": [[] for _ in range(4)], "price": [[] for _ in range(4)],
                     "contract": []}
        self.record()
        self.draw_network(full=True)
        self.draw_series()

    def record(self):
        m = self.model
        self.hist["t"].append(m.steps)
        for k in range(4):
            self.hist["share"][k].append(m.share(k) * 100)
            self.hist["price"][k].append(m.price[k])
        self.hist["contract"].append(
            sum(c.contract_left > 0 for c in m.consumers) / len(m.consumers) * 100)

    def step(self):
        n_links = sum(len(c.friends) for c in self.model.consumers)
        self.model.step()
        self.record()
        changed = n_links != sum(len(c.friends) for c in self.model.consumers)
        self.draw_network(full=changed or self.model.steps % 6 == 0)
        self.draw_series()
        self.fig.canvas.draw_idle()

    def toggle(self):
        self.running = not self.running
        self.timer.interval = int(1100 - 100 * self.s_speed.val)
        (self.timer.start if self.running else self.timer.stop)()

    def tick(self):
        if self.running:
            self.step()

    # ---------------------------------------------------------------- drawing
    def colours(self):
        digi = self.model.digi_entered
        return [COLORS[c.choice] if (c.choice < 3 or digi) else NOWO_COLOR
                for c in self.model.consumers]

    def draw_network(self, full):
        ax, m = self.ax_net, self.model
        if full:
            ax.clear()
            segs = [(c.pos, f.pos) for c in m.consumers for f in c.friends if id(c) < id(f)]
            ax.add_collection(LineCollection(segs, colors="#d8d7d3", linewidths=0.4, zorder=1))
            xs = [c.pos[0] for c in m.consumers]
            ys = [c.pos[1] for c in m.consumers]
            self.scatter = ax.scatter(xs, ys, s=14, c=self.colours(), zorder=2,
                                      edgecolors="white", linewidths=0.3)
            ax.set_xlim(-26.5, 26.5)
            ax.set_ylim(-26.5, 26.5)
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_aspect("equal")
            for s in ax.spines.values():
                s.set_color("#d8d7d3")
        else:
            self.scatter.set_facecolor(self.colours())
        name3 = "DIGI" if m.digi_entered else "NOWO"
        ax.set_title(f"Month {m.steps}  ({month_label(m.steps)})   population {len(m.consumers)}"
                     f"   [{name3}]", loc="left", fontsize=10)
        handles = [plt.Line2D([], [], marker="o", ls="", color=COLORS[k], label=LABELS[k])
                   for k in range(4)]
        ax.legend(handles=handles, loc="lower left", fontsize=8, ncol=4, frameon=True,
                  bbox_to_anchor=(0, -0.07))

    def draw_series(self):
        h, m = self.hist, self.model
        t = h["t"]
        for ax in (self.ax_share, self.ax_price, self.ax_contract):
            ax.clear()
            ax.grid(color="#e4e3df", lw=0.5)
            for s in ("top", "right"):
                ax.spines[s].set_visible(False)
            if m.entry_tick is not None:
                ax.axvline(m.entry_tick, color="#bdbcb8", lw=0.8, ls="--")
        for k in range(4):
            self.ax_share.plot(t, h["share"][k], color=COLORS[k], lw=1.4, label=LABELS[k])
            self.ax_price.step(t, h["price"][k], where="post", color=COLORS[k], lw=1.4)
        self.ax_share.scatter(list(ANACOM), list(ANACOM.values()), color="k", s=12, zorder=5,
                              label="ANACOM (DIGI)")
        self.ax_share.set_ylabel("share (%)")
        self.ax_share.set_ylim(0, 55)
        self.ax_share.legend(fontsize=7, ncol=5, loc="upper right", frameon=False)
        self.ax_price.set_ylabel("list price (EUR)")
        self.ax_price.set_ylim(15, 46)
        self.ax_contract.plot(t, h["contract"], color="#1a1a1a", lw=1.4)
        self.ax_contract.set_ylabel("under contract (%)")
        self.ax_contract.set_ylim(0, 90)
        self.ax_contract.set_xlabel("month")
        xmax = max(36, t[-1] + 1)
        for ax in (self.ax_share, self.ax_price, self.ax_contract):
            ax.set_xlim(0, xmax)
        s = [h["share"][k][-1] for k in range(4)]
        self.info.set_text(
            f"MEO {s[0]:5.1f}%  NOS {s[1]:5.1f}%  Vodafone {s[2]:5.1f}%  "
            f"{'DIGI' if m.digi_entered else 'NOWO'} {s[3]:4.1f}%\n"
            f"switches this month {m.month_switches:3d}   renewals {m.month_renewals:3d}   "
            f"avg price paid {sum(c.contract_price for c in m.consumers) / len(m.consumers):5.2f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gif", help="save an animation instead of opening a window")
    ap.add_argument("--months", type=int, default=36)
    ap.add_argument("--policy", type=int, default=1, help="0 list, 1 bandit, 2 all at 0.90 (gif)")
    args = ap.parse_args()
    view = LiveView()
    if not args.gif:
        plt.show()
        return
    from matplotlib.animation import PillowWriter
    view.radio.set_active(args.policy)
    view.setup()
    writer = PillowWriter(fps=4)
    with writer.saving(view.fig, args.gif, dpi=70):
        writer.grab_frame()
        for _ in range(args.months):
            view.step()
            writer.grab_frame()
    view.fig.savefig(os.path.splitext(args.gif)[0] + ".png", dpi=110)
    print("saved", args.gif)


if __name__ == "__main__":
    main()
