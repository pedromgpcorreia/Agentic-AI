"""Tests for the extended model (consumer_choice/telecom.py).

Run from the repository root:  python tests/test_telecom.py   (or: pytest tests/)
"""
import os
import sys
import warnings

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
warnings.filterwarnings("ignore")

from consumer_choice import ConsumerChoiceModel  # noqa: E402
from consumer_choice.telecom import Customer, TelecomMarketModel  # noqa: E402


def baseline_equivalent(seed, **kw):
    """The extended model with all extensions switched off."""
    return TelecomMarketModel(
        num_consumers=100, min_consumers=0, avg_connections=5,
        names=("orange", "blue"), initial_shares=(50, 50), prices=(0, 0),
        qualities=(0.5, 0.5), contract_months=(0, 0), price_weight=0.0,
        contracts=False, entry_tick=None, demography=False, rng=seed, **kw)


def test_regression_against_baseline():
    """Same seed, same parameters -> identical outputs for 1000 ticks."""
    cases = [dict(), dict(norm_influence=0.5), dict(exploration=0.1),
             dict(norm_influence=0.0, information_exchange=0.3)]
    for kw in cases:
        for seed in range(5):
            base = ConsumerChoiceModel(rng=seed, **kw)
            new = baseline_equivalent(seed, **kw)
            for t in range(1000):
                base.step()
                new.step()
            b = base.datacollector.get_model_vars_dataframe()
            n = new.datacollector.get_model_vars_dataframe()
            assert (b["orange"].values == (n["share_orange"].values * 100).round()).all(), (kw, seed)
            assert (abs(b["clustering"].values - n["clustering"].values) < 1e-12).all(), (kw, seed)


def test_penalty_examples():
    """Worked examples of the specification (prices of the spec, Lei 16/2022)."""
    m = TelecomMarketModel(num_consumers=50, min_consumers=0, demography=False, rng=1)
    c = m.consumers[0]
    c.choice, c.contract_price = 0, 42.49
    m.price[3] = 22.00
    # year 1: 18 months left -> savings 18*20.49 = 368.8 < penalty 0.5*18*42.49 = 382.4
    c.contract_left, c.contract_elapsed = 18, 6
    assert not c.can_leave(3)
    # year 2: 6 months left -> savings 6*20.49 = 122.9 > penalty 0.3*6*42.49 = 76.5
    c.contract_left, c.contract_elapsed = 6, 18
    assert c.can_leave(3)
    # never leave early to a more expensive operator
    assert not c.can_leave(1) or m.price[1] < c.contract_price
    # lock-in rule
    m.exit_rule = "lock"
    assert not c.can_leave(3)
    # no contract -> free
    c.contract_left = 0
    assert c.can_leave(3)


def test_invariants_full_model():
    """Population >= minimum, shares sum to 1, contracts never negative, DIGI enters."""
    m = TelecomMarketModel(rng=3)
    for t in range(48):
        m.step()
        assert len(m.consumers) >= m.min_consumers
        assert abs(sum(m.share(k) for k in range(m.n_ops)) - 1) < 1e-9
        assert all(c.contract_left >= 0 for c in m.consumers)
        assert all(len(c.friends) >= 0 and c not in c.friends for c in m.consumers)
        assert all(c in f.friends for c in m.consumers for f in c.friends)   # symmetric links
        assert len(m.agents) == len(m.consumers)
    assert m.digi_entered and m.names[3] == "DIGI"
    assert abs(m.quality[3] - m.digi_quality_end) < 1e-9          # 36 months after entry
    df = m.datacollector.get_model_vars_dataframe()
    assert df.population.iloc[-1] >= df.population.iloc[0]          # net growth


def test_initial_shares():
    """Initial shares follow the data within sampling error (n = 5000)."""
    m = TelecomMarketModel(num_consumers=5000, min_consumers=0, avg_connections=2,
                           demography=False, rng=7)
    for k, target in enumerate((41.8, 35.0, 20.6, 2.6)):
        assert abs(m.share(k) * 100 - target) < 2.0, (k, m.share(k))


def test_renewal_rule():
    m = TelecomMarketModel(num_consumers=50, min_consumers=0, demography=False, rng=2)
    c = m.consumers[0]
    c.choice = 0
    c.commit_cost = 3.0                       # discount 0.10 * 42.49 = 4.25 >= 3.0 -> accepts
    c.offer_renewal()
    assert c.contract_left == 24 and abs(c.contract_price - 0.9 * 42.49) < 1e-9
    c.commit_cost, c.contract_left = 6.0, 0   # 4.25 < 6.0 -> stays without contract
    c.offer_renewal()
    assert c.contract_left == 0 and c.contract_price == 42.49


def test_price_policies():
    """Fixed policy applies once at entry; bandit decides every 3 months with valid arms."""
    from consumer_choice.calibrated import CALIBRATED
    from consumer_choice.learning import ARMS, BanditPricePolicy, FixedPricePolicy
    m = TelecomMarketModel(rng=5, **CALIBRATED)
    m.price_policy = FixedPricePolicy((0.9, 1.0, 0.8))
    for _ in range(14):
        m.step()
    assert abs(m.price[0] - 0.9 * 42.49) < 1e-9 and m.price[1] == 42.49
    assert abs(m.price[2] - 0.8 * 40.50) < 1e-9 and m.price[3] == 22.00
    m = TelecomMarketModel(rng=5, **CALIBRATED)
    pol = BanditPricePolicy()
    m.price_policy = pol
    for _ in range(36):
        m.step()
    months = sorted({r["month"] for r in pol.log})
    assert months == [14, 17, 20, 23, 26, 29, 32, 35], months   # entry month 12 = first month of quarter 1
    assert all(r["new_arm"] in ARMS for r in pol.log)
    for k in range(3):
        assert any(abs(m.price[k] - m.base_price[k] * a) < 1e-9 for a in ARMS)
    # contracted households keep the price they signed
    assert all(c.contract_price > 0 for c in m.consumers)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok ", name)
    print("all tests passed")
