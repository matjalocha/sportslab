# Graphics Brief for Claude Design — SportsLab Alpha

> **Status:** Ready to paste (2026-04-19)
> **Owner:** `designer`
> **Consumers:** A-36 graphics pack → A-37 landing (Methodology cards, OG meta, hero fallback)
> **Tool:** Claude Design (CD) — primary visual generation for panel + landing
> **Linear issue:** SPO-142
> **Related:** [lovable_prompts.md](lovable_prompts.md) §1.1 (panel tokens), [ADR-0015](../architecture/adr-0015-report-design-inter-jetbrains-plotly.md) (typography)

---

## How to use this file

1. Copy the section you need (Methodology icons, OG card) and paste verbatim into Claude Design as the first message
2. If CD output drifts off-brand, **edit this file first**, then re-paste — never hand-tune inside a CD session
3. Each generated asset lands in `assets/branding/` with filenames specified per section
4. For hero image, see separate brief: `hero_image_brief_nanobanana.md` (CD is not the right tool for photorealistic render)

---

## 0. Shared context (prepend to every CD prompt)

```
You are generating a visual asset for SportsLab, a B2B SaaS analytics panel for
sports value-betting. Target audience: professional tipsters and ML-literate
bettors — NOT casual punters, NOT casino players.

Tone: data-forward, precise, analytical. Think Bloomberg Terminal meets Opta
Stats — NOT casino, NOT flashy, NOT hype. No dollar signs, no dice, no neon,
no cheering crowds, no player faces, no team logos.

Aesthetic references:
- Bloomberg Terminal (information density, muted palette)
- Stripe dashboard (typography discipline, restraint)
- Linear app (dark surfaces, subtle depth)
- Vercel marketing (geometric precision)
```

---

## 1. Design tokens (strict — do not deviate)

These tokens are canonical. Every asset must use these exact hex values. No approximations.

| Token | Hex | Usage in graphics |
|---|---|---|
| `bg` | `#0B0D14` | Dominant background on every dark asset |
| `surface` | `#12141D` | Card backgrounds, raised panels |
| `surface-2` | `#1A1D28` | Hover states, nested surfaces |
| `brand` | `#5B67F2` | Primary accent — icon strokes, chart highlight lines |
| `good` | `#22C55E` | Positive signals — up-trends, wins, CLV |
| `bad` | `#EF4444` | Negative signals — down-trends, losses |
| `warn` | `#F59E0B` | Cautionary states (rare in graphics) |
| `text` | `#E8EAED` | Primary text on dark background |
| `text-muted` | `#9AA0A6` | Secondary text, labels, captions, watermarks |
| `border` | `#2A2D38` | Grid lines, subtle dividers |

Typography (for OG card and any text-containing asset):
- **Body / display**: Inter (weights: 400, 500, 600, 700)
- **Data / code**: JetBrains Mono (weights: 400, 500, 700)

Source of truth: `docs/alfa/lovable_prompts.md` §1.1 + `docs/architecture/adr-0015-report-design-inter-jetbrains-plotly.md`.

---

## 2. Methodology icons (4 icons, 120x120 each)

Used on landing page Methodology section (A-37 §2.2.3). Each icon illustrates a pillar of SportsLab's technical credibility.

### Shared spec for all 4 icons

```
Format: SVG preferred, PNG transparent acceptable fallback
Canvas: 120x120px, transparent background
Style: line-art, monochrome
Stroke: 2px, color #5B67F2 (brand) — alternatively currentColor for theming flexibility
Fill: none (outlined shapes only)
Line caps: round
Line joins: round
Composition: centered, 12px safe area on all sides (actual drawing in 96x96 inner box)
No text labels inside the icon — text is rendered separately by the landing page
No gradients, no shadows, no 3D — flat geometric line-art only
```

### 2.1 `icon-features.svg` — "935 Features"

**Concept:** feature engineering scale — many small atomic inputs combining into signal.

**CD prompt:**
```
Generate a line-art icon, 120x120, transparent background, stroke #5B67F2, stroke
width 2px, rounded line caps.

Composition: a 3x3 grid of 9 small rounded squares (each ~16x16px with 4px radius),
centered, with 8px spacing between squares. Outline only, no fill. 2 of the 9
squares (top-right and bottom-left) are slightly emphasized by a thin connecting
line running diagonally behind them, suggesting relationships between features.

The grid reads as "many discrete inputs forming structure." No text, no numbers,
no labels inside the icon. Clean, symmetric, architectural.
```

### 2.2 `icon-calibration.svg` — "Calibrated Probabilities"

**Concept:** probability calibration curve — model output vs reality, the 45° diagonal is the ground truth.

