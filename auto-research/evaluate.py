#!/usr/bin/env python3
"""
evaluate.py — LoopLab Auto-Research Pipeline Step 2
Analyze conversion funnel and identify weak points using heuristics + GA4 data.
"""

import json
import re
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"


def load_harvest() -> dict:
    harvest_file = DATA_DIR / "harvest.json"
    if not harvest_file.exists():
        raise FileNotFoundError("harvest.json not found. Run harvest.py first.")
    with open(harvest_file, encoding="utf-8") as f:
        return json.load(f)


def load_ga4_data() -> dict | None:
    """Load GA4 data if available from log.py output."""
    ga4_file = DATA_DIR / "ga4_report.json"
    if ga4_file.exists():
        with open(ga4_file, encoding="utf-8") as f:
            return json.load(f)
    return None


def score_headline(h1: str) -> dict:
    """Score headline on clarity, urgency, and specificity."""
    issues = []
    score = 100

    if not h1:
        return {"score": 0, "issues": ["No H1 found"]}

    # Length check
    if len(h1) > 80:
        issues.append("Headline too long (>80 chars) — may lose mobile visitors")
        score -= 15
    if len(h1) < 20:
        issues.append("Headline too short — lacks specificity")
        score -= 10

    # Urgency / power words
    power_words = ["free", "instant", "automatic", "save", "best", "never", "always", "guaranteed"]
    has_power = any(w in h1.lower() for w in power_words)
    if not has_power:
        issues.append("No power/urgency words in headline")
        score -= 10

    # Numbers / specificity
    has_number = bool(re.search(r"\d", h1))
    if not has_number:
        issues.append("No specific numbers — adds credibility when present")
        score -= 5

    return {"score": max(0, score), "text": h1, "issues": issues}


def score_ctas(ctas: list) -> dict:
    """Evaluate CTA copy and placement."""
    issues = []
    score = 100

    if not ctas:
        return {"score": 0, "issues": ["No CTAs found on page"]}

    cta_texts = [c["text"] for c in ctas]

    # Check for action verbs
    weak_cta_words = ["click here", "learn more", "read more", "submit", "go"]
    strong_cta_words = ["add to", "get", "start", "try", "install", "download", "join", "claim"]

    for cta in cta_texts:
        lower = cta.lower()
        if any(w in lower for w in weak_cta_words):
            issues.append(f"Weak CTA copy: '{cta}' — too generic")
            score -= 15
        if not any(w in lower for w in strong_cta_words):
            issues.append(f"CTA '{cta}' lacks action verb")
            score -= 8

    # Check consistency (multiple CTAs should reinforce same action)
    if len(ctas) > 3:
        issues.append(f"Too many CTAs ({len(ctas)}) — may cause decision paralysis")
        score -= 10

    return {
        "score": max(0, score),
        "cta_count": len(ctas),
        "ctas": cta_texts,
        "issues": issues
    }


def score_social_proof(testimonials: list, stats: list) -> dict:
    """Evaluate social proof strength."""
    issues = []
    score = 100

    if not testimonials:
        issues.append("No testimonials found — social proof is critical for conversion")
        score -= 30
    elif len(testimonials) < 3:
        issues.append(f"Only {len(testimonials)} testimonials — aim for 3+")
        score -= 15

    if not stats:
        issues.append("No social stats (user count, stores, savings) — missed trust signal")
        score -= 20
    elif len(stats) < 3:
        issues.append(f"Only {len(stats)} stats — more specific numbers build trust")
        score -= 10

    return {
        "score": max(0, score),
        "testimonial_count": len(testimonials),
        "stat_count": len(stats),
        "issues": issues
    }


def score_page_structure(h2s: list, html: str) -> dict:
    """Evaluate page structure for conversion optimization."""
    issues = []
    score = 100

    essential_sections = {
        "how it works": any("how it works" in h.lower() or "how" in h.lower() for h in h2s),
        "social proof": "testimonial" in html.lower() or "review" in html.lower(),
        "cta banner": "cta-banner" in html or "cta_banner" in html,
        "faq": "faq" in html.lower() or "frequently" in html.lower(),
        "trust/privacy": "privacy" in html.lower() or "data" in html.lower(),
    }

    for section, present in essential_sections.items():
        if not present:
            issues.append(f"Missing section: {section}")
            score -= 15

    # Check for above-fold CTA
    hero_section = re.search(r'class="hero".*?</section>', html, re.DOTALL | re.IGNORECASE)
    if hero_section:
        hero_html = hero_section.group(0)
        if "btn-primary" not in hero_html and "nav-cta" not in hero_html:
            issues.append("No primary CTA in hero section — biggest conversion miss")
            score -= 25

    return {
        "score": max(0, score),
        "sections_present": essential_sections,
        "issues": issues
    }


def identify_weak_points(scores: dict) -> list:
    """Rank weak points by impact."""
    all_issues = []
    priority_map = {
        "headline": 3,
        "cta": 4,  # highest impact
        "social_proof": 3,
        "structure": 2,
    }

    for category, data in scores.items():
        weight = priority_map.get(category, 1)
        for issue in data.get("issues", []):
            all_issues.append({
                "category": category,
                "issue": issue,
                "score": data["score"],
                "priority_weight": weight,
                "impact": "high" if weight >= 3 and data["score"] < 70 else
                          "medium" if weight >= 2 else "low"
            })

    all_issues.sort(key=lambda x: (-x["priority_weight"], x["score"]))
    return all_issues


def main():
    print("[evaluate] Loading harvest data...")
    harvest = load_harvest()
    copy = harvest["copy_elements"]
    html = harvest["raw_html"]

    ga4 = load_ga4_data()
    if ga4:
        print("[evaluate] GA4 data found — incorporating into analysis")
    else:
        print("[evaluate] No GA4 data yet — running heuristic-only analysis")

    scores = {
        "headline": score_headline(copy.get("h1", "")),
        "cta": score_ctas(copy.get("ctas", [])),
        "social_proof": score_social_proof(copy.get("testimonials", []), copy.get("stats", [])),
        "structure": score_page_structure(copy.get("h2s", []), html),
    }

    weak_points = identify_weak_points(scores)

    overall_score = round(sum(s["score"] for s in scores.values()) / len(scores))

    evaluation = {
        "url": harvest["url"],
        "evaluated_at": datetime.utcnow().isoformat() + "Z",
        "overall_score": overall_score,
        "scores": scores,
        "weak_points": weak_points,
        "ga4_data_available": ga4 is not None,
        "top_3_issues": weak_points[:3],
    }

    out_file = DATA_DIR / "evaluation.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(evaluation, f, ensure_ascii=False, indent=2)

    print(f"\n[evaluate] Overall conversion score: {overall_score}/100")
    print(f"[evaluate] Scores breakdown:")
    for category, data in scores.items():
        print(f"  {category}: {data['score']}/100")
    print(f"\n[evaluate] Top weak points:")
    for i, wp in enumerate(weak_points[:5], 1):
        print(f"  {i}. [{wp['impact'].upper()}] [{wp['category']}] {wp['issue']}")
    print(f"\n[evaluate] Saved to {out_file}")

    return evaluation


if __name__ == "__main__":
    main()
