"""NEW MODEL: DIGI's entry into the Portuguese market of bundled services, with learning
incumbents, implemented in Python with Mesa (tasks 3 to 6).

Self-contained file: the model, the price policies (learning), the calibrated parameters,
the simulations of the report and the interface are all in this file. It needs no other
file of the project.

What it does
    1. Opens the model's interface in the browser (Mesa SolaraViz, the equivalent of the
       NetLogo interface): the households in their friendship network, coloured by operator
       (NOWO in grey, DIGI in purple from its entry in month 12), and the plots of market
       shares (with the ANACOM data), list prices and the share under contract, with
       Reset / Play / Step buttons and sliders. The defaults are the calibrated values of the
       report; choose "Learned (bandit)" to see the incumbents learn their prices (task 5).
    2. When you press Enter in the terminal, closes the interface and runs every simulation
       of the report for this model, with the same parameters and random seeds, so the
       printed numbers are those of the report: the calibration, the 23 price scenarios with
       fixed and learned prices (30 runs x 132 months, Tables 15 and 16) and the sensitivity
       analysis (base and 9 variants x 5 scenarios x 20 runs, Table 17).
    Results are printed and saved to new_model_full_output.txt, next to this file.

The model in short (1 tick = 1 month)
    About 1000 households linked in a friendship network choose among MEO, NOS, Vodafone and
    NOWO, which becomes DIGI in month 12 (EUR 22/month, 3-month contract, quality that
    improves over 18 months). Each month a household keeps its operator by habit, explores
    another one, or picks the operator with the highest utility: own experience, information
    from friends, the social norm (share of friends) and the price. 24-month contracts with
    the early-exit penalty of Lei 16/2022 and renewal discounts slow switching. After the
    entry the incumbents either keep fixed prices or learn them with an epsilon-greedy
    bandit (every 3 months they pick a multiplier 1.00 to 0.80 of the list price by profit).

Requirements
    Python 3.12 or later (required by Mesa 3.5). Install once:
        python -m pip install "mesa[viz,network]>=3.5,<4" "ipyvue<3" "ipyvuetify<3" numpy pandas scipy matplotlib

How to run
    VS Code: open this file, select the Python interpreter where the requirements are
    installed and press Run.
    Terminal, from the folder of this file:
        python new_model_full.py                    # interface, then the simulations
        python new_model_full.py --interface-only   # only the interface
        python new_model_full.py --no-interface     # only the simulations

Time
    The simulations use all CPU cores: about 11 minutes on 8 cores.
"""
import inspect
import math
import os
import random
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
# Extension of the original Consumer Choice model to the Portuguese bundled-services market:
#   * N operators (MEO, NOS, Vodafone and NOWO, which becomes DIGI at the entry tick);
#   * price in the product utility, with a weight tied to the norm (Confraria et al., 2017);
#   * loyalty contracts with early-exit penalties (Lei 16/2022) or full lock-in;
#   * renewal at the end of the contract decided by the consumer;
#   * DIGI quality that improves with time since entry;
#   * consumers that leave and enter the market (variable population, minimum size).
# The decision structure of the original model is kept: habit -> exploration -> utility.
EUR_PER_SHARE_UNIT = 10.22   # Confraria et al. (2017), Table 4: 0.189 / 0.25 / 0.074


