"""
launcher.py — Multi-Agent Studio orchestrator

Runs research_bot on a configurable loop.
No LinkedIn bots — discovery is fully web-driven via research_bot.

Cycle:
  1. Clear the status file
  2. Run research_bot (scrapes web + auto-discovers URLs + calls Groq)
  3. Wait for it to finish (or kill after timeout)
  4. Sleep, then repeat

Directory layout:
  research_bot.py   ← in the same folder as this file
  Data/
  Maintenance/
"""

import subprocess
import time
import os

# ============================= CONFIG =============================== #
# Get parent directory (project root)
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
RESEARCH_BOT = os.path.join(PROJECT_ROOT, "core", "research_bot.py")

# Auto-detect Python: use venv if present, else fall back to system python
_venv_win = os.path.join(PROJECT_ROOT, "venv", "Scripts", "python.exe")
_venv_unix = os.path.join(PROJECT_ROOT, "venv", "bin", "python")
if os.path.exists(_venv_win):
    PYTHON_EXEC = _venv_win
elif os.path.exists(_venv_unix):
    PYTHON_EXEC = _venv_unix
else:
    PYTHON_EXEC = "python"

STATUS_FILE = os.path.join(PROJECT_ROOT, "Maintenance", "status_file.lock")

# How long (seconds) to wait for research_bot to finish before killing it
RESEARCH_TIMEOUT = 900   # 15 minutes

# How long to wait between cycles
CYCLE_INTERVAL = 1200    # 20 minutes
# ==================================================================== #

os.makedirs(os.path.join(PROJECT_ROOT, "Maintenance"), exist_ok=True)
os.makedirs(os.path.join(PROJECT_ROOT, "Data"), exist_ok=True)


def reset_status_file():
    if os.path.exists(STATUS_FILE):
        os.remove(STATUS_FILE)
    print("[launcher] Status file cleared.")


def run_research_bot() -> subprocess.Popen:
    print(f"[launcher] Starting: {RESEARCH_BOT}")
    return subprocess.Popen([PYTHON_EXEC, RESEARCH_BOT], cwd=PROJECT_ROOT)


if __name__ == "__main__":
    cycle = 0

    print(f"\n{'='*55}")
    print(f"  MULTI-AGENT STUDIO — LAUNCHER")
    print(f"  Python  : {PYTHON_EXEC}")
    print(f"  Bot     : {RESEARCH_BOT}")
    print(f"  Timeout : {RESEARCH_TIMEOUT}s per cycle")
    print(f"  Interval: {CYCLE_INTERVAL}s between cycles")
    print(f"{'='*55}\n")

    while True:
        cycle += 1
        print(f"\n{'='*55}")
        print(f"  CYCLE {cycle} — {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*55}\n")

        reset_status_file()

        p = run_research_bot()

        try:
            p.wait(timeout=RESEARCH_TIMEOUT)
            print("[launcher] research_bot finished cleanly.")
        except subprocess.TimeoutExpired:
            print(f"[launcher] research_bot exceeded {RESEARCH_TIMEOUT}s — terminating.")
            p.terminate()
            p.wait()

        print(f"[launcher] Cycle {cycle} done. "
              f"Next cycle in {CYCLE_INTERVAL}s "
              f"({time.strftime('%H:%M:%S', time.localtime(time.time() + CYCLE_INTERVAL))})...\n")
        time.sleep(CYCLE_INTERVAL)