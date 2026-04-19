# Hero Image Brief — Nanobanana 2 / Midjourney Fallback

> **Status:** Ready to use (2026-04-19)
> **Owner:** `designer`
> **Consumer:** A-37 landing page Hero section (§2.2.1)
> **Tool:** Nanobanana 2 (preferred) or Midjourney v6+ (fallback)
> **Why not Claude Design:** this is a full photorealistic/illustrative render, not a UI mockup — CD is great for geometric assets, weaker for atmospheric compositions
> **Linear issue:** SPO-142
> **Output path:** `assets/branding/hero.png` (1920x1080) + `hero@2x.png` if available

---

## Why this brief exists

The landing hero must communicate "Bloomberg Terminal meets Opta Stats" in a single glance. It is the **first 500ms** of every prospect's encounter with SportsLab. It has to feel credible, technical, professional — not like a gambling site.

Three prompt variants are provided. Mateusz runs each, picks the strongest, and iterates with seed variation inside the chosen variant.

---

## Universal parameters (apply to all variants)

- **Aspect ratio:** 16:9
- **Resolution target:** 1920x1080 (1080p minimum; 4K preferred if tool supports)
- **Midjourney params:** `--ar 16:9 --style raw --stylize 100 --v 6.1`
  - `--style raw` strips MJ's default prettification
  - `--stylize 100` (low) keeps the prompt literal; avoid 400+ which introduces flourishes
- **Nanobanana 2 params:** `aspect 16:9, quality: high, realism: photographic, stylization: low`
- **Seed:** record seed of the chosen generation so we can re-render if assets need revision

---

## Universal negative prompts (concatenate to every variant)

```
--no cartoon, comic style, illustration style, anime, childlike, naive art,
casino, chips, dice, roulette, slot machine, poker cards, playing cards,
money, dollar signs, euro signs, cash, stacks of bills, gold coins,
trophies, medals, cheering crowds, raised arms, victory pose, celebration,
player faces, athletes portraits, recognizable people, team logos, branded
balls, Nike, Adidas, Puma, Premier League logo, Champions League logo,
bright neon colors, pink, magenta, saturated blues, rainbow gradients,
fire, explosions, lens flares, lightning bolts, sparkles,
stock photo, handshakes, business meetings, people pointing at screens,
watermarks, text, typography, numbers, words, letters, logos
```

---

## Universal color direction

```
Color palette: dominant dark background #0B0D14 (near-black with blue undertone),
primary accent #5B67F2 (desaturated indigo — NOT bright blue, NOT purple),
positive accent #22C55E (clean green — NOT neon, NOT lime),
secondary text tone #9AA0A6 (cool gray),
rare subtle white highlights #E8EAED (never pure white).

Overall mood: muted, premium, nocturnal, data-first. Think Linear, Vercel,
Stripe dark mode — not Las Vegas, not esports.
```

---

## Variant A — Minimalist

**Concept:** extreme restraint. One hero element. Massive negative space. Feels like a luxury product page.

**Full prompt (paste into Nanobanana or MJ):**

```
Ultra-minimalist abstract composition for a B2B analytics product hero image.
A single elegant data visualization floats in the center-right of a vast dark
void: a smooth probability curve or equity line chart, rendered as a thin
glowing line in desaturated indigo (#5B67F2) transitioning to soft green
(#22C55E) at its rising end. The curve is mathematical, precise, almost
scientific — like a physics textbook diagram, not a marketing graphic.

Behind the curve, barely visible, a subtle grid of faint blue-gray lines
suggests a coordinate system, fading to black at the edges. A handful of
small geometric points (not more than five) sit on the curve as markers,
each a tiny filled circle.

Lighting: soft ambient glow emanates only from the curve itself, casting a
gentle blue-green halo into the surrounding darkness. No other light source.
The rest of the frame is deep near-black (#0B0D14), with 70%+ of the image
being negative space.

Mood: contemplative, analytical, expensive. The kind of image you would see
in a Stripe product launch page or a Bloomberg Terminal advertisement. Zero
ornamentation, zero flourish, zero celebration.

Aspect ratio 16:9, resolution 1920x1080, photographic realism, soft cinematic
lighting, high dynamic range, f/1.4 shallow depth of field on the curve edges.

--ar 16:9 --style raw --stylize 100 --v 6.1
```

Negative prompt: [paste universal negative prompts block above]

---

## Variant B — Data-heavy

**Concept:** a "control room" composition with multiple data panels. Information density as statement. Football presence is atmospheric, not literal.

**Full prompt:**

