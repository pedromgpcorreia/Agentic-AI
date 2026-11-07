"""Opens a Mesa (SolaraViz) page in the browser and waits until the user closes it.

Used by original_model.py and new_model.py. The page runs in a separate process
(`solara run <page>`); pressing Enter in the terminal stops it.
"""
import importlib.util
import os
import shutil
import socket
import subprocess
import sys
import time
import webbrowser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSTALL = f'"{sys.executable}" -m pip install -r requirements.txt'


def _port_open(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def _free_port(start=8765):
    port = start
    while _port_open(port):
        port += 1
    return port


def open_interface(page, title):
    """Starts the page, opens it in the browser and waits for Enter. Returns True if it ran."""
    print(f"\n=== {title} ===")
    if importlib.util.find_spec("solara") is None or importlib.util.find_spec("mesa.visualization") is None:
        print("The interface needs the visualization packages of Mesa, which are not installed.")
        print(f"Install them with:\n    {INSTALL}\nand run this file again. Continuing without it.")
        return False
    port = _free_port()
    exe = shutil.which("solara")
    cmd = [exe] if exe else [sys.executable, "-m", "solara"]
    cmd += ["run", os.path.join(ROOT, page), "--port", str(port)]
    env = dict(os.environ, PYTHONPATH=ROOT + os.pathsep + os.environ.get("PYTHONPATH", ""))
    proc = subprocess.Popen(cmd, cwd=ROOT, env=env)
    url = f"http://localhost:{port}"
    for _ in range(240):                                  # up to 2 minutes for the first start
        if proc.poll() is not None or _port_open(port):
            break
        time.sleep(0.5)
    if proc.poll() is not None:
        print(f"The interface did not start (solara exit code {proc.returncode}). Continuing without it.")
        return False
    time.sleep(1.5)
    webbrowser.open(url)
    print(f"The interface is open in the browser: {url}")
    print("Use Reset, Play / Pause and Step on the left; change the sliders and press Reset.")
    try:
        input("\nPress Enter here to close the interface and continue... ")
    except (EOFError, KeyboardInterrupt):
        pass
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
    return True