class Customer(mesa.Agent):
    """A household that subscribes to one bundle and is linked to friends."""

    def __init__(self, model, choice, pos):
        super().__init__(model)
        n = model.n_ops
        self.choice = choice
        self.utilities = [1.0 if k == choice else 0.0 for k in range(n)]
        self.satisfaction = model.satisfaction(choice)
        self.personal_experience = [0.0] * n
        self.pos = pos
        self.friends = []
        # contract state
        self.contract_left = 0          # months of commitment left (0 = no contract)
        self.contract_elapsed = 0       # months since the contract started
        self.contract_price = model.price[choice]
        self.renewal_pending = False    # contract ended this month: renewal offer pending
        self.commit_cost = 0.0          # euros/month the household needs to accept 24 months

    # ---------------------------------------------------------------- decision
    def consume(self):
        """Habit -> exploration -> utility, subject to the contract."""
        m = self.model
        old = self.choice
        candidate = old
        if self.random.random() < self.satisfaction:
            pass                                            # habit
        elif self.random.random() < m.exploration:
            others = [k for k in m.active_ops() if k != old]
            # no random draw when there is a single alternative (as in the baseline)
            candidate = others[0] if len(others) == 1 else self.random.choice(others)
        else:
            u = self.utilities
            act = m.active_ops()
            best = max(u[k] for k in act)
            if any(u[k] != best for k in act):
                # baseline rule for two products: strict comparison, first index wins ties
                candidate = next(k for k in act if u[k] == best)
        if candidate != old and self.can_leave(candidate):
            self.switch_to(candidate)
            m.month_switches += 1
            if self.renewal_pending:
                m.month_switch_at_end += 1
        elif self.renewal_pending:
            self.offer_renewal()
        self.renewal_pending = False
        self.satisfaction = m.satisfaction(self.choice)

    def can_leave(self, target):
        """Early exit allowed only if the savings cover the legal penalty."""
        m = self.model
        if not m.contracts or self.contract_left <= 0:
            return True
        if m.exit_rule == "lock":
            return False
        months_left = self.contract_left
        rate = 0.50 if self.contract_elapsed < 12 else 0.30      # Lei 16/2022
        penalty = rate * months_left * self.contract_price
        savings = months_left * (self.contract_price - m.price[target])
        return savings - penalty > 0

    def switch_to(self, k):
        m = self.model
        self.choice = k
        self.contract_price = m.price[k]
        if m.contracts:
            self.contract_left = m.contract_months[k]
            self.contract_elapsed = 0

    def offer_renewal(self):
        """Stayed after the contract ended: accept a discounted 24-month contract?"""
        m = self.model
        k = self.choice
        if not m.offers_renewal[k]:
            self.contract_price = m.price[k]
            return
        m.month_renewal_offers += 1
        discount = m.renewal_discount * m.price[k]
        if discount >= self.commit_cost:
            self.contract_price = m.price[k] - discount
            self.contract_left = m.contract_months[k]
            self.contract_elapsed = 0
            m.month_renewals += 1
        else:
            self.contract_price = m.price[k]                    # month-to-month, no lock-in

    # ---------------------------------------------------------------- learning
    def update_utilities(self):
        """Own experience, information from friends, norm and price (baseline + price)."""
        m = self.model
        n_friends = len(self.friends)
        for option in m.active_ops():
            if self.choice == option:
                self.personal_experience[option] = m.quality[option]
            neighbor_info = 0.0
            if (self.random.random() <= m.information_exchange
                    and any(f.choice == option for f in self.friends)):
                neighbor_info = m.quality[option]
            norm_util = 0.0
            if n_friends:
                users = sum(f.choice == option for f in self.friends)
                norm_util = users / n_friends
            price = self.contract_price if option == self.choice else m.price[option]
            prod_util = ((self.personal_experience[option] + neighbor_info) / 2
                         - m.price_weight * price)
            self.utilities[option] = (m.norm_influence * norm_util
                                      + (1 - m.norm_influence) * prod_util
                                      + m.brand_constant[option])

    def advance_contract(self):
        if self.contract_left > 0:
            self.contract_left -= 1
            self.contract_elapsed += 1
            if self.contract_left == 0:
                self.renewal_pending = True