```
Wide cinematic composition depicting an analyst's view of a data-rich
workspace, rendered as an abstract multi-panel dashboard floating in dark
space. Three to four translucent panels are arranged in an asymmetric
horizontal layout across the frame, each displaying a different mathematical
abstraction:

Left panel: a scatter plot with dozens of small indigo (#5B67F2) points
distributed across a two-dimensional field, with a subtle regression line
in soft green (#22C55E).

Center panel (the largest and most prominent): a smooth equity curve trending
upward from bottom-left to top-right, rendered in glowing green (#22C55E),
with faint grid lines behind it in dark gray.

Right panel: a probability distribution histogram, bars in muted indigo, a
dashed reference line cutting through.

Behind all panels, at very low opacity (10-15%), an abstract football field
silhouette — only the center circle and penalty arcs visible as faint white
lines on the deep dark background (#0B0D14). No players, no ball, no stadium
architecture. The field is atmosphere, not subject.

Between and around the panels, subtle mathematical notation fragments float
as decorative elements — integrals, sigma symbols, small equations — all in
the secondary gray tone (#9AA0A6) at low opacity. These read as texture, not
as literal formulas.

Lighting: each panel glows softly from within, casting indigo and green light
into the surrounding dark. The overall effect is nocturnal, like a late-night
research session. Cinematic depth, subtle lens bokeh on out-of-focus panels.

Mood: dense, professional, serious. Bloomberg Terminal meets Opta Stats meets
a quantitative research lab. Feels like infrastructure, not entertainment.

Aspect ratio 16:9, resolution 1920x1080, photographic realism, volumetric
atmospheric lighting, moderate depth of field.

--ar 16:9 --style raw --stylize 100 --v 6.1
```

Negative prompt: [paste universal negative prompts block above]

---

## Variant C — Football-forward

**Concept:** football is the primary visual element; data is the treatment. More emotional than A and B, but still restrained. Use only if A and B feel too abstract for the target audience.

**Full prompt:**

```
Cinematic hero composition: a silhouetted football viewed from a low angle
against a deep dark background (#0B0D14). The football is rendered as a pure
geometric silhouette — classic pentagon-hexagon pattern visible but stripped
of any brand or logo. Matte black surface with subtle rim lighting in
desaturated indigo (#5B67F2) tracing the sphere's edge.

Emerging from and wrapping around the football: thin glowing data curves and
lines, as if the ball itself generates analytics. Multiple smooth trajectories
— some in indigo (#5B67F2), some in soft green (#22C55E) — arc through the
frame like slow-exposure light trails or orbital paths. Some curves connect
to small floating data points (tiny filled circles) that hover at varying
depths around the ball.

Behind the football, at very low opacity, a faint grid suggests a coordinate
system or a tactical pitch overlay — barely perceptible, more texture than
graphic.

The ball occupies roughly the right third of the frame. The left two-thirds
is mostly negative space, with the data trajectories extending into it,
eventually dissolving into the dark. This leaves room for landing page copy
to sit over the left portion without competing with the image.

Lighting: low-key, dramatic, mostly from behind-right. The ball is 70% in
shadow. The only light sources are the data trails themselves and the rim
lighting. No harsh highlights, no shiny surfaces.

Mood: precision engineering applied to football. Serious, technical, premium.
Feels like the opening shot of a documentary, not a sports advertisement.

Aspect ratio 16:9, resolution 1920x1080, photographic realism, cinematic
color grading, low-key lighting, subtle volumetric atmosphere, shallow depth
of field on the data trails.

--ar 16:9 --style raw --stylize 100 --v 6.1
```

Negative prompt: [paste universal negative prompts block above, **additionally**: `stadium, grass texture, crowd, players, boots, goal, net, referee`]

---

## Selection guidance

| Variant | Strongest for | Weakest for |
|---|---|---|
| A — Minimalist | Technical B2B audiences, HN, research-oriented prospects | Emotional engagement, first-time visitors |
| B — Data-heavy | Demonstrating product depth, dashboard buyers (clubs, tipsters) | Mobile hero (too much detail lost on small screens) |
| C — Football-forward | Broader audience, non-technical tipsters, social share appeal | May read as "just another sports site" if overdone |

**Default recommendation:** render all three, review at 1920x1080 **and** at 600x338 (mobile hero crop), pick the one that holds up at both sizes. If undecided, **A** is the safest brand fit; **B** is the safest "demonstrate sophistication" move.

---

## QA checklist before accepting a render

- [ ] Zero text, numbers, or letterforms anywhere in the image (all text on landing is rendered by HTML/CSS)
- [ ] Background reads as #0B0D14 (not pure black, not navy) — check with color picker
- [ ] No casino imagery: no chips, dice, cards, roulette, slot machines
- [ ] No money imagery: no currency symbols, no cash, no coins
- [ ] No player faces or recognizable identities
- [ ] No team logos or branded balls (variant C must use unbranded ball)
- [ ] Accent colors read as desaturated indigo + clean green, not neon
- [ ] Image has a clear "dark space" area (usually left or top) where headline copy can sit legibly
- [ ] Looks professional at 600px wide thumbnail (mobile preview test)
- [ ] Final file is PNG with transparent fallback version if layout requires it; otherwise JPEG at quality 90+

---

## Output

```
assets/branding/
├── hero.png              # 1920x1080, chosen variant final
├── hero@2x.png           # 3840x2160 if tool supports (retina)
├── hero.jpg              # compressed JPEG fallback for slow connections (quality 85)
└── hero-mobile.png       # 828x1792 portrait crop if needed, from same seed
```

Record the tool, variant, seed, and prompt version in `docs/alfa/graphics_iteration_log.md` so we can reproduce or regenerate.

---

## References

- `docs/alfa/graphics_for_claude_design.md` — icons + OG card (CD-based)
- `docs/alfa/lovable_prompts.md` §2.2.1 — Hero section spec
- `ideas/vision.md` — brand positioning ("Bloomberg for sports")
- Style references (external): Linear.app hero, Vercel.com dark mode marketing, Stripe Sessions 2024 keynote slides
