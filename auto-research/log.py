#!/usr/bin/env python3
"""
log.py — LoopLab Auto-Research Pipeline Step 5
Pull GA4 data and auto-generate CRO performance reports.

Requires:
  - GA4_PROPERTY_ID env var (e.g., "properties/123456789")
  - Google service account JSON in GA4_CREDENTIALS env var (base64 encoded)
    OR path to credentials file in GA4_CREDENTIALS_FILE env var
"""

import json
import os
import base64
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
REPORTS_DIR = Path(__file__).parent / "reports"

GA4_PROPERTY_ID = os.environ.get("GA4_PROPERTY_ID", "")  # e.g. "properties/123456789"
GA4_CREDENTIALS = os.environ.get("GA4_CREDENTIALS", "")   # base64 JSON service account
GA4_CREDENTIALS_FILE = os.environ.get("GA4_CREDENTIALS_FILE", "")


def get_ga4_access_token(credentials: dict) -> str:
    """Get OAuth2 access token for GA4 Data API using service account."""
    import time
    import hmac
    import hashlib

    # Build JWT for service account authentication
    now = int(time.time())
    header = base64.urlsafe_b64encode(json.dumps({"alg": "RS256", "typ": "JWT"}).encode()).rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(json.dumps({
        "iss": credentials["client_email"],
        "scope": "https://www.googleapis.com/auth/analytics.readonly",
        "aud": "https://oauth2.googleapis.com/token",
        "iat": now,
        "exp": now + 3600,
    }).encode()).rstrip(b"=").decode()

    # Sign with RSA private key
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.hazmat.backends import default_backend

        private_key = serialization.load_pem_private_key(
            credentials["private_key"].encode(),
            password=None,
            backend=default_backend()
        )
        signing_input = f"{header}.{payload}".encode()
        signature = private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
        jwt = f"{header}.{payload}.{base64.urlsafe_b64encode(signature).rstrip(b'=').decode()}"
    except ImportError:
        raise ImportError("pip install cryptography required for GA4 service account auth")

    # Exchange JWT for access token
    data = urllib.parse.urlencode({
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": jwt,
    }).encode()

    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        token_data = json.loads(resp.read().decode())
        return token_data["access_token"]


def load_credentials() -> dict | None:
    """Load GA4 service account credentials."""
    if GA4_CREDENTIALS:
        try:
            return json.loads(base64.b64decode(GA4_CREDENTIALS).decode())
        except Exception as e:
            print(f"[log] Error decoding GA4_CREDENTIALS: {e}")
            return None
    if GA4_CREDENTIALS_FILE and Path(GA4_CREDENTIALS_FILE).exists():
        with open(GA4_CREDENTIALS_FILE) as f:
            return json.load(f)
    return None


def query_ga4(access_token: str, property_id: str, date_range_days: int = 7) -> dict:
    """Query GA4 Data API for conversion events."""
    end_date = datetime.utcnow().strftime("%Y-%m-%d")
    start_date = (datetime.utcnow() - timedelta(days=date_range_days)).strftime("%Y-%m-%d")

    payload = json.dumps({
        "dateRanges": [{"startDate": start_date, "endDate": end_date}],
        "dimensions": [
            {"name": "eventName"},
            {"name": "customEvent:cta_location"},
            {"name": "customEvent:variant_id"},
        ],
        "metrics": [
            {"name": "eventCount"},
            {"name": "totalUsers"},
            {"name": "sessions"},
        ],
        "dimensionFilter": {
            "filter": {
                "fieldName": "eventName",
                "inListFilter": {
                    "values": ["cta_click", "how_it_works_click", "variant_view", "blog_click"]
                }
            }
        },
        "limit": 1000,
    }).encode()

    req = urllib.request.Request(
        f"https://analyticsdata.googleapis.com/v1beta/{property_id}:runReport",
        data=payload,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        method="POST"
    )

    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def parse_ga4_response(response: dict) -> dict:
    """Parse GA4 API response into structured report data."""
    rows = response.get("rows", [])
    events = {}

    for row in rows:
        dims = [d.get("value", "") for d in row.get("dimensionValues", [])]
        metrics = [m.get("value", "0") for m in row.get("metricValues", [])]

        event_name = dims[0] if dims else "unknown"
        cta_location = dims[1] if len(dims) > 1 else ""
        variant_id = dims[2] if len(dims) > 2 else "control"

        key = f"{event_name}|{variant_id}"
        if key not in events:
            events[key] = {
                "event_name": event_name,
                "variant_id": variant_id or "control",
                "cta_location": cta_location,
                "event_count": 0,
                "users": 0,
                "sessions": 0,
            }

        events[key]["event_count"] += int(metrics[0]) if metrics else 0
        events[key]["users"] += int(metrics[1]) if len(metrics) > 1 else 0
        events[key]["sessions"] += int(metrics[2]) if len(metrics) > 2 else 0

    return {"events": list(events.values()), "raw_row_count": len(rows)}


