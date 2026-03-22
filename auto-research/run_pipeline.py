#!/usr/bin/env python3
"""
run_pipeline.py — LoopLab Auto-Research Pipeline Runner
Orchestrates all 5 steps: Harvest → Evaluate → Generate → Deploy → Log
"""

import sys
import traceback
from datetime import datetime

STEPS = [
    ("harvest", "harvest.py", "Scraping landing page"),
    ("evaluate", "evaluate.py", "Analyzing conversion funnel"),
    ("generate", "generate.py", "Generating challenger variants via Claude API"),
    ("deploy", "deploy.py", "Preparing deployment artifacts"),
    ("log", "log.py", "Pulling GA4 data and generating report"),
]


def run_step(module_name: str, description: str) -> bool:
    print(f"\n{'='*60}")
    print(f"[pipeline] STEP: {description}")
    print(f"{'='*60}")
    try:
        import importlib
        mod = importlib.import_module(module_name)
        mod.main()
        print(f"[pipeline] ✓ {module_name} completed")
        return True
    except Exception as e:
        print(f"[pipeline] ✗ {module_name} FAILED: {e}")
        traceback.print_exc()
        return False


def main():
    start = datetime.utcnow()
    print(f"LoopLab Auto-Research Pipeline")
    print(f"Started: {start.isoformat()}Z")
    print(f"Steps: {' → '.join(s[0] for s in STEPS)}")

    # Parse step flags
    steps_to_run = sys.argv[1:] if len(sys.argv) > 1 else [s[0] for s in STEPS]

    results = {}
    for step_name, module, description in STEPS:
        if step_name not in steps_to_run:
            print(f"[pipeline] Skipping {step_name}")
            continue
        results[step_name] = run_step(step_name, description)

    elapsed = (datetime.utcnow() - start).total_seconds()
    passed = sum(1 for v in results.values() if v)
    failed = sum(1 for v in results.values() if not v)

    print(f"\n{'='*60}")
    print(f"[pipeline] DONE — {passed} passed, {failed} failed ({elapsed:.1f}s)")
    for step, ok in results.items():
        print(f"  {'✓' if ok else '✗'} {step}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
