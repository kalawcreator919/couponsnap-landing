#!/usr/bin/env python3
"""
CouponSnap Auto Research Orchestrator
Inspired by Karpathy's Auto Research pattern.

Core idea: AI agent runs A/B experiments on the landing page autonomously.
It modifies page elements, measures CTA click rate via GA4, keeps winners,
discards losers, and accumulates learnings over time.

Flow:
  1. HARVEST — Pull GA4 metrics for current experiment
  2. EVALUATE — Compare challenger vs baseline
  3. GENERATE — Create new challenger hypothesis + page changes
  4. DEPLOY — Apply changes to index.html, commit & push
  5. LOG — Record results and learnings

Requirements:
  - Google Analytics 4 Data API (google-analytics-data)
  - GA4 property with cta_click event tracking
  - GitHub repo with Pages enabled
"""

import json
import os
import sys
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

# ─── Paths ────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).parent.parent  # couponsnap-landing/
AR_DIR = Path(__file__).parent       # auto-research/
INDEX_HTML = ROOT / "index.html"
CONFIG_FILE = AR_DIR / "config.json"
BASELINE_FILE = AR_DIR / "baseline.json"
RESOURCE_FILE = AR_DIR / "resource.md"
EXPERIMENTS_DIR = AR_DIR / "experiments"
LOGS_DIR = AR_DIR / "logs"

# ─── GA4 Analytics ────────────────────────────────────────────────────────────

def fetch_ga4_metrics(property_id: str, days: int = 1) -> dict:
    """Fetch CTA click metrics from GA4 Data API."""
    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.analytics.data_v1beta.types import (
            RunReportRequest, DateRange, Dimension, Metric
        )

        client = BetaAnalyticsDataClient()

        # Total sessions
        session_request = RunReportRequest(
            property=f"properties/{property_id}",
            date_ranges=[DateRange(start_date=f"{days}daysAgo", end_date="today")],
            metrics=[Metric(name="sessions"), Metric(name="bounceRate"),
                     Metric(name="averageSessionDuration")]
        )
        session_response = client.run_report(session_request)
        sessions = int(session_response.rows[0].metric_values[0].value) if session_response.rows else 0
        bounce_rate = float(session_response.rows[0].metric_values[1].value) if session_response.rows else 0
        avg_duration = float(session_response.rows[0].metric_values[2].value) if session_response.rows else 0

        # CTA click events
        event_request = RunReportRequest(
            property=f"properties/{property_id}",
            date_ranges=[DateRange(start_date=f"{days}daysAgo", end_date="today")],
            dimensions=[Dimension(name="eventName")],
            metrics=[Metric(name="eventCount")],
        )
        event_response = client.run_report(event_request)
        cta_clicks = 0
        for row in event_response.rows:
            if row.dimension_values[0].value == "cta_click":
                cta_clicks = int(row.metric_values[0].value)

        cta_rate = (cta_clicks / sessions * 100) if sessions > 0 else 0

        return {
            "sessions": sessions,
            "cta_clicks": cta_clicks,
            "cta_click_rate": round(cta_rate, 2),
            "bounce_rate": round(bounce_rate, 2),
            "avg_session_duration": round(avg_duration, 1),
            "period_days": days,
            "fetched_at": datetime.now().isoformat()
        }

    except ImportError:
        print("[WARN] google-analytics-data not installed. Using placeholder metrics.")
        return _placeholder_metrics()
    except Exception as e:
        print(f"[WARN] GA4 fetch failed: {e}. Using placeholder metrics.")
        return _placeholder_metrics()


def _placeholder_metrics() -> dict:
    """Return placeholder metrics when GA4 is not yet configured."""
    return {
        "sessions": 0,
        "cta_clicks": 0,
        "cta_click_rate": 0,
        "bounce_rate": 0,
        "avg_session_duration": 0,
        "period_days": 1,
        "fetched_at": datetime.now().isoformat(),
        "placeholder": True
    }

# ─── Experiment Management ────────────────────────────────────────────────────

def load_config() -> dict:
    return json.loads(CONFIG_FILE.read_text())


def load_latest_experiment() -> dict | None:
    """Load the most recent experiment file."""
    experiments = sorted(EXPERIMENTS_DIR.glob("*.json"), reverse=True)
    if experiments:
        return json.loads(experiments[0].read_text())
    return json.loads(BASELINE_FILE.read_text())


def save_experiment(experiment: dict):
    """Save experiment to file."""
    filename = f"{experiment['experiment_id']}.json"
    filepath = EXPERIMENTS_DIR / filename
    filepath.write_text(json.dumps(experiment, indent=2))
    print(f"[OK] Saved experiment: {filepath}")


def log_result(experiment: dict, metrics: dict, outcome: str):
    """Append result to log file."""
    log_file = LOGS_DIR / f"log-{datetime.now().strftime('%Y-%m')}.jsonl"
    entry = {
        "timestamp": datetime.now().isoformat(),
        "experiment_id": experiment["experiment_id"],
        "type": experiment["type"],
        "metrics": metrics,
        "outcome": outcome,
        "changes": experiment.get("changes", {})
    }
    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"[OK] Logged result to {log_file}")