class TelecomMarketModel(mesa.Model):
    """Market of bundled services with the entry of DIGI."""

    def __init__(self,
                 # population and network
                 num_consumers=1000, min_consumers=1000, avg_connections=5,
                 # operators (index 3: NOWO before entry, DIGI after)
                 names=("MEO", "NOS", "Vodafone", "NOWO"),
                 initial_shares=(41.8, 35.0, 20.6, 2.6),
                 prices=(42.49, 42.49, 40.50, 26.35),
                 qualities=(0.848, 0.784, 0.776, 0.572),
                 contract_months=(24, 24, 24, 24),
                 brand_constants=None,
                 # behaviour (baseline parameters)
                 norm_influence=0.15, information_exchange=0.05, exploration=0.01,
                 price_weight=None,
                 # contracts
                 contracts=True, exit_rule="penalty", initial_contracted=0.7, initial_renewed=0.0,
                 renewal_discount=0.10, commit_cost_mean=5.25, commit_cost_spread=0.5,
                 # DIGI entry
                 entry_tick=12, digi_price=22.00, digi_contract=3,
                 digi_quality_start=0.572, digi_quality_end=0.756, digi_maturation=18,
                 # demography
                 demography=True, exit_rate=0.005, net_growth_year=0.01,
                 # firms
                 margin=0.40,
                 rng=None):
        super().__init__(rng=rng)
        self.n_ops = len(names)
        self.names = list(names)
        self.price = list(prices)
        self.base_price = list(prices)
        self.quality = list(qualities)
        self.contract_months = list(contract_months)
        self.offers_renewal = [True] * self.n_ops
        self.brand_constant = list(brand_constants) if brand_constants else [0.0] * self.n_ops
        self.norm_influence = norm_influence
        self.information_exchange = information_exchange
        self.exploration = exploration
        if price_weight is None:      # same norm/price ratio as Confraria et al. (2017)
            price_weight = (norm_influence / ((1 - norm_influence) * EUR_PER_SHARE_UNIT)
                            if norm_influence < 1 else 0.0)
        self.price_weight = price_weight
        self.contracts = contracts
        self.exit_rule = exit_rule
        self.renewal_discount = renewal_discount
        self.initial_renewed = initial_renewed
        self.commit_cost_mean = commit_cost_mean
        self.commit_cost_spread = commit_cost_spread
        self.entry_tick = entry_tick
        self.digi_price = digi_price
        self.digi_contract = digi_contract
        self.digi_quality_start = digi_quality_start
        self.digi_quality_end = digi_quality_end
        self.digi_maturation = digi_maturation
        self.digi_entered = False
        self.demography = demography
        self.exit_rate = exit_rate
        self.entry_rate = exit_rate + ((1 + net_growth_year) ** (1 / 12) - 1)
        self.min_consumers = min_consumers
        self.avg_connections = avg_connections
        self.margin = margin
        self.unit_cost = [(1 - margin) * p for p in self.base_price]
        self.price_policy = None       # set by the learning extension (task 5)
        self.month_reset()

        # consumers: initial product drawn from the market shares
        scale = 100 if all(float(s).is_integer() for s in initial_shares) else 1000
        cum, acc = [], 0.0
        for s in initial_shares:
            acc += s * scale / 100
            cum.append(acc)
        for _ in range(num_consumers):
            r = self.random.randrange(scale)
            choice = next((k for k, c in enumerate(cum) if r < c), self.n_ops - 1)
            pos = (self.random.uniform(-25.5, 25.5), self.random.uniform(-25.5, 25.5))
            Customer(self, choice, pos)
        self.consumers = list(self.agents)
        self.build_network(avg_connections)

        # contract state and commitment costs (drawn after the network, so the
        # baseline random sequence is unchanged when contracts are switched off)
        if contracts:
            for c in self.consumers:
                self.init_contract(c, initial_contracted)

        self.datacollector = mesa.DataCollector(model_reporters=self.reporters())
        self.datacollector.collect(self)

    # ------------------------------------------------------------- helpers
    def active_ops(self):
        return range(self.n_ops)

    def satisfaction(self, choice):
        return math.log10(1 + 9 * self.quality[choice])

    def month_reset(self):
        self.month_switches = 0
        self.month_switch_at_end = 0
        self.month_renewal_offers = 0
        self.month_renewals = 0
        self.month_entries = 0
        self.month_exits = 0

    def draw_commit_cost(self):
        lo = self.commit_cost_mean * (1 - self.commit_cost_spread)
        hi = self.commit_cost_mean * (1 + self.commit_cost_spread)
        return self.random.uniform(lo, hi)

    def init_contract(self, c, p_contracted):
        c.commit_cost = self.draw_commit_cost()
        if self.random.random() < p_contracted:
            length = self.contract_months[c.choice]
            c.contract_elapsed = self.random.randrange(length)
            c.contract_left = length - c.contract_elapsed
        c.contract_price = self.price[c.choice]
        # share of the initial contracts that are renewals (discounted price); without it
        # the average price paid drifts down during the first contract cycle
        if c.contract_left > 0 and self.initial_renewed > 0 and self.offers_renewal[c.choice]:
            if self.random.random() < self.initial_renewed:
                c.contract_price = self.price[c.choice] * (1 - self.renewal_discount)

    def build_network(self, avg_connections):
        """Baseline rule: link a random consumer to its nearest unlinked consumer."""
        num_links = (avg_connections * len(self.consumers)) / 2
        links = 0
        while links < num_links:
            a = self.random.choice(self.consumers)
            cands = [c for c in self.consumers if c is not a and c not in a.friends]
            if not cands:
                continue
            d_min = min(math.dist(a.pos, c.pos) for c in cands)
            nearest = [c for c in cands if math.dist(a.pos, c.pos) == d_min]
            target = self.random.choice(nearest)
            a.friends.append(target)
            target.friends.append(a)
            links += 1

    # ------------------------------------------------------------- events
    def enter_digi(self):
        """NOWO becomes DIGI: customers keep their contracts until they end."""
        self.digi_entered = True
        self.names[3] = "DIGI"
        self.price[3] = self.digi_price
        self.base_price[3] = self.digi_price
        self.unit_cost[3] = (1 - self.margin) * self.digi_price
        self.contract_months[3] = self.digi_contract
        self.offers_renewal[3] = False
        self.quality[3] = self.digi_quality_start

    def update_digi_quality(self):
        months = self.steps - self.entry_tick
        frac = min(1.0, max(0.0, months / self.digi_maturation))
        self.quality[3] = (self.digi_quality_start
                           + frac * (self.digi_quality_end - self.digi_quality_start))

    def demographic_turnover(self):
        for c in list(self.consumers):
            if self.random.random() < self.exit_rate:
                self.remove_consumer(c)
        n_in = len(self.consumers) * self.entry_rate
        n_in = int(n_in) + (1 if self.random.random() < n_in - int(n_in) else 0)
        n_in = max(n_in, self.min_consumers - len(self.consumers))
        for _ in range(n_in):
            self.add_consumer()

    def remove_consumer(self, c):
        for f in c.friends:
            f.friends.remove(c)
        self.consumers.remove(c)
        c.remove()
        self.month_exits += 1

    def add_consumer(self):
        """New household: links to its nearest consumers, asks friends, chooses, signs."""
        pos = (self.random.uniform(-25.5, 25.5), self.random.uniform(-25.5, 25.5))
        others = sorted(self.consumers, key=lambda o: math.dist(pos, o.pos))
        c = Customer(self, 0, pos)
        for o in others[:self.avg_connections]:
            c.friends.append(o)
            o.friends.append(c)
        n = len(c.friends)
        best, best_u = 0, None
        for k in self.active_ops():
            users = sum(f.choice == k for f in c.friends)
            info = self.quality[k] if users else 0.0
            c.personal_experience[k] = 0.0
            u = (self.norm_influence * (users / n if n else 0.0)
                 + (1 - self.norm_influence) * (info / 2 - self.price_weight * self.price[k])
                 + self.brand_constant[k])
            if best_u is None or u > best_u:
                best, best_u = k, u
        c.choice = best
        c.utilities = [0.0] * self.n_ops
        c.satisfaction = self.satisfaction(best)
        c.commit_cost = self.draw_commit_cost()
        c.contract_price = self.price[best]
        if self.contracts:
            c.contract_left = self.contract_months[best]
            c.contract_elapsed = 0
        self.consumers.append(c)
        self.month_entries += 1

    # ------------------------------------------------------------- schedule
    def step(self):
        self.month_reset()
        if self.demography:
            self.demographic_turnover()
        if self.entry_tick is not None and self.steps >= self.entry_tick:
            if not self.digi_entered:
                self.enter_digi()
            self.update_digi_quality()
        self.agents.shuffle_do("consume")
        self.agents.shuffle_do("update_utilities")
        if self.contracts:
            for c in self.consumers:
                c.advance_contract()
        if self.price_policy is not None:
            self.price_policy(self)
        if self.contracts:
            # households without a contract pay the current list price
            for c in self.consumers:
                if c.contract_left == 0 and not c.renewal_pending:
                    c.contract_price = self.price[c.choice]
        self.datacollector.collect(self)

    # ------------------------------------------------------------- outputs
    def count_choice(self, k):
        return sum(c.choice == k for c in self.consumers)

    def share(self, k):
        return self.count_choice(k) / len(self.consumers)

    def consumer_cluster(self):
        total = 0.0
        for c in self.consumers:
            if c.friends:
                same = sum(f.choice == c.choice for f in c.friends)
                total += same / len(c.friends)
        return total / len(self.consumers)

    def revenue(self, k):
        return sum(c.contract_price for c in self.consumers if c.choice == k)

    def profit(self, k):
        return sum(c.contract_price - self.unit_cost[k] for c in self.consumers if c.choice == k)

    def reporters(self):
        r = {}
        for k in range(self.n_ops):
            label = "DIGI" if k == 3 else self.names[k]
            r[f"share_{label}"] = (lambda m, k=k: m.share(k))
            r[f"price_{label}"] = (lambda m, k=k: m.price[k])
            r[f"profit_{label}"] = (lambda m, k=k: m.profit(k))
        r.update({
            "clustering": lambda m: m.consumer_cluster(),
            "population": lambda m: len(m.consumers),
            "switches": lambda m: m.month_switches,
            "switch_at_contract_end": lambda m: m.month_switch_at_end,
            "renewal_offers": lambda m: m.month_renewal_offers,
            "renewals": lambda m: m.month_renewals,
            "pct_contracted": lambda m: sum(c.contract_left > 0 for c in m.consumers) / len(m.consumers),
            "avg_price_paid": lambda m: sum(c.contract_price for c in m.consumers) / len(m.consumers),
            "digi_quality": lambda m: m.quality[3] if m.n_ops > 3 else float("nan"),
            "entries": lambda m: m.month_entries,
            "exits": lambda m: m.month_exits,
        })
        return r


