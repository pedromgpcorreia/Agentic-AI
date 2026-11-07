# Consumer Choice — DIGI's entry into the Portuguese bundle market (Project 1, Agentic AI)

André Pires, José Pinho, Manuel Sampaio and Pedro Correia — Faculty of Economics, University of Porto.

| File | Content |
|---|---|
| `Report_Consumer_Choice.docx` | Project report (LNCS format), tasks 1 to 6 |
| `original_model_full.py` | Original Consumer Choice model (tasks 1 and 2): model, interface and the simulations behind Tables 7 to 11 |
| `new_model_full.py` | New model, DIGI's entry with learning incumbents (tasks 3 to 6): model, interface and the simulations behind the calibration and Tables 15 to 17 |
| `requirements.txt` | Python packages needed by both files |

Each `.py` file is self-contained: it runs on its own, without any other file.

## How to run

Python 3.12 or later (required by Mesa 3.5). Install the packages once:

```bash
python -m pip install -r requirements.txt
```

Then run either model:

```bash
python original_model_full.py      # about 6 minutes on 8 cores
python new_model_full.py           # about 11 minutes on 8 cores
```

Each file first opens the model's interface in the browser (Mesa SolaraViz, the equivalent of
the NetLogo interface: the agents in their network, the plots, Reset / Play / Step and sliders).
Press Enter in the terminal to close it; the simulations of the report then run with the same
parameters and random seeds as the report, so the printed numbers are those of the report.
They are also saved to `original_model_full_output.txt` and `new_model_full_output.txt`.

Options: `--interface-only` (only the interface) and `--no-interface` (only the simulations).
In VS Code: select the Python interpreter where the packages are installed, open either file
and press Run.
