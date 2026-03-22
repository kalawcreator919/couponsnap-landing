#!/usr/bin/env python3
"""
harvest.py — LoopLab Auto-Research Pipeline Step 1
Scrape landing page HTML and analyze current copy structure.
"""

import urllib.request
import json
import re
import sys
from datetime import datetime
from pathlib import Path

TARGET_URL = "https://kalawcreator919.github.io/couponsnap-landing"
OUTPUT_DIR = Path(__file__).parent / "data"


def fetch_html(url: str) -> str:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "LoopLab-AutoResearch/1.0 (CRO Pipeline)"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def extract_copy_elements(html: str) -> dict:
    """Extract key copy elements from HTML for analysis."""
    elements = {}

    # Hero headline (h1)
    h1_match = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.DOTALL | re.IGNORECASE)
    if h1_match:
        elements["h1"] = re.sub(r"<[^>]+>", "", h1_match.group(1)).strip()

    # Hero subheadline (hero p)
    hero_p = re.search(r'class="hero"[^>]*>.*?<p[^>]*>(.*?)</p>', html, re.DOTALL | re.IGNORECASE)
    if hero_p:
        elements["hero_subtitle"] = re.sub(r"<[^>]+>", "", hero_p.group(1)).strip()

    # All CTAs (anchor tags with btn classes)
    cta_pattern = re.compile(r'<a[^>]*class="[^"]*btn[^"]*"[^>]*href="([^"]*)"[^>]*>(.*?)</a>', re.DOTALL | re.IGNORECASE)
    elements["ctas"] = []
    for match in cta_pattern.finditer(html):
        href = match.group(1)
        text = re.sub(r"<[^>]+>", "", match.group(2)).strip()
        if text:
            elements["ctas"].append({"href": href, "text": text})

    # Section titles (h2)
    h2_pattern = re.compile(r"<h2[^>]*>(.*?)</h2>", re.DOTALL | re.IGNORECASE)
    elements["h2s"] = [
        re.sub(r"<[^>]+>", "", m.group(1)).strip()
        for m in h2_pattern.finditer(html)
        if re.sub(r"<[^>]+>", "", m.group(1)).strip()
    ]

    # Nav CTA
    nav_cta = re.search(r'class="nav-cta"[^>]*>(.*?)</a>', html, re.DOTALL | re.IGNORECASE)
    if nav_cta:
        elements["nav_cta"] = re.sub(r"<[^>]+>", "", nav_cta.group(1)).strip()

    # Hero badge
    badge = re.search(r'class="hero-badge"[^>]*>(.*?)</div>', html, re.DOTALL | re.IGNORECASE)
    if badge:
        elements["hero_badge"] = re.sub(r"<[^>]+>", "", badge.group(1)).strip()

    # Stats
    stats = []
    stat_pattern = re.compile(
        r'class="stat-num"[^>]*>(.*?)</div>.*?class="stat-label"[^>]*>(.*?)</div>',
        re.DOTALL | re.IGNORECASE
    )
    for m in stat_pattern.finditer(html):
        stats.append({
            "value": re.sub(r"<[^>]+>", "", m.group(1)).strip(),
            "label": re.sub(r"<[^>]+>", "", m.group(2)).strip()
        })
    elements["stats"] = stats

    # Testimonials
    testimonials = []
    test_pattern = re.compile(
        r'class="testimonial"[^>]*>.*?<p>(.*?)</p>.*?<cite>(.*?)</cite>',
        re.DOTALL | re.IGNORECASE
    )
    for m in test_pattern.finditer(html):
        testimonials.append({
            "text": re.sub(r"<[^>]+>", "", m.group(1)).strip(),
            "author": re.sub(r"<[^>]+>", "", m.group(2)).strip()
        })
    elements["testimonials"] = testimonials

    return elements


def count_words(html: str) -> int:
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()
    return len(text.split())


def main():
    print(f"[harvest] Fetching {TARGET_URL} ...")
    html = fetch_html(TARGET_URL)

    copy_elements = extract_copy_elements(html)
    word_count = count_words(html)

    harvest_data = {
        "url": TARGET_URL,
        "harvested_at": datetime.utcnow().isoformat() + "Z",
        "html_length": len(html),
        "word_count": word_count,
        "copy_elements": copy_elements,
        "raw_html": html,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_file = OUTPUT_DIR / "harvest.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(harvest_data, f, ensure_ascii=False, indent=2)

    print(f"[harvest] Saved to {out_file}")
    print(f"[harvest] HTML length: {len(html)} chars, ~{word_count} words")
    print(f"[harvest] H1: {copy_elements.get('h1', 'N/A')}")
    print(f"[harvest] CTAs found: {len(copy_elements.get('ctas', []))}")
    print(f"[harvest] H2s: {copy_elements.get('h2s', [])}")

    return harvest_data


if __name__ == "__main__":
    main()
