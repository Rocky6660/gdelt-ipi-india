"""Run a Q2 stage end to end through bq_runner (all safety gates stay inside bq_runner).

  python scripts/run_stage.py --stage A --apply-ladder   # set rung from plan/ladder.json, plan, run FIRST group only
  python scripts/run_stage.py --stage A --rest            # after `mark-checked`: run every remaining chunk

Chunks already RUN_OK are skipped. A refused or failed chunk stops the loop (nothing is retried silently).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bq_runner as R  # noqa: E402


def sh(*args: str) -> int:
    print("$ bq_runner", " ".join(args), flush=True)
    return subprocess.call([sys.executable, str(HERE / "bq_runner.py"), *args])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["A", "B"], required=True)
    ap.add_argument("--apply-ladder", action="store_true")
    ap.add_argument("--rest", action="store_true")
    a = ap.parse_args()
    cfg_path = HERE / "config.yaml"
    cfg = R.load_config(cfg_path)
    if a.apply_ladder:
        lad = json.loads((R.rpath(cfg, "plan_dir") / "ladder.json").read_text())
        rec = lad.get("recommended")
        if not rec:
            sys.exit("ladder recommends no rung: escalate to the user (Gate 0b)")
        s = cfg_path.read_text()
        s = re.sub(r"(?m)^rung: .*$", f"rung: {rec}                      # Gate 0b: ladder.json recommendation", s, count=1)
        with open(cfg_path, "r+") as fh:
            fh.seek(0); fh.write(s); fh.truncate()
        print(f"rung set to {rec}")
        cfg = R.load_config(cfg_path)
    rung = cfg["rung"]
    pp = R.plan_path(cfg, rung, a.stage)
    if not pp.exists():
        if sh("plan", "--rung", rung, "--stage", a.stage) != 0:
            sys.exit("plan failed")
    plan = json.loads(pp.read_text())
    ok = R.Ledger(R.rpath(cfg, "ledger")).ok_labels()
    todo = [c for c in plan["chunks"] if c["label"] not in ok and (a.rest or c["group"] == plan["first_group"])]
    print(f"rung {rung} stage {a.stage}: {len(plan['chunks'])} chunks, {len(todo)} to run now")
    for c in todo:
        if sh("run-chunk", "--rung", rung, "--stage", a.stage, "--label", c["label"]) != 0:
            sys.exit(f"stopped at {c['label']}")
    print("stage step complete")


if __name__ == "__main__":
    main()
