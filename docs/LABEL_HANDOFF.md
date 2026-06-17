# BLK PHX LABS — Focus Powder Label Handoff
**Date:** 2026-06-16
**Status:** Logo locked. Label drafted in Affinity. 2 blockers before Supliful submission.

---

## Product

Supliful "Focus Powder" (Sour Grape flavor) — white-label dropship, Phase 1 SKU.

---

## Files

```
label-mockups-extracted/
├── 89b73670-...-label-mockups.zip      # Original Supliful template download
├── OSM0GRAP_Focus_Powder_(Sour Grape).psd   # Supliful mockup (smart-object → linked .ai)
├── OSM0GRAP_Focus_Powder_(Sour Grape).ai    # Supliful label dieline
├── BLKPHXLABEL.af                       # Working Affinity file — label in progress
├── BLKPHXLABEL.png                      # Flattened preview of current label state
├── 1.png                                # Final logo mark (transparent-ready, phoenix icon)
└── README.txt                           # Supliful's official editing instructions
```

`BLKPHXLABEL.af` is the live working file — open in Affinity Designer to continue editing.

---

## What's Done

- **Logo mark**: geometric phoenix icon generated via Gemini, black line art + single electric-blue accent. Clean, symmetric, no artifacts. Approved.
- **Wordmark assembly**: "BLK PHX LABS" typeset in Canva, combined with the icon.
- **Label layout**: logo block placed on the Supliful dieline in Affinity, sitting between the Drug Facts/Supplement Facts panels. Ingredient list and Supplement Facts panel untouched (Supliful's formulation data — do not edit).

---

## Blockers — must fix before submission

| # | Issue | Fix needed |
|---|---|---|
| 1 | **Compliance**: tagline reads "Enhances mental clarity*" — an unhedged/absolute claim | Reword to mechanism-hedged language, e.g. "Formulated to support mental clarity*" or "May support focus and mental clarity*" |
| 2 | **Legal**: manufacturer/distributor block still has placeholder text — `[LLC name here]` / `[your full address and phone number]` | Needs real registered business name + mailing address (LLC, DBA, or registered agent/virtual mailbox address). If no LLC formed yet, this is a prerequisite step bigger than the label itself |

---

## Verify Before Export

- Supplement Facts panel text size — confirm ≥6pt on white background / ≥7pt on black, per Supliful's labeling guide. Can't be judged from a flattened PNG preview; check actual point sizes in Affinity.

---

## Remaining Steps

1. Reword tagline (compliance fix)
2. Insert real manufacturer name + address (legal fix)
3. Verify font sizes in Affinity
4. Export from Affinity: `File → Export` → PDF (print preset) for the Label Design; PNG for the product mockup image
5. Upload both files to the Focus Powder product page in Supliful
6. Expect a design verification pass from Supliful before first order ships — budget for one revision round
7. Once approved, get the Supliful variant ID and `SUPLIFUL_API_KEY` → populate `SUPLIFUL_VARIANT_MAP` in `.env` to wire up auto-fulfillment (see root `HANDOFF.md`)

---

## Tooling Notes (for next session / next product)

- **Icon generation**: Gemini — prompt for icon-only (no text baked in), flat vector style, no gradient/shadow, isolated on white background (transparent-background requests are unreliable; remove white bg after)
- **Wordmark + assembly**: Canva — typeset brand name with a real font rather than letting AI render text (AI-generated text in logos is consistently lower quality)
- **Label file editing**: Affinity Designer opens Supliful's `.ai`/`.psd` natively — no Adobe CC needed. Keep `.ai` and `.psd` in the same folder so the smart-object link resolves.
