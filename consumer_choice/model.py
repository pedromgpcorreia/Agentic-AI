"""Consumer Choice: agent-based model of habits and social influence.

Python/Mesa 3 implementation of the NetLogo Models Library model
"Consumer Choice" (Jager & Wang, 2024; basic model by M. A. Janssen).
The rules follow the NetLogo code line by line.
Product 0 is the orange product and product 1 is the blue product.

Original model: Copyright 2024 Uri Wilensky, CC BY-NC-SA 3.0.
"""
import math

import mesa

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
