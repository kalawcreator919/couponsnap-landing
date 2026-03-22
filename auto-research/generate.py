#!/usr/bin/env python3
"""
generate.py — LoopLab Auto-Research Pipeline Step 3
Use Claude API to generate 3 challenger variants based on evaluation.
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
VARIANTS_DIR = Path(__file__).parent / "variants"

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL = "claude-sonnet-4-6"


def load_evaluation() -> dict:
    eval_file = DATA_DIR / "evaluation.json"
    if not eval_file.exists():
        raise FileNotFoundError("evaluation.json not found. Run evaluate.py first.")
    with open(eval_file, encoding="utf-8") as f:
        return json.load(f)


def load_harvest() -> dict:
    harvest_file = DATA_DIR / "harvest.json"
    if not harvest_file.exists():
        raise FileNotFoundError("harvest.json not found. Run harvest.py first.")
    with open(harvest_file, encoding="utf-8") as f:
        return json.load(f)


def call_claude(prompt: str) -> str:
    """Call Claude API via urllib (no SDK dependency)."""
    import urllib.request

    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")

    payload = json.dumps({
        "model": MODEL,
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": prompt}]
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST"
    )

    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        return result["content"][0]["text"]


def build_prompt(harvest: dict, evaluation: dict, variant_type: str) -> str:
    copy = harvest["copy_elements"]
    weak_points = evaluation["top_3_issues"]
    weak_summary = "\n".join(f"- [{wp['category']}] {wp['issue']}" for wp in weak_points)

    variant_instructions = {
        "headline": (
            "Focus: Rewrite the H1 headline and hero subtitle ONLY. "
            "Keep all other copy identical. "
            "Generate a stronger, more specific, urgency-driven headline that addresses the weak points. "
            "Also update the nav CTA and hero badge to match the new headline direction."
        ),
        "cta": (
            "Focus: Rewrite ALL call-to-action buttons ONLY. "
            "Keep headline and body copy identical. "
            "Generate more action-oriented, benefit-focused CTA copy. "
            "Each CTA should use strong verbs and convey the specific benefit."
        ),
        "layout": (
            "Focus: Restructure the page LAYOUT and section ORDER. "
            "Move the strongest social proof (testimonials/stats) closer to the top. "
            "Add a sticky CTA or urgency element. "
            "Keep all copy identical but reorganize the HTML structure for better flow."
        ),
    }

    instruction = variant_instructions.get(variant_type, variant_instructions["headline"])

    return f"""You are a world-class CRO (Conversion Rate Optimization) expert.

## Current Landing Page Analysis

**Product:** CouponSnap — Free Chrome extension that auto-finds deals and applies coupon codes.
**URL:** {harvest['url']}

**Current H1:** {copy.get('h1', 'N/A')}
**Current Nav CTA:** {copy.get('nav_cta', 'N/A')}
**Current Hero Badge:** {copy.get('hero_badge', 'N/A')}
**Current CTAs:** {json.dumps(copy.get('ctas', []), ensure_ascii=False)}
**Overall Conversion Score:** {evaluation['overall_score']}/100

**Top Weak Points Identified:**
{weak_summary}

## Your Task: Generate Variant Type "{variant_type.upper()}"

{instruction}

## Output Format

Return ONLY a JSON object with this structure:
{{
  "variant_type": "{variant_type}",
  "rationale": "1-2 sentence explanation of the CRO hypothesis being tested",
  "hypothesis": "If we [change X], then [Y metric] will improve by [Z%] because [reason]",
  "changes": {{
    "h1": "new headline text (if changed)",
    "hero_subtitle": "new subtitle (if changed)",
    "hero_badge": "new badge text (if changed)",
    "nav_cta": "new nav CTA text (if changed)",
    "ctas": [{{"location": "hero|nav|footer", "old": "old text", "new": "new text"}}],
    "layout_notes": "description of layout changes (if layout variant)"
  }},
  "html_patches": [
    {{
      "selector": "CSS selector or description",
      "old_html": "exact HTML to find",
      "new_html": "replacement HTML"
    }}
  ]
}}