# ============================================================================ calibrated parameters
# norm_influence 0.10 and exploration 0.02: grid search against the ANACOM DIGI shares
# 2.8 / 3.0 / 3.2 % at months 19 / 25 / 28; renewal discount 10 %; initial_renewed 0.48
# (share of renewals among contracts, fixed point without the entry); brand constants
# re-calibrated so that the market without the entry keeps the ANACOM Q3 2024 shares.
CALIBRATED = dict(
    norm_influence=0.10,
    exploration=0.02,
    renewal_discount=0.10,
    initial_renewed=0.48,
    brand_constants=[0.0, 0.0307, 0.0161, -0.0820],
)


# ============================================================================ price policies (task 5)
# Price changes apply to new contracts, renewals and households without a contract;
# households under contract keep the price they signed.
# price multipliers of the base price: 1.00 = list price before the entry,
# 0.80 = 20 % cut (EUR 34 for MEO/NOS), still above unit cost (0.60 x base, margin 40 %)
ARMS = (1.00, 0.95, 0.90, 0.85, 0.80)
INCUMBENTS = (0, 1, 2)


class FixedPricePolicy:
    """Constant price multipliers from the entry month on (one per incumbent)."""

    def __init__(self, multipliers=(1.0, 1.0, 1.0)):
        self.multipliers = multipliers
        self.applied = False

    def __call__(self, model):
        if model.digi_entered and not self.applied:
            for k, mult in zip(INCUMBENTS, self.multipliers):
                model.price[k] = model.base_price[k] * mult
            self.applied = True


