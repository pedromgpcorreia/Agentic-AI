"""NEW MODEL: DIGI's entry into the Portuguese market of bundled services, with learning
incumbents, implemented in Python with Mesa (tasks 3 to 6).

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

Files
    The model is consumer_choice/telecom.py, with learning.py (price policies, the bandit)
    and calibrated.py (calibrated values); the interface is visualization/app.py; the
    simulations are parts 2 and 3 of main.py (the single file that runs the whole report).
    Results are printed and saved to new_model_output.txt, next to this file.

Requirements
    Python 3.12 or later (required by Mesa 3.5). Install once, from this folder:
        python -m pip install -r requirements.txt

How to run
    VS Code: open this folder (File > Open Folder), select the Python interpreter where the
    requirements are installed, open new_model.py and press Run.
    Terminal, from this folder:
        python new_model.py                    # interface, then the simulations
        python new_model.py --interface-only   # only the interface
        python new_model.py --no-interface     # only the simulations

Time
    The simulations use all CPU cores: about 13 minutes on 8 cores.
"""
import os
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

import main  # noqa: E402  (the report's simulations: same code, parameters and seeds)
from visualization.launch import open_interface  # noqa: E402

if __name__ == "__main__":
    args = sys.argv[1:]
    if "--no-interface" not in args:
        open_interface("visualization/app.py", "New model: interface")
    if "--interface-only" in args:
        sys.exit(0)
    print("\n=== New model: simulations of the report (tasks 3 to 6) ===\n")
    start = time.time()
    for part in (main.part2, main.part3):
        t = time.time()
        part()
        main.say(f"  ({time.time() - t:.0f} s)")
    main.say(f"\nDone in {(time.time() - start) / 60:.1f} minutes.")
    with open(os.path.join(ROOT, "new_model_output.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(main.OUT) + "\n")
    print("Saved to new_model_output.txt")
