"""Price policies for the incumbents (tasks 3 and 5).

* FixedPricePolicy: after the DIGI entry each incumbent sets a constant price
  (scenarios used as the no-learning reference).
* BanditPricePolicy: each incumbent learns its price with an epsilon-greedy
  multi-armed bandit with a constant step size (Sutton & Barto, 2018, ch. 2),
  which suits a non-stationary environment.

Both are attached to a TelecomMarketModel through `model.price_policy`, which the
model calls at the end of every month.

Price changes apply to new contracts, renewals and households without a contract;
households under contract keep the price they signed.
"""

# price multipliers of the base price (agreed plan): 1.00 = list price before the entry,
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
    """Epsilon-greedy bandit per incumbent, deciding every `period` months.

    Reward of a period = profit of the operator summed over the months of the period:
    sum over its customers of (price paid - unit cost). Unit cost = (1 - margin) x base price.
    """

    def __init__(self, epsilon=0.1, alpha=0.2, period=3, arms=ARMS,
                 learn_before_entry=False):
        self.epsilon = epsilon
        self.alpha = alpha
        self.period = period
        self.arms = list(arms)
        self.learn_before_entry = learn_before_entry
        self.q = {k: None for k in INCUMBENTS}          # action values, set on first decision
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
            if self.q[k] is None:
                # initial values on the scale of the rewards: the profit observed
                # with the base price (optimistic for lower prices)
                self.q[k] = [reward] * len(self.arms)
            a = self.action[k]
            self.q[k][a] += self.alpha * (reward - self.q[k][a])
            if model.random.random() < self.epsilon:
                new_a = model.random.randrange(len(self.arms))
                explored = True
            else:
                best = max(self.q[k])
                new_a = min(i for i, v in enumerate(self.q[k]) if v == best)
                explored = False
            self.log.append({"month": model.steps, "operator": model.names[k],
                             "reward": reward, "previous_arm": self.arms[a],
                             "new_arm": self.arms[new_a], "explored": explored,
                             "price": model.base_price[k] * self.arms[new_a],
                             **{f"Q_{m:.2f}": v for m, v in zip(self.arms, self.q[k])}})
            self.action[k] = new_a
            model.price[k] = model.base_price[k] * self.arms[new_a]
            self.acc[k] = 0.0
        self.months = 0