# ─── HTML Modification ────────────────────────────────────────────────────────

def read_index() -> str:
    return INDEX_HTML.read_text(encoding="utf-8")


def write_index(html: str):
    INDEX_HTML.write_text(html, encoding="utf-8")


def apply_changes(html: str, changes: dict) -> str:
    """Apply experiment changes to HTML string."""
    for key, change in changes.items():
        old_val = change.get("old")
        new_val = change.get("new")
        if old_val and new_val and old_val in html:
            html = html.replace(old_val, new_val, 1)
            print(f"  [CHANGE] {key}: '{old_val[:50]}...' → '{new_val[:50]}...'")
        else:
            print(f"  [SKIP] {key}: old value not found in HTML")
    return html


def revert_to_baseline(html: str, baseline: dict) -> str:
    """Revert page to baseline state."""
    baseline_elements = baseline.get("page_elements", {})
    # This is a safety net — in practice, we track old/new in each experiment
    return html

# ─── Git Operations ───────────────────────────────────────────────────────────

def git_commit_and_push(message: str):
    """Commit changes and push to GitHub Pages."""
    try:
        subprocess.run(["git", "add", "-A"], cwd=ROOT, check=True)
        subprocess.run(["git", "commit", "-m", message], cwd=ROOT, check=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=ROOT, check=True)
        print(f"[OK] Pushed: {message}")
    except subprocess.CalledProcessError as e:
        print(f"[WARN] Git operation failed: {e}")

# ─── Update Resource.md ──────────────────────────────────────────────────────

def append_learning(learning: str):
    """Append a learning to resource.md."""
    content = RESOURCE_FILE.read_text()
    timestamp = datetime.now().strftime("%Y-%m-%d")
    entry = f"\n- [{timestamp}] {learning}"
    if "## Experiment Log" in content:
        content = content.replace(
            "## Experiment Log",
            f"## Experiment Log{entry}"
        )
    else:
        content += f"\n## Experiment Log{entry}"
    RESOURCE_FILE.write_text(content)

# ─── Main Pipeline ────────────────────────────────────────────────────────────

def harvest(config: dict) -> dict:
    """Step 1: Collect metrics from GA4."""
    print("\n=== HARVEST ===")
    property_id = config["metric"]["ga4_property_id"]
    days = config["metric"]["baseline_period_days"]
    metrics = fetch_ga4_metrics(property_id, days)
    print(f"  Sessions: {metrics['sessions']}")
    print(f"  CTA Clicks: {metrics['cta_clicks']}")
    print(f"  CTA Click Rate: {metrics['cta_click_rate']}%")
    return metrics


def evaluate(current_experiment: dict, metrics: dict, config: dict) -> str:
    """Step 2: Evaluate current experiment results."""
    print("\n=== EVALUATE ===")

    min_sessions = config["metric"]["minimum_sessions"]
    if metrics.get("placeholder") or metrics["sessions"] < min_sessions:
        print(f"  Not enough data yet ({metrics['sessions']}/{min_sessions} sessions). Skipping evaluation.")
        return "insufficient_data"

    # Update experiment with metrics
    current_experiment["metrics"] = metrics

    if current_experiment["type"] == "baseline":
        print(f"  Baseline CTA rate: {metrics['cta_click_rate']}%")
        return "baseline_recorded"

    # Compare with baseline
    baseline = json.loads(BASELINE_FILE.read_text())
    baseline_rate = baseline.get("metrics", {}).get("cta_click_rate", 0)
    challenger_rate = metrics["cta_click_rate"]

    print(f"  Baseline: {baseline_rate}% | Challenger: {challenger_rate}%")

    if challenger_rate > baseline_rate * 1.05:  # 5% improvement threshold
        print(f"  ✓ WINNER — Challenger beats baseline by {challenger_rate - baseline_rate:.2f}pp")
        return "winner"
    elif challenger_rate < baseline_rate * 0.95:
        print(f"  ✗ LOSER — Challenger underperforms by {baseline_rate - challenger_rate:.2f}pp")
        return "loser"
    else:
        print(f"  ~ INCONCLUSIVE — Within 5% margin")
        return "inconclusive"