**CD prompt:**
```
Generate a line-art icon, 120x120, transparent background, stroke #5B67F2, stroke
width 2px, rounded line caps.

Composition: a small coordinate system occupying the inner 96x96 area.
- Thin axis lines (left and bottom), same stroke color but at 60% opacity
- A dashed diagonal reference line from bottom-left to top-right (this is "perfect calibration")
- A solid sigmoid-like S-curve that crosses the diagonal near the center — starts
  slightly below the diagonal at the bottom-left, bends through it in the middle,
  finishes slightly above at the top-right
- 3 small dots on the sigmoid curve at evenly spaced x-values (probability bins)

Reads as "our model's predicted probability vs observed frequency, with the
diagonal as reference." No axis labels, no numbers.
```

### 2.3 `icon-kelly.svg` — "Portfolio Kelly"

**Concept:** fractional allocation across multiple bets — not everything gets the same stake.

**CD prompt:**
```
Generate a line-art icon, 120x120, transparent background, stroke #5B67F2, stroke
width 2px, rounded line caps.

Composition: a horizontal stacked bar divided into 5 segments of varying widths,
centered vertically. From left to right the segments are roughly: 35%, 25%, 18%,
14%, 8% of total width. Each segment is outlined (no fill), separated by a 2px
gap. The bar sits on a baseline (thin horizontal line).

Above the bar, 3 small tick marks at irregular intervals suggest the top of a
capital axis. Reads as "fractional stake allocation across a portfolio of bets,
with larger stakes on higher-edge opportunities." Clean, architectural.

Alternative composition (designer can choose): same concept rendered as a donut
chart with 5 unequal arcs instead of stacked bar. Prefer the stacked bar for
consistency with other icons.
```

### 2.4 `icon-clv.svg` — "Closing Line Value"

**Concept:** equity curve with a clear upward trend, crossing the bookmaker's implied baseline.

**CD prompt:**
```
Generate a line-art icon, 120x120, transparent background, stroke #5B67F2, stroke
width 2px, rounded line caps.

Composition: a line chart in the inner 96x96 area.
- Thin baseline at the bottom (x-axis) at 60% opacity
- A main equity curve that starts bottom-left, moves upward with 2-3 small
  local peaks and troughs, reaching a clearly higher point top-right (positive
  slope overall). The curve is smooth, not jagged.
- A dashed horizontal "breakeven" line at ~40% of canvas height — the equity
  curve starts below this line, crosses it around 30% of x-axis, and ends well
  above it
- A single small filled circle at the highest point of the curve (peak), same
  color as stroke

Reads as "sustained edge over the bookmaker's closing line." No axis labels.
```

---

## 3. OG card (1200x630, social share)

Used for Twitter, Discord, LinkedIn, Telegram meta previews. Must work at thumbnail size.

### Shared spec

```
Format: PNG (for og:image), SVG source preferred if CD can export both
Canvas: 1200x630px
Background: #0B0D14 solid
Safe area: 60px margin on all sides for text-critical content
Text: Inter for body, JetBrains Mono for data values
Color usage: #E8EAED primary text, #9AA0A6 captions, #5B67F2 accents,
  #22C55E for positive metric values
Subtle gradient: top-left corner, radial, #5B67F2 at 20% opacity fading to
  transparent over ~400px radius — adds depth without noise
```

### 3.1 Variant A — "Formal / corporate" (recommended default)

**CD prompt:**
```
Generate an Open Graph social share card, 1200x630px, background solid #0B0D14
with a subtle radial gradient in the top-left corner (#5B67F2 at 20% opacity
fading to transparent).

Two-column layout with a vertical divider line at 40% width (#2A2D38, 1px):

LEFT COLUMN (480px wide, 60px padding):
- Large "SL" monogram at top, #22C55E, geometric line-art style, approximately
  160x160px, matching the favicon aesthetic (stroke-based, rounded caps)
- Below the monogram, 48px spacing
- Headline: "Value bets, mathematically proven." in Inter 48px, weight 700,
  color #E8EAED, line-height 1.15. Wrap to 2 lines naturally.
- Below headline, 16px spacing
- Subline: "B2B analytics panel for ML-literate bettors" in Inter 18px,
  weight 400, color #9AA0A6

RIGHT COLUMN (720px wide, 60px padding):
- A mini equity curve illustration filling most of the column. Line chart,
  2px stroke, color #22C55E, smooth upward trend with 3-4 subtle peaks and
  troughs. A faint grid (#2A2D38, 1px, 20% opacity) behind the curve.
- Two data callouts as small cards floating over the chart at natural positions:
  - Top-right area: "CLV" label in Inter 12px #9AA0A6, value "+2.8%" in
    JetBrains Mono 28px weight 700 #22C55E
  - Lower-middle area: "ROI 30d" label in Inter 12px #9AA0A6, value "+4.2%"
    in JetBrains Mono 28px weight 700 #22C55E
  Each callout sits on a #12141D surface with 1px #2A2D38 border, 8px radius,
  12px padding.

BOTTOM-RIGHT CORNER (outside main columns):
- "sportslab.dev" in JetBrains Mono 14px, color #9AA0A6, right-aligned,
  40px from bottom-right edges
```

