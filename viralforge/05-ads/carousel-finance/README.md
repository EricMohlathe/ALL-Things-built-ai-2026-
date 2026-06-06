# Finance Carousel — 7 slides (ready to post)

A complete, brand-exact Instagram/TikTok carousel (1080×1350, 4:5) built as SVGs.
Topic: **"$760/year is hiding in your phone"** (finance niche). Content matches
[`../../04-content/CAROUSELS.md`](../../04-content/CAROUSELS.md).

| Slide | File | Role |
|---|---|---|
| 1 | [`slide-1.svg`](slide-1.svg) | Bold hook — "$760 a year is hiding in your phone" |
| 2 | [`slide-2.svg`](slide-2.svg) | Step 1 — open bank app, search "subscription" |
| 3 | [`slide-3.svg`](slide-3.svg) | Step 2 — sort by recurring, screenshot |
| 4 | [`slide-4.svg`](slide-4.svg) | Example — old free trials |
| 5 | [`slide-5.svg`](slide-5.svg) | Example — apps used once |
| 6 | [`slide-6.svg`](slide-6.svg) | Example — unused "premium" |
| 7 | [`slide-7.svg`](slide-7.svg) | CTA — comment "MONEY", save 📌 |

Each slide carries the logo, a `N / 7` counter, and a progress bar so the set feels
like one cohesive swipe.

## View / export to PNG
SVGs open in any browser. To export to PNG for posting:
```bash
# with rsvg-convert (librsvg)
for f in slide-*.svg; do rsvg-convert -w 1080 -h 1350 "$f" -o "${f%.svg}.png"; done
# or with ImageMagick
for f in slide-*.svg; do magick -density 144 "$f" "${f%.svg}.png"; done
```

## Regenerate / rebrand
Edit `build_carousel.py` (slide copy lives in the `SLIDES` list) and run
`python3 build_carousel.py`. Swap the copy to spin the same template for the
side-hustle or get-paid-in-USD niches.
