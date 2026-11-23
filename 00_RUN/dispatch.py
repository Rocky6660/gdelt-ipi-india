"""Windows dispatcher: runs the commands in 00_RUN/next.json inside a venv, logging to logs/dispatch/.
Stdlib only. Double-click RUN.bat to execute. Never stores credentials in the project folder."""
import json, os, subprocess, sys, datetime as dt, venv
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent           # ...\GDELT_IPI
PIPE = ROOT / "09_ANALYSIS" / "pipeline"
LAD = Path(os.environ.get("LOCALAPPDATA", str(Path.home())))
VENV = LAD / "gdelt_ipi_venv"
LOGD = ROOT / "logs" / "dispatch"; LOGD.mkdir(parents=True, exist_ok=True)
task = json.loads((ROOT / "00_RUN" / "next.json").read_text(encoding="utf-8"))
if task.get("venv"): VENV = LAD / task["venv"]
BOOT = LAD / "gdelt_ipi_venv" / "Scripts" / "python.exe"
PY312 = LAD / "gdelt_ipi_py312" / "Scripts" / "python.exe"
tid = task.get("id", "task")
log = LOGD / f"{tid}.log"
status = LOGD / f"{tid}.status"
py = VENV / "Scripts" / "python.exe"
def w(msg):
    with open(log, "a", encoding="utf-8") as fh: fh.write(msg + "\n")
status.write_text("RUNNING", encoding="utf-8")
w(f"== {tid} start {dt.datetime.now().isoformat(timespec='seconds')}")
try:
    if not py.exists():
        w("creating venv " + str(VENV)); venv.create(VENV, with_pip=True)
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8", GDELT_IPI_ROOT=str(PIPE))
    rc_all = 0
    for cmd in task["commands"]:
        cmd = [str(py) if c == "PY" else str(BOOT) if c == "BOOT" else c.replace("{PY312}", str(PY312)).replace("{LAD}", str(LAD)).replace("{PIPE}", str(PIPE)).replace("{ROOT}", str(ROOT)) for c in cmd]
        w(f"$ {' '.join(cmd)}")
        with open(log, "a", encoding="utf-8") as fh:
            rc = subprocess.call(cmd, cwd=str(PIPE), stdout=fh, stderr=subprocess.STDOUT, env=env)
        w(f"-> exit {rc}")
        if rc != 0:
            rc_all = rc
            if task.get("stop_on_error", True): break
    status.write_text("DONE" if rc_all == 0 else f"FAILED {rc_all}", encoding="utf-8")
except Exception as e:
    w(f"DISPATCH ERROR {e!r}"); status.write_text("FAILED dispatch", encoding="utf-8")
w(f"== {tid} end {dt.datetime.now().isoformat(timespec='seconds')}")