class BanditPricePolicy:
    """Epsilon-greedy bandit per incumbent with a constant step size (Sutton & Barto, 2018,
    ch. 2), deciding every `period` months.

    Reward of a period = profit of the operator summed over the months of the period:
    sum over its customers of (price paid - unit cost). Unit cost = (1 - margin) x base price.

    Each arm is played once, in random order, before the epsilon-greedy rule starts, and
    its first reward sets its action value; this avoids a tie that would always favour
    the list price. The policy draws from its own random generator (`seed`), so the
    consumers' random draws are the same as in the fixed-price scenarios with the same seed.
    """

    def __init__(self, epsilon=0.1, alpha=0.2, period=3, arms=ARMS,
                 learn_before_entry=False, seed=None):
        self.epsilon = epsilon
        self.alpha = alpha
        self.period = period
        self.arms = list(arms)
        self.learn_before_entry = learn_before_entry
        self.random = random.Random(seed)
        self.q = {k: [None] * len(self.arms) for k in INCUMBENTS}   # None = arm not tried yet
        self.action = {k: 0 for k in INCUMBENTS}        # index of the current arm (0 = base price)
        self.acc = {k: 0.0 for k in INCUMBENTS}          # profit accumulated in the current period
        self.months = 0
        self.log = []                                    # one row per decision (explainability)

    def active(self, model):
        return self.learn_before_entry or model.digi_entered

    def __call__(self, model):
        if not self.active(model):
            return
        for k in INCUMBENTS:
            self.acc[k] += model.profit(k)
        self.months += 1
        if self.months < self.period:
            return
        for k in INCUMBENTS:
            reward = self.acc[k]
            q = self.q[k]
            a = self.action[k]
            if q[a] is None:
                q[a] = reward                            # first reward of this arm
            else:
                q[a] += self.alpha * (reward - q[a])
            untried = [i for i, v in enumerate(q) if v is None]
            if untried:
                new_a = self.random.choice(untried)
                explored = True
            elif self.random.random() < self.epsilon:
                new_a = self.random.randrange(len(self.arms))
                explored = True
            else:
                best = max(q)
                new_a = self.random.choice([i for i, v in enumerate(q) if v == best])
                explored = False
            self.log.append({"month": model.steps, "operator": model.names[k],
                             "reward": reward, "previous_arm": self.arms[a],
                             "new_arm": self.arms[new_a], "explored": explored,
                             "price": model.base_price[k] * self.arms[new_a],
                             **{f"Q_{m:.2f}": v for m, v in zip(self.arms, q)}})
            self.action[k] = new_a
            model.price[k] = model.base_price[k] * self.arms[new_a]
            self.acc[k] = 0.0
        self.months = 0


# ============================================================================ scenarios of the report
MONTHS = 132                      # 12 months before the entry + 10 years after
ENTRY = 12
OPS4 = ["MEO", "NOS", "Vodafone", "DIGI"]
OPS = ("MEO", "NOS", "Vodafone")
LIST_PRICE = {"MEO": 42.49, "NOS": 42.49, "Vodafone": 40.50}
ANACOM = {19: 2.8, 25: 3.0, 28: 3.2}            # NOWO/DIGI share (%), ANACOM
PRICING_SEEDS = range(4000, 4030)               # common random numbers across scenarios
SENSITIVITY_SEEDS = range(4000, 4020)


def pricing_scenarios():
    """Prices of the incumbents from the DIGI entry (month 12) on.

    no_entry: DIGI never enters; fixed_X: the three incumbents at X x list price;
    solo_OP_X: only OP cuts to X; bandit_e{eps}_a{alpha}: each incumbent learns its price;
    bandit_p{months}: main bandit (eps 0.10, alpha 0.2) deciding every 6 or 12 months.
    """
    sc = {"no_entry": dict(entry=False, policy=None)}
    for x in ARMS:
        sc[f"fixed_{x:.2f}"] = dict(policy=("fixed", (x, x, x)))
    for i, op in enumerate(OPS4[:3]):
        for x in (0.90, 0.80):
            mult = [1.0, 1.0, 1.0]
            mult[i] = x
            sc[f"solo_{op}_{x:.2f}"] = dict(policy=("fixed", tuple(mult)))
    for eps in (0.05, 0.10, 0.20):
        for alpha in (0.1, 0.2, 0.4):
            sc[f"bandit_e{eps:.2f}_a{alpha:.1f}"] = dict(policy=("bandit", eps, alpha, 3))
    for period in (6, 12):
        sc[f"bandit_p{period}"] = dict(policy=("bandit", 0.10, 0.2, period))
    return sc


