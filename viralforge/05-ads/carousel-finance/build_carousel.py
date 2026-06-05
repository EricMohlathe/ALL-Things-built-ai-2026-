#!/usr/bin/env python3
"""Generate the 7-slide ViralForge 'finance' carousel as brand-exact SVGs (1080x1350)."""
import os

SLIDES = [
    {"label": "START HERE", "lines": ["$760 a year is", "hiding in your", "phone."], "hi": 0, "cta": "Let's find it  →"},
    {"label": "STEP 1", "lines": ["Open your bank", "app. Search", "“subscription”."], "hi": None, "cta": "Swipe  →"},
    {"label": "STEP 2", "lines": ["Sort by recurring", "charges.", "Screenshot it."], "hi": None, "cta": "Swipe  →"},
    {"label": "EXAMPLE", "lines": ["Old free trials", "you forgot to", "cancel? Gone."], "hi": 2, "cta": "Swipe  →"},
    {"label": "EXAMPLE", "lines": ["Apps you opened", "once? You", "won't miss them."], "hi": None, "cta": "Swipe  →"},
    {"label": "EXAMPLE", "lines": ["“Premium” you", "never use?", "Downgrade to free."], "hi": 2, "cta": "Swipe  →"},
    {"label": "YOUR MOVE", "lines": ["Comment", "“MONEY” for the", "1-screen audit."], "hi": 1, "cta": "Save this  \U0001F4CC", "final": True},
]

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def slide_svg(i, s):
    n = i + 1
    headline = ""
    y = 560
    for idx, line in enumerate(s["lines"]):
        color = "url(#orange)" if s.get("hi") == idx else "#F4F4F6"
        headline += f'  <text x="90" y="{y}" font-size="98" font-weight="700" fill="{color}">{esc(line)}</text>\n'
        y += 122
    final = s.get("final")
    cta_block = (
        f'''  <g transform="translate(90,1120)">
    <rect width="430" height="92" rx="20" fill="url(#orange)"/>
    <text x="215" y="60" font-size="34" text-anchor="middle" fill="#1a0c02" font-weight="700">{esc(s["cta"])}</text>
  </g>'''
        if final else
        f'  <text x="90" y="1180" font-size="40" fill="#FF6A2C" font-weight="600">{esc(s["cta"])}</text>'
    )
    footer = (
        '  <text x="90" y="1290" font-size="22" fill="#9A9AA8">@viralforge · save + share · results vary with effort</text>'
        if final else
        f'  <text x="90" y="1290" font-size="22" fill="#5f5f6b">ViralForge · faceless money tips</text>'
    )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1350" viewBox="0 0 1080 1350" font-family="'Space Grotesk','Segoe UI',sans-serif">
  <defs>
    <linearGradient id="orange" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#FF6A2C"/><stop offset="1" stop-color="#FF9A3D"/></linearGradient>
    <radialGradient id="glow" cx="0.85" cy="0.12" r="0.7"><stop offset="0" stop-color="#FF6A2C" stop-opacity="0.22"/><stop offset="1" stop-color="#FF6A2C" stop-opacity="0"/></radialGradient>
  </defs>
  <rect width="1080" height="1350" fill="#0B0B0F"/>
  <rect width="1080" height="1350" fill="url(#glow)"/>
  <!-- logo -->
  <g transform="translate(90,84)">
    <rect width="52" height="52" rx="14" fill="url(#orange)"/>
    <text x="26" y="37" font-size="30" text-anchor="middle" fill="#1a0c02" font-weight="700">⚡</text>
    <text x="70" y="36" font-size="30" fill="#F4F4F6" font-weight="700">ViralForge</text>
  </g>
  <!-- slide counter -->
  <text x="990" y="120" font-size="28" text-anchor="end" fill="#9A9AA8" font-weight="600">{n} / 7</text>
  <!-- progress bar -->
  <rect x="90" y="150" width="900" height="6" rx="3" fill="#1E1E29"/>
  <rect x="90" y="150" width="{int(900*n/7)}" height="6" rx="3" fill="url(#orange)"/>
  <!-- label -->
  <text x="90" y="360" font-size="30" fill="#FF6A2C" font-weight="600" letter-spacing="4">{esc(s["label"])}</text>
{headline}{cta_block}
{footer}
</svg>
'''

here = os.path.dirname(os.path.abspath(__file__))
for i, s in enumerate(SLIDES):
    path = os.path.join(here, f"slide-{i+1}.svg")
    with open(path, "w") as f:
        f.write(slide_svg(i, s))
    print("wrote", path)
