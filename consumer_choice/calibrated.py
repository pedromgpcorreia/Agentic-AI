"""Calibrated parameter set of the telecom model (docs/model_v2_spec.md, section 11).

Version of 29/10 (19:22): renewal discount back to 10 % (decision of Pedro). The 70 % of
households under contract is only the starting point; the contracted share then evolves
with the consumers' decisions (it settles near 40 % without the DIGI entry).

* renewal_discount 0.10: proposal of the group.
* initial_renewed 0.48: share of renewals among the contracts signed in months 24-72
  without the entry (fixed point). Removes the drift of the average price paid caused by
  pricing every initial contract at the list price.
* norm_influence 0.10, exploration 0.02: grid w in {0.08, 0.10, 0.12} x e in
  {0.005, 0.01, 0.02, 0.03} (calibration/calibrate_entry.py delta10). RMSE 0.15 pp against
  the ANACOM DIGI shares 2.8 / 3.0 / 3.2 % at months 19 / 25 / 28. The point (0.12, 0.005)
  gives 0.12 pp; (0.10, 0.02) is retained because it keeps w and gives a turnover closer
  to the data (2.7 %/year against 2.1 %/year).
* brand_constants: re-calibrated for this set so that the market without the DIGI entry
  keeps the ANACOM Q3 2024 shares (months 12-24).

Previous version (renewal discount 0.178, exploration 0.03, initial_renewed 0.78) is in
the git history (commit e395505) and in results/v2/calibration_long.json.
"""
CALIBRATED = dict(
    norm_influence=0.10,
    exploration=0.02,
    renewal_discount=0.10,
    initial_renewed=0.48,
    brand_constants=[0.0, 0.0307, 0.0161, -0.0820],
)