### 3.2 Variant B — "Minimal" (alternative for text-heavy contexts)

**CD prompt:**
```
Generate an Open Graph card, 1200x630px, background #0B0D14 with the same
top-left radial gradient (#5B67F2 at 20% opacity).

Single centered composition, no columns:
- "SL" monogram, #22C55E, 200x200px, centered horizontally at 180px from top
- Below, 48px spacing, headline "Value bets, mathematically proven." in Inter
  56px weight 700 #E8EAED, centered, max-width 800px
- Below, 16px spacing, a thin horizontal divider (#2A2D38, 1px, 120px wide)
- Below divider, 16px spacing, three inline stats separated by dot dividers:
  "CLV +2.8%   •   ROI +4.2%   •   14 leagues"
  in JetBrains Mono 18px, #E8EAED for values, #9AA0A6 for labels
- "sportslab.dev" bottom-right, JetBrains Mono 14px #9AA0A6, 40px inset

No chart, no illustrations. Pure typographic composition with generous breathing
room. Feels editorial.
```

### 3.3 Variant C — "Data-heavy" (for technical audiences, HN/Reddit)

**CD prompt:**
```
Generate an Open Graph card, 1200x630px, background #0B0D14 with top-left
radial gradient (#5B67F2 at 20% opacity).

Three-column layout, each column separated by a 1px #2A2D38 vertical line:

COLUMN 1 (400px, "Evidence"):
- Header "CALIBRATION" in Inter 11px weight 600 #9AA0A6, letter-spacing 0.1em
- A small calibration chart below: diagonal reference line (dashed, #2A2D38)
  and a sigmoid curve (solid, #5B67F2, 2px)
- Below chart: "ECE 1.4%" in JetBrains Mono 32px weight 700 #22C55E

COLUMN 2 (400px, "Performance"):
- Header "EQUITY CURVE 30D"
- A mini line chart, #22C55E, clear upward trend
- Below: "CLV +2.8%" in JetBrains Mono 32px weight 700 #22C55E

COLUMN 3 (400px, "Scale"):
- Header "COVERAGE"
- A small 3x3 grid of dots representing leagues/features
- Below: "14 leagues" in JetBrains Mono 32px weight 700 #E8EAED
- Secondary: "935 features" in JetBrains Mono 16px #9AA0A6

TOP BAR (above the 3 columns, full width, 80px tall):
- "SL" monogram left-aligned, #22C55E, 48x48px
- "sportslab.dev" right-aligned, JetBrains Mono 14px #9AA0A6

Feels like a dashboard frame — Bloomberg Terminal aesthetic.
```

**Mateusz picks one variant.** Default recommendation: **Variant A** for broad audiences; switch to **C** if landing traffic skews technical.

---

## 4. Output filenames

Place generated assets at:

```
assets/branding/
├── icon-features.svg
├── icon-calibration.svg
├── icon-kelly.svg
├── icon-clv.svg
├── og-card.png           # 1200x630, from chosen variant
├── og-card.svg           # source if available
└── favicon.svg           # already produced separately
```

---

## 5. QA checklist (run after every CD export)

- [ ] All hex values match the token table in §1 exactly (no drift like `#5b68f3` or `#22c45d`)
- [ ] Icons render cleanly at 48x48 (Methodology card size on mobile) and at 120x120 (desktop)
- [ ] OG card readable at 600x315 thumbnail (Twitter preview size)
- [ ] No stray `#FFFFFF` backgrounds, no default CD watermarks, no placeholder text
- [ ] Typography matches — Inter for UI, JetBrains Mono for data. If CD substitutes a generic sans, reject and re-prompt
- [ ] SVGs optimized: no `<metadata>` blocks, no editor cruft, <10KB each
- [ ] File names lowercase-kebab-case as specified in §4

---

## 6. References

- `docs/alfa/lovable_prompts.md` §1.1 — canonical panel tokens
- `docs/architecture/adr-0015-report-design-inter-jetbrains-plotly.md` — typography rationale
- `docs/alfa/hero_image_brief_nanobanana.md` — hero image (separate tool, photorealistic)
- `ideas/vision.md` — brand positioning (Bloomberg for sports)