def run_pricing(args):
    """One run of a price scenario: totals per run, monthly series and the bandit's decisions."""
    name, spec, seed = args
    warnings.filterwarnings("ignore")
    m = TelecomMarketModel(entry_tick=ENTRY if spec.get("entry", True) else None,
                           rng=seed, **CALIBRATED)
    pol = spec["policy"]
    if pol and pol[0] == "fixed":
        m.price_policy = FixedPricePolicy(pol[1])
    elif pol and pol[0] == "bandit":
        m.price_policy = BanditPricePolicy(epsilon=pol[1], alpha=pol[2], period=pol[3], seed=seed)
    for _ in range(MONTHS):
        m.step()
    df = m.datacollector.get_model_vars_dataframe()
    df["scenario"], df["seed"], df["month"] = name, seed, range(len(df))
    post = df.iloc[ENTRY + 1:]
    row = {"scenario": name, "seed": seed}
    for op in OPS4:
        row[f"profit_{op}"] = post[f"profit_{op}"].sum()          # cumulative, after entry
        row[f"share_{op}_end"] = post[f"share_{op}"].iloc[-12:].mean()
        row[f"price_{op}_mean"] = post[f"price_{op}"].mean()
    row["profit_incumbents"] = sum(row[f"profit_{op}"] for op in OPS4[:3])
    row["avg_price_paid_end"] = post.avg_price_paid.iloc[-12:].mean()
    log = None
    if pol and pol[0] == "bandit":
        log = pd.DataFrame(m.price_policy.log)
        log["scenario"], log["seed"] = name, seed
    return row, df, log


# Sensitivity (task 6): each variant changes one parameter of the calibrated model; the
# others, including the brand constants, are not re-calibrated.
# quality q = 0.80 - kappa * ln(r), r = complaints relative to the incumbents' mean;
# r is recovered from the qualities with kappa = 0.20
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


def sensitivity_scenarios():
    sc = {"fixed_1.00": ("fixed", (1.0, 1.0, 1.0))}
    for i, op in enumerate(OPS4[:3]):
        mult = [1.0, 1.0, 1.0]
        mult[i] = 0.90
        sc[f"solo_{op}_0.90"] = ("fixed", tuple(mult))
    sc["bandit"] = ("bandit",)
    return sc


def run_sensitivity(args):
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
           "share_DIGI_end": post.share_DIGI.iloc[-12:].mean()}
    for op in OPS4:
        row[f"profit_{op}"] = post[f"profit_{op}"].sum()          # cumulative, after entry
    row["profit_incumbents"] = sum(row[f"profit_{op}"] for op in OPS4[:3])
    return row


# ============================================================================ tables of the report
OUT = []


def say(text=""):
    print(text, flush=True)
    OUT.append(text)


def rnd(x, d=3):
    """Round half up on the decimal value, as in the report (0.5065 -> 0.507)."""
    return str(Decimal(repr(round(float(x), 9))).quantize(Decimal(1).scaleb(-d), ROUND_HALF_UP))


def sg(x, d=1):
    return ("+" if x >= 0 else "−") + rnd(abs(x), d)


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


def price_simulations():
    say("New model: DIGI entry and learning incumbents (tasks 3 to 5)\n")
    sc = pricing_scenarios()
    seeds = list(PRICING_SEEDS)
    out = pool_map(run_pricing, [(n, s, seed) for n, s in sc.items() for seed in seeds], "price scenarios")
    runs = pd.DataFrame([o[0] for o in out])
    series = pd.concat([o[1] for o in out])
    logs = pd.concat([o[2] for o in out if o[2] is not None])
    ref = runs[runs.scenario == "fixed_1.00"].set_index("seed")

    def paired(name, col="profit_incumbents"):
        g = runs[runs.scenario == name].set_index("seed").loc[ref.index]
        return ci((g[col] - ref[col]) / ref[col] * 100)

    fx = series[series.scenario == "fixed_1.00"].groupby("month").mean(numeric_only=True)
    cal = {t: fx.share_DIGI[t] * 100 for t in ANACOM}
    rmse = np.sqrt(np.mean([(cal[t] - v) ** 2 for t, v in ANACOM.items()]))
    say(f"Calibration ({len(seeds)} runs, seeds {seeds[0]} to {seeds[-1]}): NOWO/DIGI share")
    table(["Month", "Model", "ANACOM"], [[t, f"{cal[t]:.1f}%", f"{v:.1f}%"] for t, v in ANACOM.items()])
    say(f"  RMSE {rmse:.2f} percentage points. Incumbents at month 28: "
        + ", ".join(f"{o} {fx[f'share_{o}'][28] * 100:.1f}%" for o in OPS) + "\n")

    say("Table 15. Joint profit of the incumbents over 10 years after the entry, % against all at "
        "list price (paired by seed), DIGI share in year 10, average price paid in year 10.")
    rows = []
    for name, lab in [("no_entry", "No entry"), ("fixed_1.00", "All at list price"),
                      ("bandit_e0.10_a0.2", "Learned, every 3 months"), ("bandit_p6", "Learned, every 6 months"),
                      ("bandit_p12", "Learned, every 12 months"), ("fixed_0.95", "All at x0.95"),
                      ("fixed_0.90", "All at x0.90"), ("fixed_0.85", "All at x0.85"), ("fixed_0.80", "All at x0.80")]:
        g = runs[runs.scenario == name]
        m, lo, hi = paired(name)
        rows.append([lab, "0.0" if name == "fixed_1.00" else sg(m),
                     "reference" if name == "fixed_1.00" else f"{sg(lo)} to {sg(hi)}",
                     "n/a" if name == "no_entry" else rnd(g.share_DIGI_end.mean() * 100, 1),
                     rnd(g.avg_price_paid_end.mean(), 2)])
    table(["Scenario", "Profit (%)", "95% CI", "DIGI (%)", "Price (EUR)"], rows)

    say("\nTable 16. Own profit of each incumbent over 10 years, % against all at list price (95% CI).")
    rows = []
    for o in OPS:
        cells = [o]
        for name in (f"solo_{o}_0.90", "fixed_0.90", f"solo_{o}_0.80"):
            m, lo, hi = paired(name, f"profit_{o}")
            cells.append(f"{sg(m)}% ({sg(lo)} to {sg(hi)})")
        rows.append(cells)
    table(["Incumbent", "Cuts alone to x0.90", "All cut to x0.90", "Cuts alone to x0.80"], rows)

    say("\nLearned prices (bandit, epsilon 0.1, alpha 0.2, decisions every 3 months)")
    late = logs[(logs.scenario == "bandit_e0.10_a0.2") & (logs.month > 72)]
    say("  List price chosen in years 6 to 10: " + ", ".join(
        f"{o} {(late[late.operator == o].new_arm == 1).mean() * 100:.0f}%" for o in OPS)
        + f"; {(late[~late.explored].new_arm == 1).mean() * 100:.0f}% of the decisions without exploration")
    rows = []
    for name in [n for n in sc if n.startswith("bandit")]:
        g = runs[runs.scenario == name]
        mult = np.mean([(g[f"price_{o}_mean"] / LIST_PRICE[o]).mean() for o in OPS])
        rows.append([name, sg(paired(name)[0]), rnd(mult, 2), rnd(g.share_DIGI_end.mean() * 100, 1)])
    table(["Bandit scenario", "Joint profit (%)", "Mean multiplier", "DIGI y10 (%)"], rows)