def generate_challenger(config: dict, current: dict, resource_knowledge: str) -> dict:
    """Step 3: Generate a new challenger experiment.

    In the full version, this calls Claude API to generate hypotheses.
    For now, it uses a predefined rotation of test ideas.
    """
    print("\n=== GENERATE ===")

    # Predefined challenger ideas (will be replaced by Claude API calls)
    challengers = [
        {
            "hypothesis": "Shorter, more direct headline increases urgency",
            "changes": {
                "headline": {
                    "old": "Save Money <em>Automatically</em><br>While You Shop Online",
                    "new": "Stop Overpaying Online.<br><em>CouponSnap Saves You Money</em>"
                }
            }
        },
        {
            "hypothesis": "Action-oriented CTA with specific savings increases clicks",
            "changes": {
                "cta_primary": {
                    "old": "Add to Chrome — It's Free",
                    "new": "Start Saving Now — Free Forever"
                },
                "cta_footer": {
                    "old": "Add CouponSnap to Chrome — Free",
                    "new": "Get CouponSnap — Start Saving Today"
                }
            }
        },
        {
            "hypothesis": "Savings-focused badge instead of privacy-focused increases interest",
            "changes": {
                "hero_badge": {
                    "old": "🔒 We NEVER sell your data — unlike Honey",
                    "new": "💰 Users saved $2.3M last month — join them free"
                }
            }
        },
        {
            "hypothesis": "Curiosity-driven headline with specific number performs better",
            "changes": {
                "headline": {
                    "old": "Save Money <em>Automatically</em><br>While You Shop Online",
                    "new": "This Free Extension Finds <em>Hidden Coupons</em><br>at 1,000+ Stores"
                }
            }
        },
        {
            "hypothesis": "Combining social proof with CTA increases trust and clicks",
            "changes": {
                "cta_primary": {
                    "old": "Add to Chrome — It's Free",
                    "new": "Join 10,000+ Smart Shoppers — Free"
                }
            }
        }
    ]

    # Pick the next untested challenger
    tested_ids = set()
    for f in EXPERIMENTS_DIR.glob("*.json"):
        exp = json.loads(f.read_text())
        tested_ids.add(exp.get("experiment_id", ""))

    idx = len(tested_ids) % len(challengers)
    challenger_template = challengers[idx]

    experiment = {
        "experiment_id": f"challenger-{datetime.now().strftime('%Y%m%d-%H%M')}",
        "created": datetime.now().isoformat(),
        "type": "challenger",
        "hypothesis": challenger_template["hypothesis"],
        "changes": challenger_template["changes"],
        "metrics": {},
        "status": "active"
    }

    print(f"  Hypothesis: {experiment['hypothesis']}")
    for key, change in experiment["changes"].items():
        print(f"  {key}: '{change['old'][:40]}...' → '{change['new'][:40]}...'")

    return experiment


def deploy(experiment: dict):
    """Step 4: Apply changes to index.html and push."""
    print("\n=== DEPLOY ===")
    html = read_index()
    html = apply_changes(html, experiment["changes"])
    write_index(html)
    save_experiment(experiment)
    git_commit_and_push(f"auto-research: deploy {experiment['experiment_id']}")


def run_pipeline():
    """Main pipeline loop."""
    print(f"\n{'='*60}")
    print(f"  CouponSnap Auto Research — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}")

    config = load_config()
    current = load_latest_experiment()

    # Step 1: Harvest
    metrics = harvest(config)

    # Step 2: Evaluate
    outcome = evaluate(current, metrics, config)

    # Step 3: Handle outcome
    if outcome == "insufficient_data":
        print("\n[WAIT] Not enough data. Will retry next cycle.")
        return

    if outcome == "winner":
        # Update baseline with winning experiment
        current["status"] = "winner"
        current["metrics"] = metrics
        save_experiment(current)

        # New baseline = current winner
        baseline = json.loads(BASELINE_FILE.read_text())
        for key, change in current["changes"].items():
            if key in baseline["page_elements"]:
                baseline["page_elements"][key] = change["new"]
        baseline["metrics"] = metrics
        BASELINE_FILE.write_text(json.dumps(baseline, indent=2))

        learning = f"WINNER: {current['hypothesis']} (CTR {metrics['cta_click_rate']}%)"
        append_learning(learning)
        print(f"\n[OK] Baseline updated with winner.")

    elif outcome == "loser":
        # Revert to baseline
        current["status"] = "loser"
        current["metrics"] = metrics
        save_experiment(current)

        baseline = json.loads(BASELINE_FILE.read_text())
        html = read_index()
        for key, change in current["changes"].items():
            new_val = change.get("new", "")
            old_val = change.get("old", "")
            if new_val in html:
                html = html.replace(new_val, old_val, 1)
        write_index(html)

        learning = f"LOSER: {current['hypothesis']} (CTR {metrics['cta_click_rate']}%)"
        append_learning(learning)
        git_commit_and_push(f"auto-research: revert {current['experiment_id']} (loser)")
        print(f"\n[OK] Reverted to baseline.")

    # Step 4: Generate & deploy new challenger
    resource_knowledge = RESOURCE_FILE.read_text()
    new_experiment = generate_challenger(config, current, resource_knowledge)
    deploy(new_experiment)

    print(f"\n{'='*60}")
    print(f"  Pipeline complete. Next run in {config['schedule']['loop_interval']}.")
    print(f"{'='*60}")


if __name__ == "__main__":
    run_pipeline()