Be specific. Return valid JSON only, no markdown fences."""


def apply_patches(html: str, patches: list) -> str:
    """Apply HTML patches to create the variant HTML."""
    result = html
    for patch in patches:
        old = patch.get("old_html", "")
        new = patch.get("new_html", "")
        if old and new and old in result:
            result = result.replace(old, new, 1)
            print(f"  [patch] Applied: {patch.get('selector', 'unknown')}")
        else:
            print(f"  [patch] SKIP (not found): {patch.get('selector', 'unknown')}")
    return result


def generate_variant(harvest: dict, evaluation: dict, variant_type: str) -> dict:
    print(f"\n[generate] Generating {variant_type} variant via Claude API...")
    prompt = build_prompt(harvest, evaluation, variant_type)
    response_text = call_claude(prompt)

    # Parse JSON response
    try:
        variant_data = json.loads(response_text)
    except json.JSONDecodeError:
        # Try to extract JSON from response
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            variant_data = json.loads(json_match.group(0))
        else:
            raise ValueError(f"Could not parse Claude response as JSON: {response_text[:200]}")

    # Apply patches to create variant HTML
    base_html = harvest["raw_html"]
    patches = variant_data.get("html_patches", [])
    variant_html = apply_patches(base_html, patches)

    # Add variant tracking marker
    variant_id = f"v_{variant_type}_{datetime.utcnow().strftime('%Y%m%d')}"
    variant_html = variant_html.replace(
        "gtag('config', 'G-BRZEPQKZSY');",
        f"gtag('config', 'G-BRZEPQKZSY');\n    gtag('event', 'variant_view', {{variant_id: '{variant_id}', variant_type: '{variant_type}'}});"
    )

    result = {
        "variant_id": variant_id,
        "variant_type": variant_type,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "rationale": variant_data.get("rationale", ""),
        "hypothesis": variant_data.get("hypothesis", ""),
        "changes": variant_data.get("changes", {}),
        "patches_applied": len([p for p in patches if p.get("old_html", "") in base_html]),
        "patches_total": len(patches),
        "html": variant_html,
    }

    return result


def main():
    print("[generate] Loading evaluation and harvest data...")
    evaluation = load_evaluation()
    harvest = load_harvest()

    VARIANTS_DIR.mkdir(parents=True, exist_ok=True)

    variant_types = ["headline", "cta", "layout"]
    all_variants = []

    for vtype in variant_types:
        try:
            variant = generate_variant(harvest, evaluation, vtype)
            all_variants.append(variant)

            # Save variant HTML
            html_path = VARIANTS_DIR / f"variant_{vtype}.html"
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(variant["html"])

            # Save variant metadata (without HTML for readability)
            meta = {k: v for k, v in variant.items() if k != "html"}
            meta_path = DATA_DIR / f"variant_{vtype}_meta.json"
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)

            print(f"  [generate] {vtype}: {variant['patches_applied']}/{variant['patches_total']} patches applied")
            print(f"  [generate] Hypothesis: {variant['hypothesis'][:100]}...")

        except Exception as e:
            print(f"  [generate] ERROR generating {vtype} variant: {e}")

    # Save summary
    summary = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "base_url": harvest["url"],
        "variants": [
            {
                "variant_id": v["variant_id"],
                "variant_type": v["variant_type"],
                "rationale": v["rationale"],
                "hypothesis": v["hypothesis"],
            }
            for v in all_variants
        ]
    }
    with open(DATA_DIR / "variants_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\n[generate] Generated {len(all_variants)}/3 variants")
    print(f"[generate] Variant HTML files saved to: {VARIANTS_DIR}")

    return all_variants


if __name__ == "__main__":
    main()