def sensitivity_simulations():
    say("\nSensitivity analysis of the new model (task 6)\n")
    sc = sensitivity_scenarios()
    seeds = list(SENSITIVITY_SEEDS)
    jobs = [(v, n, p, seed) for v in VARIANTS for n, p in sc.items() for seed in seeds]
    runs = pd.DataFrame(pool_map(run_sensitivity, jobs, "sensitivity"))
    say(f"Table 17. Sensitivity analysis ({len(seeds)} runs per scenario). Own profit of a solo cut to "
        "x0.90 and joint profit with learned prices, % against all at list price; DIGI share at "
        "month 28 (ANACOM 3.2%) and in year 10 with list prices.")
    rows = []
    for v in VARIANTS:
        g = runs[runs.variant == v]
        ref = g[g.scenario == "fixed_1.00"].set_index("seed")

        def paired(name, col):
            x = g[g.scenario == name].set_index("seed").loc[ref.index]
            return ci((x[col] - ref[col]) / ref[col] * 100)[0]

        rows.append([v] + [sg(paired(f"solo_{o}_0.90", f"profit_{o}")) for o in OPS]
                    + [sg(paired("bandit", "profit_incumbents")),
                       rnd(ref.share_DIGI_m28.mean() * 100, 1), rnd(ref.share_DIGI_end.mean() * 100, 1)])
    table(["Variant", "MEO solo", "NOS solo", "Vod. solo", "Learned", "DIGI m28", "DIGI y10"], rows)


# ============================================================================ the interface (SolaraViz)
COLORS = ["#2a78d6", "#eb6834", "#1a9e77", "#7a3fbf"]
NOWO_COLOR = "#9a9a9a"
POLICIES = ["List prices", "Learned (bandit)", "All at 0.90"]


class LiveTelecomModel(TelecomMarketModel):
    """Calibrated model with the price policy chosen in the interface."""

    def __init__(self, norm_influence=0.10, exploration=CALIBRATED["exploration"], entry_tick=12,
                 policy=POLICIES[0], seed=4000):
        params = dict(CALIBRATED, norm_influence=norm_influence, exploration=exploration)
        if abs(norm_influence - CALIBRATED["norm_influence"]) > 1e-9:
            params.pop("brand_constants")      # constants were calibrated for w = 0.10
        super().__init__(entry_tick=int(entry_tick), rng=int(seed), **params)
        self.policy_name = policy
        if policy == POLICIES[1]:
            self.price_policy = BanditPricePolicy(seed=int(seed))
        elif policy == POLICIES[2]:
            self.price_policy = FixedPricePolicy((0.9, 0.9, 0.9))


