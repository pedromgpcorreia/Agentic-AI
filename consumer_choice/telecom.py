"""Consumer Choice extended to the Portuguese bundled-services market (model v2).

Extension of the baseline model (model.py) following docs/model_v2_spec.md:
  * N operators (MEO, NOS, Vodafone and NOWO, which becomes DIGI at the entry tick);
  * price in the product utility, with a weight tied to the norm (Confraria et al., 2017);
  * loyalty contracts with early-exit penalties (Lei 16/2022) or full lock-in;
  * renewal at the end of the contract decided by the consumer;
  * DIGI quality that improves with time since entry;
  * consumers that leave and enter the market (variable population, minimum size).

The decision structure of the baseline is kept: habit -> exploration -> utility.
With 2 operators and all extensions switched off, the model reproduces the baseline
exactly (same random draws, same outputs); see tests/test_telecom.py.

1 tick = 1 month.
"""
import math

import mesa

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
    """Market of bundled services with the entry of DIGI (model v2)."""

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