def calculate_conversion_rates(events_data: dict, deployment: dict | None) -> dict:
    """Calculate conversion rates per variant."""
    events = events_data.get("events", [])

    # Group by variant
    variants = {}
    for event in events:
        vid = event["variant_id"] or "control"
        if vid not in variants:
            variants[vid] = {"views": 0, "cta_clicks": 0, "engagement": 0}

        if event["event_name"] == "variant_view":
            variants[vid]["views"] += event["event_count"]
        elif event["event_name"] == "cta_click":
            variants[vid]["cta_clicks"] += event["event_count"]
        elif event["event_name"] in ("how_it_works_click", "blog_click"):
            variants[vid]["engagement"] += event["event_count"]

    # Calculate rates
    results = {}
    for vid, data in variants.items():
        views = data["views"] or 1  # avoid div by zero
        results[vid] = {
            "variant_id": vid,
            "views": data["views"],
            "cta_clicks": data["cta_clicks"],
            "engagement_events": data["engagement"],
            "cta_conversion_rate": round(data["cta_clicks"] / views * 100, 2),
            "engagement_rate": round(data["engagement"] / views * 100, 2),
        }

    # Rank by CTA conversion rate
    ranked = sorted(results.values(), key=lambda x: x["cta_conversion_rate"], reverse=True)

    return {
        "variants": ranked,
        "winner": ranked[0]["variant_id"] if ranked else None,
        "winner_lift": (
            round((ranked[0]["cta_conversion_rate"] - ranked[-1]["cta_conversion_rate"]) /
                  max(ranked[-1]["cta_conversion_rate"], 0.01) * 100, 1)
            if len(ranked) > 1 else 0
        ),
    }


def generate_markdown_report(analysis: dict, ga4_raw: dict, date_range_days: int) -> str:
    """Generate human-readable markdown report."""
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    winner = analysis.get("winner", "N/A")
    variants = analysis.get("variants", [])

    rows = ""
    for v in variants:
        rows += f"| {v['variant_id']} | {v['views']:,} | {v['cta_clicks']:,} | {v['cta_conversion_rate']}% | {v['engagement_rate']}% |\n"

    winner_section = ""
    if winner and winner != "control" and analysis.get("winner_lift", 0) > 5:
        winner_section = f"""
## 🏆 Recommendation: Promote Winner

**Winner:** `{winner}` with **{analysis['winner_lift']}% lift** over baseline.

Action: Replace control `index.html` with `challengers/{winner.replace('v_', '').split('_')[0]}/index.html` and run next cycle.
"""

    return f"""# CouponSnap CRO Report — {now}

**Period:** Last {date_range_days} days
**Pipeline:** LoopLab Auto-Research (Harvest → Evaluate → Generate → Deploy → Log)

## Variant Performance

| Variant | Views | CTA Clicks | CTA Conv. Rate | Engagement Rate |
|---------|-------|------------|----------------|-----------------|
{rows}
{winner_section}
## Notes

- CTA click = user clicked "Add to Chrome" button (conversion goal)
- Engagement = "How it works" click or blog link click
- Minimum 100 views per variant recommended for statistical significance
- Data source: GA4 Property `{GA4_PROPERTY_ID}`

---
*Generated by LoopLab Auto-Research Pipeline*
"""


def generate_mock_report() -> dict:
    """Generate a mock report when GA4 credentials are not available."""
    print("[log] GA4 credentials not configured — generating mock report structure")
    return {
        "report_type": "mock",
        "note": "GA4_PROPERTY_ID and GA4_CREDENTIALS required for real data",
        "setup_instructions": {
            "step1": "Create GA4 property and get Measurement ID (G-XXXXXXXXXX)",
            "step2": "Create Google service account with Analytics Read permission",
            "step3": "Set GA4_PROPERTY_ID=properties/YOUR_NUMERIC_ID",
            "step4": "Set GA4_CREDENTIALS=<base64 encoded service account JSON>",
        },
        "events_to_track": [
            "cta_click (conversion goal)",
            "how_it_works_click (engagement)",
            "variant_view (variant exposure)",
            "blog_click (engagement)",
        ],
        "sample_report_structure": {
            "variants": [
                {"variant_id": "control", "cta_conversion_rate": 2.1},
                {"variant_id": "v_headline_20260321", "cta_conversion_rate": 3.4},
                {"variant_id": "v_cta_20260321", "cta_conversion_rate": 2.8},
                {"variant_id": "v_layout_20260321", "cta_conversion_rate": 2.5},
            ],
            "winner": "v_headline_20260321",
            "winner_lift": 61.9,
        }
    }


def main():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # Load deployment manifest if exists
    deployment = None
    deploy_file = DATA_DIR / "deployment.json"
    if deploy_file.exists():
        with open(deploy_file) as f:
            deployment = json.load(f)

    credentials = load_credentials()

    if not credentials or not GA4_PROPERTY_ID:
        mock_data = generate_mock_report()
        out_file = DATA_DIR / "ga4_report.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(mock_data, f, ensure_ascii=False, indent=2)
        print(f"[log] Mock report saved to {out_file}")
        print("[log] Configure GA4_PROPERTY_ID + GA4_CREDENTIALS to enable real reporting")
        return mock_data

    print(f"[log] Fetching GA4 data for property: {GA4_PROPERTY_ID}")
    access_token = get_ga4_access_token(credentials)
    raw_response = query_ga4(access_token, GA4_PROPERTY_ID, date_range_days=7)
    events_data = parse_ga4_response(raw_response)
    analysis = calculate_conversion_rates(events_data, deployment)

    # Save raw GA4 data
    out_file = DATA_DIR / "ga4_report.json"
    full_report = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "property_id": GA4_PROPERTY_ID,
        "events_data": events_data,
        "analysis": analysis,
    }
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(full_report, f, ensure_ascii=False, indent=2)

    # Generate markdown report
    md_report = generate_markdown_report(analysis, events_data, date_range_days=7)
    report_filename = f"report_{datetime.utcnow().strftime('%Y%m%d')}.md"
    md_path = REPORTS_DIR / report_filename
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_report)

    print(f"[log] GA4 data: {len(events_data.get('events', []))} event rows")
    print(f"[log] Winner: {analysis.get('winner', 'N/A')} (+{analysis.get('winner_lift', 0)}% lift)")
    print(f"[log] Report saved to {md_path}")

    return full_report


if __name__ == "__main__":
    main()