def build_page():
    """Mesa's browser interface: sliders and Reset / Play / Step on the left, network and plots."""
    import solara
    from matplotlib.collections import LineCollection
    from matplotlib.figure import Figure
    from mesa.visualization import SolaraViz

    def make_safe_plot_component(measures, post_process=None, xlabel="Step"):
        """Plot that copies the data first, so it is safe while the model is stepping."""
        if isinstance(measures, str):
            measures = {measures: "#1a1a1a"}

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
            elif len(measures) > 1:
                ax.legend(fontsize=7)
            return solara.FigureMatplotlib(fig, format="png", dpi=72)
        return SafePlot

    def NetworkView(model):
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
        ax.set_title(f"Month {model.steps} - prices: {model.policy_name} - population {len(consumers)}\n"
                     f"blue MEO, orange NOS, green Vodafone, "
                     f"{'purple' if model.digi_entered else 'grey'} {name3}", fontsize=8, loc="left")
        return solara.FigureMatplotlib(fig, format="png", dpi=72)

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
    d = {k: v.default for k, v in inspect.signature(TelecomMarketModel.__init__).parameters.items()
         if v.default is not inspect.Parameter.empty}
    d.update(CALIBRATED)
    bandit = {k: v.default for k, v in inspect.signature(BanditPricePolicy.__init__).parameters.items()
              if v.default is not inspect.Parameter.empty}

    def pct(x):
        return f"{x * 100:g}%"

    def FixedParameters(model):
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
            ("Households under contract at the start", pct(d["initial_contracted"])),
            ("Initial contracts that are renewals", pct(d["initial_renewed"])),
            ("Renewal discount", pct(d["renewal_discount"])),
            ("Cost of commitment (mean, spread)",
             f"€{d['commit_cost_mean']:.2f}/month, ±{pct(d['commit_cost_spread'])}"),
            ("Early exit", "penalty of Lei 16/2022" if d["exit_rule"] == "penalty" else d["exit_rule"]),
            ("DIGI price", f"€{d['digi_price']:.2f}/month"),
            ("DIGI quality", f"{d['digi_quality_start']:.3f} → {d['digi_quality_end']:.3f} "
                             f"in {d['digi_maturation']} months"),
            ("Exits / net growth of households",
             f"{pct(d['exit_rate'])} per month / {pct(d['net_growth_year'])} per year"),
            ("Margin of the incumbents", pct(d["margin"])),
            ("Bandit (learned prices)", f"ε = {bandit['epsilon']}, α = {bandit['alpha']}, decision every "
                                        f"{bandit['period']} months, arms × "
                                        + ", ".join(f"{a:.2f}" for a in bandit["arms"])),
        ]
        rows_md = "\n".join(f"| {k} | {v} |" for k, v in rows)
        return solara.Markdown(
            "**After changing a slider or the price policy, press Reset**: the change applies to a new run.\n\n"
            "**Fixed parameters of the report** (not changeable here; see Sect. 4 of the report)\n\n"
            "| Parameter | Value |\n|---|---|\n" + rows_md)

    model_params = {
        "norm_influence": {"type": "SliderFloat", "value": 0.10, "label": "Norm influence (w)",
                           "min": 0.0, "max": 0.5, "step": 0.01},
        "exploration": {"type": "SliderFloat", "value": CALIBRATED["exploration"], "label": "Exploration",
                        "min": 0.0, "max": 0.1, "step": 0.005},
        "entry_tick": {"type": "SliderInt", "value": 12, "label": "DIGI entry (month)",
                       "min": 0, "max": 36, "step": 1},
        "policy": {"type": "Select", "value": POLICIES[0], "values": POLICIES,
                   "label": "Incumbents' prices after entry"},
        "seed": {"type": "SliderInt", "value": 4000, "label": "Random seed (report runs: 4000 to 4029)",
                 "min": 4000, "max": 4029, "step": 1},
    }
    shares = make_safe_plot_component(
        {"share_MEO": COLORS[0], "share_NOS": COLORS[1], "share_Vodafone": COLORS[2],
         "share_DIGI": COLORS[3]}, post_process=anacom_points, xlabel="Month")
    prices = make_safe_plot_component(
        {"price_MEO": COLORS[0], "price_NOS": COLORS[1], "price_Vodafone": COLORS[2],
         "price_DIGI": COLORS[3]}, post_process=dash_nos, xlabel="Month")
    contracts = make_safe_plot_component("pct_contracted", post_process=label_contracts, xlabel="Month")
    return SolaraViz(
        LiveTelecomModel(),
        components=[(NetworkView, 0), shares, prices, contracts, (FixedParameters, 0)],
        model_params=model_params,
        name="Consumer Choice - DIGI entry",
        play_interval=100,
        render_interval=1,
    )


def open_interface():
    """Serves this file as a Solara page, opens it in the browser and waits for Enter."""
    import importlib.util
    import webbrowser
    print("\n=== New model: interface ===")
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
    print('Use Reset, Play / Pause and Step on the left; choose "Learned (bandit)" and press Reset '
          "to see the incumbents learn their prices.")
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
elif __name__ == "__main__":         # run by `python new_model_full.py`
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = sys.argv[1:]
    if "--no-interface" not in args:
        open_interface()
    if "--interface-only" not in args:
        print()
        start = time.time()
        for part in (price_simulations, sensitivity_simulations):
            t = time.time()
            part()
            say(f"  ({time.time() - t:.0f} s)")
        say(f"\nDone in {(time.time() - start) / 60:.1f} minutes.")
        with open(os.path.join(HERE, "new_model_full_output.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(OUT) + "\n")
        print("Saved to new_model_full_output.txt")
