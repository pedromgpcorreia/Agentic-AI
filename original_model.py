"""ORIGINAL MODEL: Consumer Choice (Jager & Wang), implemented in Python with Mesa (tasks 1 and 2).

What it does
    1. Opens the model's interface in the browser (Mesa SolaraViz, the equivalent of the
       NetLogo interface): the consumers in their friendship network, coloured by product,
       and the plots of the outputs, with Reset / Play / Step buttons and sliders. The
       defaults are the baseline of the report.
    2. When you press Enter in the terminal, closes the interface and runs every simulation
       of the report for this model, with the same parameters and random seeds, so the
       printed numbers are those of the report: the baseline (1000 runs x 2000 ticks,
       Tables 7 and 8) and the sensitivity analysis of norm_influence, quality_blue and
       exploration (100 runs per value x 1000 ticks, Tables 9 to 11).

Files
    The model is consumer_choice/model.py; the interface is visualization/baseline_app.py;
    the simulations are part 1 of main.py (the single file that runs the whole report).
    Results are printed and saved to original_model_output.txt, next to this file.

Requirements
    Python 3.12 or later (required by Mesa 3.5). Install once, from this folder:
        python -m pip install -r requirements.txt

How to run
    VS Code: open this folder (File > Open Folder), select the Python interpreter where the
    requirements are installed, open original_model.py and press Run.
    Terminal, from this folder:
        python original_model.py                    # interface, then the simulations
        python original_model.py --interface-only   # only the interface
        python original_model.py --no-interface     # only the simulations

Time
    The simulations use all CPU cores: about 7 minutes on 8 cores.
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
        open_interface("visualization/baseline_app.py", "Original model: interface")
    if "--interface-only" in args:
        sys.exit(0)
    print("\n=== Original model: simulations of the report (tasks 1 and 2) ===\n")
    start = time.time()
    main.part1()
    main.say(f"\nDone in {(time.time() - start) / 60:.1f} minutes.")
    with open(os.path.join(ROOT, "original_model_output.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(main.OUT) + "\n")
    print("Saved to original_model_output.txt")
