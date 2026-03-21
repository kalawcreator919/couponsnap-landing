# CouponSnap Landing Page — CRO Knowledge Base
*Maintained by Spark (Marketing) | Updated: 2026-03-21*

---

## 1. Core Conversion Principles

### Hierarchy of Persuasion
1. **Relevance** — Does the visitor immediately understand what this is and who it's for?
2. **Value** — Is the benefit crystal clear within 3 seconds?
3. **Trust** — Do they believe the claim?
4. **Urgency** — Why act now?
5. **Friction** — How easy is the action?

### The 3-Second Rule
Above the fold must answer in ≤3 seconds:
- What is this? (Product clarity)
- What's in it for me? (Value prop)
- Is it safe/credible? (Trust signal)

---

## 2. What We Know Works (Validated for CouponSnap)

| Signal | Why It Works |
|--------|-------------|
| Privacy-first messaging ("we never sell your data") | Honey's data scandal created high awareness; genuine differentiator |
| "Free" explicitly in CTA | Removes payment anxiety; key for Chrome extension adoption |
| "Unlike Honey" comparison | Honey has near-universal brand awareness; contrast triggers emotion |
| 1,000+ stores (specific number) | Specificity builds credibility vs vague "many stores" |
| $4B acquisition reference | Social proof by association; shows scale of the problem |

---

## 3. CRO Best Practices by Element

### Headlines (H1)
- **Benefit > Feature**: "Save money automatically" > "Coupon code extension"
- **Specificity beats vague**: "Save at 1,000+ stores" > "Save everywhere"
- **Pain point framing**: "Stop missing coupon codes" — loss aversion angle
- **Curiosity gap**: "The extension PayPal doesn't want you to know about"
- **Numbers anchor value**: "Save $247/year on average" — requires data but powerful
- **Optimal length**: 6–12 words for mobile, up to 15 for desktop

### CTA Buttons
- **Action verb + value**: "Start Saving" > "Learn More" > "Click Here"
- **First person**: "Get My Free Extension" > "Get Your Free Extension" (+10–20% in studies)
- **Specificity**: "Add to Chrome — Free" > "Install Now"
- **Size**: Bigger is usually better (min 44px touch target)
- **Placement**: Above fold CTA + end-of-page CTA minimum

### Hero Badge / Trust Signal
- Privacy angle: "🔒 We never sell your data" — differentiator
- Social proof: "Join 10,000+ smart shoppers" — FOMO + validation
- Credibility: "Works at Amazon, Walmart, Target + 1,000 more"
- Anti-Honey: "PayPal's Honey sells your data. We don't."

### Hero Description (Subtitle)
- Keep under 25 words for above-fold placement
- Lead with outcome: "Save money instantly" > "CouponSnap finds codes"
- Mention top 3 stores by name (Amazon, Walmart, Target) — recognition triggers trust
- Include "free" and "automatic" — both reduce friction

### Stats / Social Proof Numbers
- Specific > round: "1,247 stores" > "1,000+ stores" (only if accurate)
- Money saved > stores supported as primary stat
- User count is powerful once real: "47,000 installs"

---

## 4. Psychological Principles for Extension Installs

### Loss Aversion (Kahneman — 2:1 ratio)
People fear losing money more than gaining it.
- Frame: "Stop losing money at checkout" > "Save money at checkout"
- "Every time you shop without CouponSnap, you might be leaving money on the table"

### Social Proof
- Explicit user counts (once real)
- Testimonials with specifics: "Saved $43 on my last Target order" > "Great app!"
- Named store examples trigger recognition

### Authority / Credibility
- "Built by a privacy-first indie team"
- Chrome Web Store rating (once established)
- Press logos if obtained (TechCrunch, Product Hunt, etc.)

### Commitment & Consistency
- "Free, no credit card" removes all commitment barriers
- "Uninstall anytime in 10 seconds" — reduces perceived risk

---

## 5. Mobile vs Desktop Considerations

| Element | Mobile | Desktop |
|---------|--------|---------|
| Headline length | Max 8 words | Up to 15 words |
| CTA | Full width button | Inline |
| Social proof | 1 key stat | All 3 stats |
| Description | 1–2 sentences | 2–3 sentences |

*Note: Chrome Extensions install from mobile redirect to desktop — consider messaging this.*

---

## 6. Competitor Analysis

### Honey (PayPal)
- Hero: "Honey saves you money" — benefit-driven
- Weakness: Data privacy scandal; PayPal ownership now a liability
- **Our angle**: Privacy-first + indie = trust advantage

### Capital One Shopping
- Strength: Bank-backed credibility
- Weakness: Tied to Capital One brand (irrelevant to non-CC users)

---

## 7. Metrics Reference

| Metric | Good | Great | Excellent |
|--------|------|-------|-----------|
| CTA Click Rate | >2% | >5% | >10% |
| Bounce Rate | <70% | <55% | <40% |
| Avg Session Duration | >30s | >60s | >90s |

*Industry benchmarks for browser extension landing pages*

---

## 8. A/B Test Rules

1. **Max 2 variables per experiment** (see config.json constraints)
2. **Minimum 50 sessions** before evaluating winner
3. **5% improvement threshold** for challenger to win
4. **Document everything** — losing experiments teach us too
5. **Never sacrifice clarity for cleverness** — confused visitors don't convert
6. **Preserve privacy-first messaging** — it's the core differentiator

---

## 9. Experiment Log Summary

| Experiment | Variables Changed | Result | Lift |
|------------|-------------------|--------|------|
| baseline-v1 | — (original) | Awaiting data | — |
| exp-001 | headline + hero_badge | Pending | — |
| exp-002 | cta_primary | Pending | — |
| exp-003 | hero_description | Pending | — |
| exp-004 | headline + stats | Pending | — |
| exp-005 | cta_primary + hero_badge | Pending | — |
| exp-006 | headline | Pending | — |
| exp-007 | hero_description + stats | Pending | — |
| exp-008 | hero_badge | Pending | — |
| exp-009 | headline + cta_primary | Pending | — |
| exp-010 | hero_description + cta_primary | Pending | — |

*Auto-updated by orchestrator after each evaluation cycle*
