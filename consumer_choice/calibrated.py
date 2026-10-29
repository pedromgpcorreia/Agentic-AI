"""Calibrated parameter set of the telecom model (docs/model_v2_spec.md, section 11).

* renewal_discount 0.178: steady-state share of households under contract = 0.70
  (calibration/calibrate_pre_entry.py).
* norm_influence 0.10: best value of the post-entry grid (calibration/calibrate_entry.py
  fine; with exploration 0.02, RMSE 0.11 pp against ANACOM DIGI shares 2.8 / 3.0 / 3.2 %
  at months 19 / 25 / 28).
* brand_constants: re-calibrated for (0.10, 0.02) so that the market without the
  DIGI entry keeps the ANACOM Q3 2024 shares.
* initial_renewed 0.78: share of renewals among the contracts signed in the long run
  (fixed point, calibration/calibrate_long.py). Without it all initial contracts are at
  the list price and the average price paid falls from EUR 41.6 to 37.4 in 36 months,
  a trend that would bias the profit signal of the learning operators.
* exploration 0.03: with initial_renewed 0.78, exploration 0.02 gives RMSE 0.36 pp;
  0.025 gives 0.23 pp; 0.03 gives 0.18 pp (48 seeds). 0.03 is retained.
"""
CALIBRATED = dict(
    norm_influence=0.10,
    exploration=0.03,
    renewal_discount=0.178,
    initial_renewed=0.78,
    brand_constants=[0.0, 0.0280, 0.0168, -0.0837],
)
