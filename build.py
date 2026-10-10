#!/usr/bin/env python3
"""Builds README.md and the artwork in assets/ for the github.com/viny4 profile page.

Every image comes in a day version (GitHub's light theme) and a night version (dark
theme), and the README picks one with <picture>. Text inside the images is drawn as
glyph outlines, so it looks the same in every browser without web fonts.

To change the profile, edit CONTENT and run:

    pip install fonttools brotli   # once
    python3 build.py

Fonts (Instrument Serif, Inter, JetBrains Mono) and logos (Simple Icons) are
downloaded once into .cache/.
"""
from __future__ import annotations

import math
import random
import re
import subprocess
from html import escape
from pathlib import Path
from types import SimpleNamespace

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
CACHE = ROOT / ".cache"

CONTENT = {
    "name": "Vinayagam",
    "role": "Backend Engineer",
    "fields": "Distributed Systems · Physics · Astronomy",
    "username": "viny4",
    "portfolio": ("vinay-engineer.me", "https://vinay-engineer.me"),
    "linkedin": ("LinkedIn", "https://linkedin.com/in/vinjr"),
    "links": [
        ("Portfolio", "https://vinay-engineer.me"),
        ("LinkedIn", "https://linkedin.com/in/vinjr"),
        ("Orbica", "https://orbica.space"),
        ("Engineering Shelf", "https://engineering-shelf.pages.dev"),
    ],
    # The banner and footer stress the half that matches the viewer's theme.
    "day": ("Building ", "backend systems", " by day."),
    "night": ("Exploring ", "the universe", " by night."),
    "about": [
        ("Now", "Backend engineer at **[Trames](https://trames.io)**, working mainly with "
                "TypeScript, Node.js, PostgreSQL and AWS."),
        ("Building", "**[Orbica](https://orbica.space)**, an open space encyclopedia covering rockets, "
                     "satellites and launches since 1957, with live 3D orbital tracking."),
        ("Before", "Built and shipped backend systems serving **~200K users** at Thaagam Foundation, "
                   "using Django, PostgreSQL, Redis and the WhatsApp Business API."),
        ("Studying", "Finishing an MCA alongside full-time engineering work."),
    ],
    "stack": [
        ("Languages", ["TypeScript", "Go", "Python", "JavaScript", "C#"]),
        ("Backend", ["Node.js", "NestJS", "Express", "Django", "FastAPI", "Next.js"]),
        ("Data", ["PostgreSQL", "Redis", "Neo4j", "Prisma"]),
        ("Infrastructure", ["AWS", "Docker", "Cloudflare", "GitHub Actions", "Grafana"]),
    ],
    "featured": {
        "name": "Orbica",
        "url": "https://orbica.space",
        "label": "Live · orbica.space",
        "tagline": "Space encyclopedia + real-time orbital tracking",
        "description": "Rockets, satellites and launches since 1957, with live 3D orbital tracking "
                       "and real-time SGP4 propagation over WebSockets.",
        "stack": ["Next.js", "React Three Fiber", "Go", "PostgreSQL"],
    },
    "projects": [
        {
            "name": "Nexora",
            "url": "https://github.com/viny4/nexora-saas-platform",
            "label": "SaaS · Billing",
            "icon": "tenants",
            "tagline": "Multi-tenant SaaS billing platform",
            "description": "Row Level Security between tenants, SERIALIZABLE credit transactions "
                           "and partitioned audit logs.",
            "stack": ["NestJS", "Prisma", "PostgreSQL", "Redis"],
        },
        {
            "name": "Backend Masterclass",
            "url": "https://github.com/viny4/Backend-Masterclass",
            "label": "APIs · Playground",
            "icon": "terminal",
            "tagline": "Backend engineering playground",
            "description": "JWT authentication, multi-role authorization, WebSockets "
                           "and HTTP Range video streaming.",
            "stack": ["Django REST", "FastAPI", "WebSockets"],
        },
        {
            "name": "Movie Knowledge Graph",
            "url": "https://github.com/viny4/movie-knowledge-graph",
            "label": "Graphs · Neo4j",
            "icon": "graph",
            "tagline": "Movies as a graph instead of relational tables",
            "description": "A Neo4j knowledge graph connecting films, actors and directors.",
            "stack": ["Neo4j", "Cypher", "TypeScript", "Express"],
        },
        {
            "name": "Panebox",
            "url": "https://github.com/viny4/panebox",
            "label": "Desktop · AI",
            "icon": "panes",
            "tagline": "Desktop AI workspace",
            "description": "ChatGPT, Claude, Gemini and other AI tools side by side, "
                           "each in its own isolated session.",
            "stack": ["Electron", "JavaScript"],
        },
    ],
    "learning": [
        "Distributed systems", "Database internals", "PostgreSQL internals", "AWS architecture",
        "TypeScript / Node.js", "Data structures & algorithms", "Astrophysics & orbital mechanics",
    ],
}

SECTIONS = ["About", "Stack", "Selected work", "Activity", "Currently learning", "Connect"]

# Day matches GitHub's light theme (#ffffff page), night its dark theme (#0d1117 page).
THEMES = {
    "day": dict(
        canvas="#f7f7f3", panel="#fbfbf9", well="#ffffff", chip="#ffffff", line="#e4e4de",
        ink="#111111", ink2="#33332f", muted="#66665f", faint="#9b9b93",
        accent="#0e7c46", stroke="#1f9d5f", satellite="#111111",
    ),
    "night": dict(
        canvas="#05080c", panel="#0f141a", well="#0a0e13", chip="#141a22", line="#232a33",
        ink="#edf0f2", ink2="#c5ccd3", muted="#8b96a0", faint="#5e6974",
        accent="#5adc8c", stroke="#5adc8c", satellite="#e9fff1",
    ),
}

CDN = "https://cdn.jsdelivr.net/npm/"
FONT_FILES = {
    "serif": "@fontsource/instrument-serif@5.3.0/files/instrument-serif-latin-400-normal.woff2",
    "serif-italic": "@fontsource/instrument-serif@5.3.0/files/instrument-serif-latin-400-italic.woff2",
    "sans": "@fontsource/inter@5.3.0/files/inter-latin-400-normal.woff2",
    "sans-medium": "@fontsource/inter@5.3.0/files/inter-latin-500-normal.woff2",
    "sans-semibold": "@fontsource/inter@5.3.0/files/inter-latin-600-normal.woff2",
    "mono": "@fontsource/jetbrains-mono@5.3.0/files/jetbrains-mono-latin-400-normal.woff2",
    "mono-medium": "@fontsource/jetbrains-mono@5.3.0/files/jetbrains-mono-latin-500-normal.woff2",
}
ICONS = "simple-icons@16.34.0/icons/"
# Simple Icons slugs; names in DRAWN are drawn here because Simple Icons doesn't carry them.
LOGOS = {
    "TypeScript": "typescript", "Go": "go", "Python": "python", "JavaScript": "javascript",
    "Node.js": "nodedotjs", "NestJS": "nestjs", "Express": "express", "Django": "django",
    "FastAPI": "fastapi", "Next.js": "nextdotjs", "PostgreSQL": "postgresql", "Redis": "redis",
    "Neo4j": "neo4j", "Prisma": "prisma", "Docker": "docker", "Cloudflare": "cloudflare",
    "GitHub Actions": "githubactions", "Grafana": "grafana", "C#": "csharp", "AWS": "aws",
}
DRAWN = {"csharp", "aws", "linkedin", "globe"}

# Orbit regimes drawn in the banner: name, radii, real period, seconds per loop, dashes.
ORBITS = [
    ("LEO", 74, 25, "92 min", 9.0, None),
    ("MEO", 116, 40, "12 h", 17.0, "3 4"),
    ("GEO", 162, 56, "23 h 56 m", 29.0, "1 3.5"),
]

MOTION_CSS = (
    ".pulse{transform-box:fill-box;transform-origin:center;animation:pulse 2.6s ease-out infinite}"
    "@keyframes pulse{0%{transform:scale(1);opacity:.6}100%{transform:scale(3.4);opacity:0}}"
    ".tw{animation:tw 5s ease-in-out infinite}"
    "@keyframes tw{0%,100%{opacity:1}50%{opacity:.15}}"
    "@media (prefers-reduced-motion:reduce){.pulse,.tw{animation:none}.pulse{opacity:0}}"
)


def fetch(path: str) -> Path:
    file = CACHE / re.sub(r"[^A-Za-z0-9._-]", "_", path)
    if not file.exists():
        CACHE.mkdir(exist_ok=True)
        # curl uses the system's certificates; python.org builds of Python often have none set up.
        subprocess.run(["curl", "-fsSL", "--max-time", "60", "-o", str(file), CDN + path], check=True)
    return file


def fmt(v: float) -> str:
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


# ── Fonts ────────────────────────────────────────────────────────────────────

class Font:
    def __init__(self, key: str, path: Path):
        self.key = key
        self.tt = TTFont(path)
        self.upm = self.tt["head"].unitsPerEm
        self.cmap = self.tt.getBestCmap()
        self.hmtx = self.tt["hmtx"]
        self.glyphset = self.tt.getGlyphSet()
        self.cap_height = getattr(self.tt["OS/2"], "sCapHeight", 0) or self.upm * 0.7
        self.kern_lookups = kern_lookups(self.tt)
        self._paths: dict[str, str] = {}
        self._kern: dict[tuple[str, str], int] = {}

    def glyph(self, ch: str) -> str:
        name = self.cmap.get(ord(ch))
        if name is None:
            raise SystemExit(f"{self.key} has no glyph for {ch!r}")
        return name

    def kern(self, left: str, right: str) -> int:
        key = (left, right)
        if key not in self._kern:
            self._kern[key] = sum(pair_adjustment(subtables, left, right) for subtables in self.kern_lookups)
        return self._kern[key]

    def layout(self, text: str, size: float, tracking: float = 0.0):
        """Glyph names with their x offsets, and the run's width, in px."""
        scale = size / self.upm
        x, placed, prev = 0.0, [], None
        for ch in text:
            name = self.glyph(ch)
            if prev is not None:
                x += self.kern(prev, name) * scale
            placed.append((name, x))
            x += self.hmtx[name][0] * scale + tracking * size
            prev = name
        return placed, (x - tracking * size if text else 0.0)

    def width(self, text: str, size: float, tracking: float = 0.0) -> float:
        return self.layout(text, size, tracking)[1]

    def cap(self, size: float) -> float:
        return self.cap_height * size / self.upm

    def lsb(self, text: str, size: float) -> float:
        return self.hmtx[self.glyph(text[0])][1] * size / self.upm

    def path(self, name: str) -> str:
        if name not in self._paths:
            pen = SVGPathPen(self.glyphset, ntos=lambda v: str(round(v)))
            self.glyphset[name].draw(pen)
            self._paths[name] = pen.getCommands()
        return self._paths[name]


def kern_lookups(tt: TTFont):
    """The pair-positioning subtables behind the 'kern' feature for Latin."""
    if "GPOS" not in tt:
        return []
    gpos = tt["GPOS"].table
    if not gpos.ScriptList or not gpos.FeatureList:
        return []
    scripts = {r.ScriptTag: r.Script for r in gpos.ScriptList.ScriptRecord}
    script = scripts.get("latn") or scripts.get("DFLT") or next(iter(scripts.values()))
    features = script.DefaultLangSys.FeatureIndex if script.DefaultLangSys else []
    records = gpos.FeatureList.FeatureRecord
    lookup_ids = sorted({i for f in features if records[f].FeatureTag == "kern"
                         for i in records[f].Feature.LookupListIndex})
    lookups = []
    for i in lookup_ids:
        lookup = gpos.LookupList.Lookup[i]
        subtables = []
        for st in lookup.SubTable:
            if lookup.LookupType == 9:
                if st.ExtensionLookupType != 2:
                    continue
                st = st.ExtSubTable
            elif lookup.LookupType != 2:
                continue
            subtables.append((st, {g: n for n, g in enumerate(st.Coverage.glyphs)}))
        lookups.append(subtables)
    return lookups


def pair_adjustment(subtables, left: str, right: str) -> int:
    for st, coverage in subtables:
        if left not in coverage:
            continue
        if st.Format == 1:
            for record in st.PairSet[coverage[left]].PairValueRecord:
                if record.SecondGlyph == right:
                    return x_advance(record.Value1)
            continue
        c1 = st.ClassDef1.classDefs.get(left, 0) if st.ClassDef1 else 0
        c2 = st.ClassDef2.classDefs.get(right, 0) if st.ClassDef2 else 0
        return x_advance(st.Class1Record[c1].Class2Record[c2].Value1)
    return 0


def x_advance(value) -> int:
    return (getattr(value, "XAdvance", 0) or 0) if value is not None else 0


def wrap(font: Font, text: str, size: float, max_width: float) -> list[str]:
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if line and font.width(trial, size) > max_width:
            lines.append(line)
            line = word
        else:
            line = trial
    return lines + [line] if line else lines


F: dict[str, Font] = {}


# ── SVG document ─────────────────────────────────────────────────────────────

class Svg:
    def __init__(self, w: float, h: float, title: str):
        self.w, self.h, self.title = w, h, title
        self.defs: dict[str, str] = {}
        self.css: list[str] = []
        self.parts: list[str] = []

    def add(self, markup: str):
        self.parts.append(markup)

    def define(self, id_: str, markup: str):
        self.defs.setdefault(id_, markup)

    def animate(self):
        if MOTION_CSS not in self.css:
            self.css.append(MOTION_CSS)

    def text(self, font: Font, s: str, x: float, y: float, size: float, fill: str,
             anchor: str = "start", tracking: float = 0.0, opacity: float | None = None) -> float:
        placed, width = font.layout(s, size, tracking)
        if anchor == "middle":
            x -= width / 2
        elif anchor == "end":
            x -= width
        k = size / font.upm
        uses = []
        for name, gx in placed:
            d = font.path(name)
            if not d:
                continue
            gid = f"{font.key}-{re.sub(r'[^A-Za-z0-9]', '_', name)}"
            self.defs.setdefault(gid, f'<path id="{gid}" d="{d}"/>')
            ux = round(gx / k)
            uses.append(f'<use href="#{gid}"' + (f' x="{ux}"' if ux else "") + "/>")
        op = f' fill-opacity="{opacity}"' if opacity is not None else ""
        self.add(f'<g fill="{fill}"{op} transform="translate({fmt(x)} {fmt(y)}) '
                 f'scale({k:.5f} {-k:.5f})">{"".join(uses)}</g>')
        return width

    def runs(self, font: Font, parts, x: float, y: float, size: float) -> float:
        """Draws [(text, color)] one after another; returns the end x."""
        for s, color in parts:
            x += self.text(font, s, x, y, size, color)
        return x

    def render(self) -> str:
        title = escape(self.title)
        css = f"<style>{''.join(self.css)}</style>" if self.css else ""
        defs = f"<defs>{''.join(self.defs.values())}</defs>" if self.defs else ""
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{fmt(self.w)}" height="{fmt(self.h)}" '
                f'viewBox="0 0 {fmt(self.w)} {fmt(self.h)}" role="img" aria-label="{title}">'
                f'<title>{title}</title>{css}{defs}{"".join(self.parts)}</svg>\n')


# ── Shared pieces ────────────────────────────────────────────────────────────

def panel(svg: Svg, t, x: float, y: float, w: float, h: float, r: float = 16, fill: str | None = None):
    svg.add(f'<rect x="{fmt(x + .5)}" y="{fmt(y + .5)}" width="{fmt(w - 1)}" height="{fmt(h - 1)}" '
            f'rx="{fmt(r)}" fill="{fill or t.panel}" stroke="{t.line}"/>')


def status_dot(svg: Svg, x: float, y: float, color: str):
    svg.animate()
    svg.add(f'<circle class="pulse" cx="{fmt(x)}" cy="{fmt(y)}" r="3" fill="{color}"/>'
            f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="3" fill="{color}"/>')


def eyebrow(svg: Svg, text: str, x: float, cy: float, size: float, color: str) -> float:
    font = F["mono-medium"]
    return svg.text(font, text.upper(), x, cy + font.cap(size) / 2, size, color, tracking=.18)


def arrow(svg: Svg, x: float, y: float, s: float, color: str, width: float = 1.4):
    svg.add(f'<path d="M{fmt(x)} {fmt(y + s)}L{fmt(x + s)} {fmt(y)}M{fmt(x + s * .3)} {fmt(y)}H{fmt(x + s)}'
            f'V{fmt(y + s * .7)}" fill="none" stroke="{color}" stroke-width="{width}" '
            f'stroke-linecap="round" stroke-linejoin="round"/>')


def icon_path(slug: str) -> str:
    return re.search(r' d="([^"]+)"', fetch(f"{ICONS}{slug}.svg").read_text()).group(1)


def logo(svg: Svg, slug: str, x: float, y: float, size: float, color: str, bg: str):
    """A 24-unit logo scaled to size px with its top-left corner at x, y."""
    k = size / 24
    g = f'<g transform="translate({fmt(x)} {fmt(y)}) scale({k:.4f})">'
    if slug == "csharp":
        svg.add(g + f'<path d="M12 1.5 21.1 6.75v10.5L12 22.5 2.9 17.25V6.75Z" fill="{color}"/>'
                f'<path d="M10.3 7.8 9.3 16.2M14.7 7.8 13.7 16.2M7.6 10.5h9M7.3 13.5h9" stroke="{bg}" '
                f'stroke-width="1.7" stroke-linecap="round"/></g>')
    elif slug == "aws":
        svg.add(g + f'<path d="M3 16c5.3 3.7 12.7 3.7 18 0M17.5 14.4l3.6 1.6-1 3.6" fill="none" '
                f'stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></g>')
        svg.text(F["sans-semibold"], "aws", x + size / 2, y + size * .52, size * .52, color, anchor="middle")
    elif slug == "linkedin":
        svg.add(g + f'<rect width="24" height="24" rx="4.5" fill="{color}"/></g>')
        svg.text(F["sans-semibold"], "in", x + size * .53, y + size * .79, size * .74, bg, anchor="middle")
    elif slug == "globe":
        svg.add(g + f'<g fill="none" stroke="{color}" stroke-width="1.8"><circle cx="12" cy="12" r="9.5"/>'
                f'<ellipse cx="12" cy="12" rx="4.2" ry="9.5"/><path d="M2.5 12h19M4 7.2h16M4 16.8h16"/></g></g>')
    else:
        svg.add(g + f'<path d="{icon_path(slug)}" fill="{color}"/></g>')


def chip(svg: Svg, t, x: float, cy: float, label: str, font: Font, size: float, h: float, pad: float,
         slug: str | None = None, logo_size: float = 0, gap: float = 0) -> float:
    lw = logo_size + gap if slug else 0
    w = pad * 2 + lw + font.width(label, size)
    svg.add(f'<rect x="{fmt(x + .5)}" y="{fmt(cy - h / 2 + .5)}" width="{fmt(w - 1)}" height="{fmt(h - 1)}" '
            f'rx="{fmt((h - 1) / 2)}" fill="{t.chip}" stroke="{t.line}"/>')
    if slug:
        logo(svg, slug, x + pad, cy - logo_size / 2, logo_size, t.ink2, t.chip)
    svg.text(font, label, x + pad + lw, cy + font.cap(size) / 2, size, t.ink2)
    return w


def chip_row(svg: Svg, t, x: float, cy: float, labels, font: Font, size: float, h: float, pad: float,
             gap: float = 6) -> float:
    for label in labels:
        x += chip(svg, t, x, cy, label, font, size, h, pad) + gap
    return x - gap


def ellipse_d(rx: float, ry: float) -> str:
    # Starts at the right end and runs counterclockwise on screen (prograde, seen from the north).
    return f"M{rx} 0A{rx} {ry} 0 1 0 {-rx} 0A{rx} {ry} 0 1 0 {rx} 0"


def glow_filter(svg: Svg):
    svg.define("glow", '<filter id="glow" x="-300%" y="-300%" width="700%" height="700%">'
                       '<feGaussianBlur stdDeviation="2.2" result="b"/><feMerge><feMergeNode in="b"/>'
                       '<feMergeNode in="SourceGraphic"/></feMerge></filter>')


# ── Banner ───────────────────────────────────────────────────────────────────

def banner(t, mode: str) -> str:
    c = CONTENT
    night = mode == "night"
    W, H = 840, 300
    cx, cy, tilt = 628, 140, -14
    x0 = 48
    svg = Svg(W, H, f"{c['name']}: {c['role']}. {c['fields']}.")
    # Boxes around the words, so no star lands on a letter.
    keep_out = [
        (x0 - 8, 48, x0 + 24 + F["mono-medium"].width(c["role"].upper(), 11, .18), 76),
        (x0 - 8, 76, x0 + 8 + F["serif"].width(c["name"], 84), 172),
        (x0 - 8, 166, x0 + 10 + sum(F["serif-italic"].width(s, 25) for s in c[mode]), 204),
        (x0 - 8, 236, x0 + 8 + F["mono"].width(c["fields"].upper(), 10, .18), 262),
        (W - x0 - 8 - legend_width(), 236, W - x0 + 8, 262),
    ]
    svg.define("frame", f'<clipPath id="frame"><rect width="{W}" height="{H}" rx="20"/></clipPath>')
    svg.add('<g clip-path="url(#frame)">')

    if night:
        svg.define("sky", '<linearGradient id="sky" x1="0" y1="0" x2="1" y2="1">'
                          '<stop offset="0" stop-color="#0b121a"/><stop offset="1" stop-color="#030508"/>'
                          '</linearGradient>')
        svg.define("nebula", f'<radialGradient id="nebula" gradientUnits="userSpaceOnUse" cx="{cx}" cy="{cy}" '
                             f'r="300"><stop offset="0" stop-color="{t.accent}" stop-opacity=".13"/>'
                             f'<stop offset="1" stop-color="{t.accent}" stop-opacity="0"/></radialGradient>')
        svg.add(f'<rect width="{W}" height="{H}" fill="url(#sky)"/><rect width="{W}" height="{H}" fill="url(#nebula)"/>')
        svg.animate()
        rng = random.Random(1957)
        stars = []
        for _ in range(150):
            x, y = rng.uniform(0, W), rng.uniform(0, H)
            if any(a <= x <= b and top <= y <= bottom for a, top, b, bottom in keep_out):
                continue
            if x < 430 and 40 < y < 270 and rng.random() < .6:
                continue  # keep the sky around the words quieter
            r = rng.choice([.45, .55, .6, .7, .8, .9, 1.1, 1.4])
            op = round(rng.uniform(.25, .9), 2)
            twinkle = f' class="tw" style="animation-delay:-{rng.uniform(0, 5):.1f}s"' if rng.random() < .2 else ""
            stars.append(f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="{r}" fill-opacity="{op}"{twinkle}/>')
        svg.add(f'<g fill="#ffffff">{"".join(stars)}</g>')
    else:
        svg.add(f'<rect width="{W}" height="{H}" fill="{t.canvas}"/>')
        svg.define("grid", f'<pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">'
                           f'<path d="M20 0H0V20" fill="none" stroke="{t.ink}" stroke-opacity=".06"/></pattern>')
        svg.define("grid5", f'<pattern id="grid5" width="100" height="100" patternUnits="userSpaceOnUse" x="28">'
                            f'<path d="M100 0H0V100" fill="none" stroke="{t.ink}" stroke-opacity=".07"/></pattern>')
        svg.define("fade", f'<radialGradient id="fade" gradientUnits="userSpaceOnUse" cx="{cx}" cy="{cy}" r="330">'
                           '<stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/>'
                           '</radialGradient>')
        svg.define("gridmask", f'<mask id="gridmask"><rect width="{W}" height="{H}" fill="url(#fade)"/></mask>')
        svg.add(f'<g mask="url(#gridmask)"><rect width="{W}" height="{H}" fill="url(#grid)"/>'
                f'<rect width="{W}" height="{H}" fill="url(#grid5)"/></g>')

    orbit_system(svg, t, night, cx, cy, tilt)
    svg.add("</g>")
    svg.add(f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="19.5" fill="none" stroke="{t.line}"/>')

    # Words
    status_dot(svg, x0 + 4, 62, t.accent)
    eyebrow(svg, c["role"], x0 + 16, 62, 11, t.ink2)
    serif = F["serif"]
    svg.text(serif, c["name"], x0 - serif.lsb(c["name"], 84), 148, 84, t.ink)
    lead, stress, tail = c[mode]
    svg.runs(F["serif-italic"], [(lead, t.muted), (stress, t.ink), (tail, t.muted)], x0, 190, 25)
    svg.text(F["mono"], c["fields"].upper(), x0, 252, 10, t.muted, tracking=.18)
    legend(svg, t, night, W - x0, 252)
    return svg.render()


def orbit_system(svg: Svg, t, night: bool, cx: float, cy: float, tilt: float):
    line = t.accent if night else t.ink
    svg.add(f'<g transform="translate({cx} {cy}) rotate({tilt})">')
    for i, (_, rx, ry, _, _, dash) in enumerate(ORBITS):
        op = (.34, .27, .21)[i] if night else (.55, .45, .38)[i]
        da = f' stroke-dasharray="{dash}"' if dash else ""
        svg.add(f'<path d="{ellipse_d(rx, ry)}" fill="none" stroke="{line}" stroke-opacity="{op}"{da}/>')

    # The planet, its equator in the orbital plane.
    svg.define("globe", '<clipPath id="globe"><circle r="16"/></clipPath>')
    if night:
        svg.define("atmo", f'<radialGradient id="atmo"><stop offset=".45" stop-color="{t.accent}" stop-opacity=".22"/>'
                           f'<stop offset="1" stop-color="{t.accent}" stop-opacity="0"/></radialGradient>')
        svg.define("planet", '<radialGradient id="planet" cx=".36" cy=".3" r=".8"><stop offset="0" stop-color="#21384a"/>'
                             '<stop offset="1" stop-color="#060b10"/></radialGradient>')
        svg.add(f'<circle r="34" fill="url(#atmo)"/><circle r="16" fill="url(#planet)"/>')
    else:
        svg.add(f'<path d="M0-30V30M-30 0h8M22 0h8" stroke="{t.ink}" stroke-opacity=".35" stroke-dasharray="2 3"/>'
                f'<circle r="16" fill="{t.well}"/>')
    svg.add(f'<g clip-path="url(#globe)" fill="none" stroke="{line}" stroke-opacity="{.25 if night else .3}" '
            f'stroke-width=".8"><ellipse rx="7.5" ry="16"/><ellipse rx="13.5" ry="16"/>'
            f'<path d="M0-16V16M-16 0H16M-16-8H16M-16 8H16"/></g>')
    svg.add(f'<circle r="16" fill="none" stroke="{line}" stroke-opacity="{.6 if night else .9}" '
            f'stroke-width="{1 if night else 1.1}"/>')

    if night:
        glow_filter(svg)
    for i, (_, rx, ry, _, dur, _) in enumerate(ORBITS):
        d = ellipse_d(rx, ry)
        begin = f"-{dur * (.12, .55, .8)[i]:.2f}s"
        # A fading trail: three dashes of falling opacity that all end at the satellite.
        for length, op in ((120, .12), (64, .26), (26, .6)):
            svg.add(f'<path d="{d}" pathLength="1000" fill="none" stroke="{t.stroke}" stroke-opacity="{op}" '
                    f'stroke-width="1.6" stroke-linecap="round" stroke-dasharray="{length} {1000 - length}" '
                    f'stroke-dashoffset="{length}"><animate attributeName="stroke-dashoffset" '
                    f'values="{length};{length - 1000}" dur="{dur}s" begin="{begin}" repeatCount="indefinite"/></path>')
        if night:
            dot = f'<circle r="2.3" fill="{t.satellite}" filter="url(#glow)"/>'
        else:
            dot = f'<circle r="2.7" fill="{t.well}" stroke="{t.satellite}" stroke-width="1.2"/>'
        svg.add(f'<g>{dot}<animateMotion dur="{dur}s" begin="{begin}" repeatCount="indefinite" path="{d}"/></g>')
    svg.add("</g>")


def legend_width() -> float:
    return sum(F["mono"].width(f"{name} {period}", 9.5, .06) + 42 for name, _, _, period, _, _ in ORBITS) - 20


def legend(svg: Svg, t, night: bool, right: float, baseline: float):
    font, size = F["mono"], 9.5
    x = right
    for name, _, _, period, _, dash in reversed(ORBITS):
        label = f"{name} {period}"
        x -= font.width(label, size, .06)
        svg.text(font, label, x, baseline, size, t.muted, tracking=.06)
        ly = baseline - font.cap(size) / 2
        da = f' stroke-dasharray="{dash}"' if dash else ""
        svg.add(f'<path d="M{fmt(x - 22)} {fmt(ly)}h15" stroke="{t.accent if night else t.ink}" '
                f'stroke-opacity=".75"{da}/>')
        x -= 22 + 20


# ── Section headers ──────────────────────────────────────────────────────────

def section_header(n: int, label: str, t) -> str:
    num_font, serif = F["mono-medium"], F["serif"]
    size, baseline = 30, 33
    num = f"{n:02d}"
    num_w = num_font.width(num, 11, .08)
    rule_x = num_w + 9
    label_x = rule_x + 26
    w = label_x + serif.width(label, size) + 2
    svg = Svg(math.ceil(w), 44, label)
    mid = baseline - serif.cap(size) / 2
    svg.text(num_font, num, 0, mid + num_font.cap(11) / 2, 11, t.accent, tracking=.08)
    svg.add(f'<path d="M{fmt(rule_x)} {fmt(mid)}h17" stroke="{t.accent}" stroke-opacity=".55"/>')
    svg.text(serif, label, label_x - serif.lsb(label, size), baseline, size, t.ink)
    return svg.render()


# ── Stack ────────────────────────────────────────────────────────────────────

def stack(t) -> str:
    rows = CONTENT["stack"]
    W, top, pitch, h = 840, 24, 46, 30
    H = top * 2 + pitch * (len(rows) - 1) + h
    svg = Svg(W, H, "Stack. " + " ".join(f"{group}: {', '.join(items)}." for group, items in rows))
    panel(svg, t, 0, 0, W, H)
    font, size = F["sans-medium"], 12.5
    for i, (group, items) in enumerate(rows):
        cy = top + h / 2 + pitch * i
        if i:
            svg.add(f'<path d="M28 {fmt(cy - pitch / 2)}H{W - 28}" stroke="{t.line}" stroke-opacity=".7"/>')
        eyebrow(svg, group, 28, cy, 9.5, t.muted)
        x = 172
        for item in items:
            x += chip(svg, t, x, cy, item, font, size, h, 11, LOGOS.get(item), 14, 7) + 8
    return svg.render()


# ── Featured project ─────────────────────────────────────────────────────────

def ground_track(lon0: float, inclination: float = 51.6, period: float = 92.68, n: int = 180):
    """(lon, lat) of one circular orbit's ground track, with the Earth turning underneath."""
    i = math.radians(inclination)
    spin = 360 / 1436.07  # degrees per minute (sidereal day)
    points, prev, turns = [], None, 0
    for k in range(n + 1):
        u = 2 * math.pi * k / n
        lon = math.degrees(math.atan2(math.cos(i) * math.sin(u), math.cos(u)))
        if prev is not None and lon < prev - 180:
            turns += 360
        prev = lon
        lat = math.degrees(math.asin(math.sin(i) * math.sin(u)))
        points.append((lon0 + lon + turns - spin * period * k / n, lat))
    return points


def polyline(points) -> str:
    return "M" + "L".join(f"{fmt(x)} {fmt(y)}" for x, y in points)


def featured(t, mode: str) -> str:
    p = CONTENT["featured"]
    night = mode == "night"
    # Map: an equirectangular Earth with the ISS ground track (i 51.6°, T 92.7 min).
    mx, my, mw, mh = 436.0, 32.0, 372.0, 186.0
    x0, col = 32, 384
    taglines = wrap(F["sans-medium"], p["tagline"], 15, col)
    descriptions = wrap(F["sans"], p["description"], 13, col)
    y_tag = my + 98
    y_desc = y_tag + 21 * (len(taglines) - 1) + 26
    # The chips sit on the map's bottom edge unless the words run longer than the map.
    chips_cy = max(y_desc + 20 * (len(descriptions) - 1) + 28, my + mh - 12)
    W, H = 840, max(my + mh, chips_cy + 12) + 32
    svg = Svg(W, H, alt_for(p))
    panel(svg, t, 0, 0, W, H)

    def at(lon: float, lat: float):
        return mx + (lon + 180) / 360 * mw, my + (90 - lat) / 180 * mh

    svg.define("map", f'<clipPath id="map"><rect x="{fmt(mx)}" y="{fmt(my)}" width="{fmt(mw)}" '
                      f'height="{fmt(mh)}" rx="10"/></clipPath>')
    svg.add(f'<rect x="{fmt(mx)}" y="{fmt(my)}" width="{fmt(mw)}" height="{fmt(mh)}" rx="10" fill="{t.well}"/>')
    svg.add('<g clip-path="url(#map)">')
    # Night side (sun over 14°N): south of the terminator.
    decl, sun_lon = math.radians(14), 30
    term = [at(lon, math.degrees(math.atan(-math.cos(math.radians(lon - sun_lon)) / math.tan(decl))))
            for lon in range(-180, 181, 5)]
    svg.add(f'<path d="{polyline(term + [at(180, -90), at(-180, -90)])}Z" fill="{"#000" if night else t.ink}" '
            f'fill-opacity="{.32 if night else .045}"/>')
    grid = t.accent if night else t.ink
    lines = "".join(f"M{fmt(at(lon, 0)[0])} {fmt(my)}V{fmt(my + mh)}" for lon in range(-150, 180, 30))
    lines += "".join(f"M{fmt(mx)} {fmt(at(0, lat)[1])}H{fmt(mx + mw)}" for lat in (-60, -30, 30, 60))
    svg.add(f'<path d="{lines}" fill="none" stroke="{grid}" stroke-opacity="{.09 if night else .08}"/>')
    svg.add(f'<path d="M{fmt(mx)} {fmt(at(0, 0)[1])}H{fmt(mx + mw)}" stroke="{grid}" '
            f'stroke-opacity="{.22 if night else .2}"/>')
    shift = 360 / 1436.07 * 92.68  # how far west each pass lands
    previous = [at(*pt) for pt in ground_track(-168 + shift)]
    svg.add(f'<path d="{polyline(previous)}" fill="none" stroke="{t.stroke}" stroke-opacity=".38" '
            f'stroke-dasharray="2 3"/>')
    current = [at(*pt) for pt in ground_track(-168)]
    svg.add(f'<path id="track" d="{polyline(current)}" fill="none" stroke="{t.stroke}" stroke-width="1.5" '
            f'stroke-opacity=".9"/>')
    if night:
        glow_filter(svg)
        dot = f'<circle r="3" fill="{t.satellite}" filter="url(#glow)"/>'
    else:
        dot = f'<circle r="3.2" fill="{t.well}" stroke="{t.satellite}" stroke-width="1.3"/>'
    svg.add(f'<g><circle r="16" fill="{t.accent}" fill-opacity=".1" stroke="{t.accent}" stroke-opacity=".45" '
            f'stroke-width=".8"/>{dot}<animateMotion dur="16s" begin="-5s" repeatCount="indefinite">'
            f'<mpath href="#track"/></animateMotion></g>')
    svg.add("</g>")
    svg.add(f'<rect x="{fmt(mx + .5)}" y="{fmt(my + .5)}" width="{fmt(mw - 1)}" height="{fmt(mh - 1)}" rx="9.5" '
            f'fill="none" stroke="{t.line}"/>')
    # Map key, bottom right, below the southernmost point of the track (51.6°S).
    cap, caption = F["mono"], "ISS ground track · i 51.6° · T 92.7 min"
    cw = cap.width(caption, 9, .04)
    svg.add(f'<rect x="{fmt(mx + mw - cw - 22)}" y="{fmt(my + mh - 26)}" width="{fmt(cw + 14)}" height="16" rx="8" '
            f'fill="{t.well}" fill-opacity=".85"/>')
    svg.text(cap, caption, mx + mw - 15, my + mh - 18 + cap.cap(9) / 2, 9, t.muted, anchor="end", tracking=.04)

    # Words
    status_dot(svg, x0 + 4, my + 5, t.accent)
    eyebrow(svg, p["label"], x0 + 15, my + 5, 10, t.accent)
    serif = F["serif"]
    svg.text(serif, p["name"], x0 - serif.lsb(p["name"], 58), my + 68, 58, t.ink)
    for i, line in enumerate(taglines):
        svg.text(F["sans-medium"], line, x0, y_tag + 21 * i, 15, t.ink)
    for i, line in enumerate(descriptions):
        svg.text(F["sans"], line, x0, y_desc + 20 * i, 13, t.muted)
    chip_row(svg, t, x0, chips_cy, p["stack"], F["mono"], 10, 24, 10)
    return svg.render()


# ── Project cards ────────────────────────────────────────────────────────────

CARD_W, CARD_GAP, CARD_PAD = 420, 20, 24


def card_text(p):
    inner = CARD_W - CARD_GAP / 2 - CARD_PAD * 2
    taglines = wrap(F["sans-medium"], p["tagline"], 13.5, inner)
    descriptions = wrap(F["sans"], p["description"], 12.5, inner)
    y_tag = 124
    y_desc = y_tag + 19 * (len(taglines) - 1) + 23
    bottom = y_desc + 18 * (len(descriptions) - 1)
    return taglines, y_tag, descriptions, y_desc, bottom


def card_height() -> float:
    return max(card_text(p)[4] for p in CONTENT["projects"]) + 24 + 22 + CARD_PAD


def card_icon(svg: Svg, kind: str, x: float, y: float, t):
    line = f'fill="none" stroke="{t.ink2}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"'
    lit = f'fill="{t.accent}" fill-opacity=".16" stroke="{t.accent}" stroke-width="1.5" stroke-linejoin="round"'
    if kind == "tenants":  # rows kept apart by Row Level Security
        body = (f'<rect x="4" y="12" width="24" height="8" {lit}/>'
                f'<rect x="4" y="4" width="24" height="24" rx="5" {line}/>')
    elif kind == "terminal":
        body = (f'<rect x="3" y="6" width="26" height="20" rx="4" {line}/>'
                f'<path d="M8.5 12.5 12 16l-3.5 3.5M14.5 19.5H20" fill="none" stroke="{t.accent}" '
                f'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>')
    elif kind == "graph":
        nodes = [(7, 8), (25, 6), (7, 26), (26, 25)]
        body = (f'<path d="M7 8 16 16.5M25 6 16 16.5M7 26 16 16.5M26 25 16 16.5M25 6 26 25" {line} '
                f'stroke-opacity=".7"/>'
                + "".join(f'<circle cx="{a}" cy="{b}" r="2.8" fill="{t.panel}" stroke="{t.ink2}" '
                          f'stroke-width="1.5"/>' for a, b in nodes)
                + f'<circle cx="16" cy="16.5" r="3.8" fill="{t.accent}"/>')
    else:  # panes
        body = (f'<rect x="3" y="10.5" width="11" height="16.5" {lit}/>'
                f'<rect x="3" y="5" width="26" height="22" rx="4" {line}/>'
                f'<path d="M3 10.5H29M14 10.5V27M14 18.75H29" {line}/>')
    svg.add(f'<g transform="translate({fmt(x)} {fmt(y)})">{body}</g>')


def card(p, t, side: str, H: float) -> str:
    svg = Svg(CARD_W, H, alt_for(p))
    x0 = 0 if side == "left" else CARD_GAP / 2
    w = CARD_W - CARD_GAP / 2
    panel(svg, t, x0, 0, w, H)
    left = x0 + CARD_PAD
    card_icon(svg, p["icon"], left, 22, t)
    eyebrow(svg, p["label"], left + 44, 38, 9.5, t.muted)
    arrow(svg, x0 + w - CARD_PAD - 10, 33, 10, t.faint)
    serif = F["serif"]
    svg.text(serif, p["name"], left - serif.lsb(p["name"], 32), 98, 32, t.ink)
    taglines, y_tag, descriptions, y_desc, _ = card_text(p)
    for i, line in enumerate(taglines):
        svg.text(F["sans-medium"], line, left, y_tag + 19 * i, 13.5, t.ink)
    for i, line in enumerate(descriptions):
        svg.text(F["sans"], line, left, y_desc + 18 * i, 12.5, t.muted)
    chip_row(svg, t, left, H - CARD_PAD - 11, p["stack"], F["mono"], 10, 22, 9)
    return svg.render()


# ── Currently learning ───────────────────────────────────────────────────────

def learning(t) -> str:
    topics = CONTENT["learning"]
    W, cols, pad, row_h = 840, 2, 8, 40
    rows = math.ceil(len(topics) / cols)
    H = pad * 2 + row_h * rows
    svg = Svg(W, H, "Currently learning: " + ", ".join(topics) + ".")
    panel(svg, t, 0, 0, W, H)
    for r in range(1, rows):
        svg.add(f'<path d="M28 {pad + row_h * r}H{W - 28}" stroke="{t.line}" stroke-opacity=".7"/>')
    font, size, col_w = F["sans-medium"], 13.5, (W - 56) / cols
    for i, topic in enumerate(topics):
        x, cy = 28 + (i // rows) * col_w, pad + row_h * (i % rows + .5)
        svg.add(f'<circle cx="{fmt(x + 5)}" cy="{fmt(cy)}" r="4.5" fill="none" stroke="{t.accent}" '
                f'stroke-opacity=".55"/><circle cx="{fmt(x + 5)}" cy="{fmt(cy)}" r="1.7" fill="{t.accent}"/>')
        svg.text(font, topic, x + 21, cy + font.cap(size) / 2, size, t.ink2)
    return svg.render()


# ── Connect ──────────────────────────────────────────────────────────────────

def button(label: str, slug: str, t, mode: str, primary: bool) -> str:
    font, size, h, pad, icon, gap = F["sans-medium"], 14, 42, 18, 16, 9
    w = pad * 2 + icon + gap + font.width(label, size) + 12 + 9
    svg = Svg(math.ceil(w), h, label)
    if primary:
        fill = t.ink if mode == "day" else t.accent
        color = "#ffffff" if mode == "day" else "#04140b"
        svg.add(f'<rect width="{fmt(math.ceil(w))}" height="{h}" rx="{h / 2}" fill="{fill}"/>')
    else:
        fill, color = t.panel, t.ink
        svg.add(f'<rect x=".5" y=".5" width="{fmt(math.ceil(w) - 1)}" height="{h - 1}" rx="{(h - 1) / 2}" '
                f'fill="{fill}" stroke="{t.line}"/>')
    logo(svg, slug, pad, (h - icon) / 2, icon, color, fill)
    end = svg.text(font, label, pad + icon + gap, h / 2 + font.cap(size) / 2, size, color) + pad + icon + gap
    arrow(svg, end + 12, h / 2 - 4.5, 9, color, 1.5)
    return svg.render()


def footer(t, mode: str) -> str:
    c = CONTENT
    W, H, cx = 840, 132, 420
    svg = Svg(W, H, f"{''.join(c['day'])} {''.join(c['night'])}")
    # userSpaceOnUse: a gradient sized to a flat line's bounding box (zero height) never renders.
    svg.define("horizon", f'<linearGradient id="horizon" gradientUnits="userSpaceOnUse" x1="{cx - 90}" x2="{cx + 90}">'
                          f'<stop offset="0" stop-color="{t.ink}" stop-opacity="0"/>'
                          f'<stop offset=".5" stop-color="{t.ink}" stop-opacity=".45"/>'
                          f'<stop offset="1" stop-color="{t.ink}" stop-opacity="0"/></linearGradient>')
    svg.add(f'<path d="M{cx - 90} 54h180" stroke="url(#horizon)"/>')
    if mode == "day":
        rays = "".join(
            f"M{fmt(cx + 17 * math.cos(a))} {fmt(54 - 17 * math.sin(a))}"
            f"L{fmt(cx + 23 * math.cos(a))} {fmt(54 - 23 * math.sin(a))}"
            for a in (math.radians(d) for d in (20, 55, 90, 125, 160)))
        svg.add(f'<path d="M{cx - 11} 54a11 11 0 0 1 22 0" fill="{t.canvas}" stroke="{t.ink}" stroke-width="1.2"/>'
                f'<path d="{rays}" stroke="{t.accent}" stroke-width="1.4" stroke-linecap="round"/>')
    else:
        svg.define("moon", f'<mask id="moon"><rect width="{W}" height="{H}" fill="#fff"/>'
                           f'<circle cx="{cx + 5}" cy="29" r="9.5" fill="#000"/></mask>')
        svg.animate()
        sparkle = "M0-4.5Q.6-.6 4.5 0Q.6 .6 0 4.5Q-.6 .6-4.5 0Q-.6-.6 0-4.5Z"
        stars = "".join(f'<path class="tw" style="animation-delay:-{d}s" transform="translate({x} {y}) scale({s})" '
                        f'd="{sparkle}"/>' for x, y, s, d in ((cx - 38, 26, .8, 1.2), (cx + 32, 18, .6, 3.1),
                                                               (cx + 44, 42, .9, 2.2), (cx - 24, 44, .5, 4)))
        svg.add(f'<circle cx="{cx}" cy="33" r="11" fill="{t.ink2}" mask="url(#moon)"/>'
                f'<g fill="{t.accent}">{stars}</g>')
    italic, size = F["serif-italic"], 22
    day, night = "".join(c["day"]), "".join(c["night"])
    lit, dim = (t.ink, t.faint)
    parts = [(day + "  ", lit if mode == "day" else dim), (night, lit if mode == "night" else dim)]
    total = sum(italic.width(s, size) for s, _ in parts)
    svg.runs(italic, parts, cx - total / 2, 100, size)
    return svg.render()


# ── README ───────────────────────────────────────────────────────────────────

def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def alt_for(p) -> str:
    return f"{p['name']}: {p['tagline']}. {p['description']} Built with {', '.join(p['stack'])}."


def asset_url(name: str) -> str:
    # Absolute, because GitHub doesn't resolve relative paths in a <source srcset>.
    user = CONTENT["username"]
    return f"https://raw.githubusercontent.com/{user}/{user}/main/assets/{name}.svg"


def picture(name: str, alt: str, width: str | None = None, href: str | None = None) -> str:
    w = f' width="{width}"' if width else ""
    pic = (f'<picture><source media="(prefers-color-scheme: dark)" srcset="{asset_url(name + "-night")}">'
           f'<img alt="{escape(alt)}" src="{asset_url(name + "-day")}"{w}></picture>')
    return f'<a href="{href}">{pic}</a>' if href else pic


def themed_url(kind: str, t) -> str:
    def h(color: str) -> str:
        return color.lstrip("#")
    user = CONTENT["username"]
    # Sizes: stats 495×189 and languages 495×190 sit side by side at 49% each; the streak
    # card is twice as wide (1010×195), so at 98.5% its text renders at the same scale.
    if kind == "streak":
        return (f"https://streak-stats.demolab.com/?user={user}&card_width=1010&background={h(t.panel)}"
                f"&border={h(t.line)}&stroke={h(t.line)}&ring={h(t.accent)}&fire={h(t.accent)}"
                f"&currStreakNum={h(t.ink)}&sideNums={h(t.ink)}&currStreakLabel={h(t.accent)}"
                f"&sideLabels={h(t.muted)}&dates={h(t.faint)}&border_radius=16")
    colors = (f"&bg_color={h(t.panel)}&border_color={h(t.line)}&title_color={h(t.ink)}"
              f"&text_color={h(t.muted)}&icon_color={h(t.accent)}&ring_color={h(t.accent)}&border_radius=16")
    if kind == "langs":
        return (f"https://github-readme-stats.vercel.app/api/top-langs/?username={user}&layout=compact"
                f"&langs_count=8&card_width=495&custom_title=Most%20used%20languages{colors}")
    return (f"https://github-readme-stats.vercel.app/api?username={user}&show_icons=true&card_width=495"
            f"&line_height=24&custom_title=GitHub%20stats{colors}")


def live_picture(kind: str, alt: str, width: str) -> str:
    day, night = (themed_url(kind, SimpleNamespace(**THEMES[m])) for m in ("day", "night"))
    return (f'<picture><source media="(prefers-color-scheme: dark)" srcset="{escape(night)}">'
            f'<img alt="{alt}" src="{escape(day)}" width="{width}"></picture>')


def readme() -> str:
    c = CONTENT
    out = ["<!-- Generated by build.py: edit CONTENT there, then run `python3 build.py`. -->", ""]

    def section(n: int):
        out.extend(["<br>", "", picture(f"section-{n}", SECTIONS[n - 1]), ""])

    out += [picture("banner", f"{c['name']}: {c['role']}. {c['fields']}.", "100%", c["portfolio"][1]), ""]
    links = " &nbsp;·&nbsp; ".join(f'<a href="{url}"><b>{name}</b></a>' for name, url in c["links"])
    out += [f'<p align="center">{links}</p>', ""]

    section(1)
    out += [f"- **{label}** — {text}" for label, text in c["about"]] + [""]

    section(2)
    out += [picture("stack", "Stack. " + " ".join(f"{g}: {', '.join(items)}." for g, items in c["stack"]),
                    "100%"), ""]

    section(3)
    f = c["featured"]
    out += [picture("featured", alt_for(f), "100%", f["url"]), ""]
    cards = [picture(f"project-{slug(p['name'])}", alt_for(p), "50%", p["url"]) for p in c["projects"]]
    for i in range(0, len(cards), 2):
        out += ["".join(cards[i:i + 2]), ""]  # no whitespace: the gap is drawn inside the cards

    section(4)
    out += [f'<p align="center">{live_picture("stats", "GitHub stats", "49%")} '
            f'{live_picture("langs", "Most used languages", "49%")}</p>', "",
            f'<p align="center">{live_picture("streak", "Contribution streak", "98.5%")}</p>', ""]

    section(5)
    out += [picture("learning", "Currently learning: " + ", ".join(c["learning"]) + ".", "100%"), ""]

    section(6)
    portfolio, linkedin = c["portfolio"], c["linkedin"]
    out += [f'<p align="center"><a href="{portfolio[1]}">{picture("button-portfolio", portfolio[0])}</a>'
            f'&nbsp;&nbsp;<a href="{linkedin[1]}">{picture("button-linkedin", linkedin[0])}</a></p>', "",
            picture("footer", f"{''.join(c['day'])} {''.join(c['night'])}", "100%"), ""]
    return "\n".join(out)


# ── Build ────────────────────────────────────────────────────────────────────

def main():
    for key, path in FONT_FILES.items():
        F[key] = Font(key, fetch(path))
    ASSETS.mkdir(exist_ok=True)
    c = CONTENT
    H = card_height()
    sizes = []
    for mode, values in THEMES.items():
        t = SimpleNamespace(**values)
        files = {
            "banner": banner(t, mode),
            "stack": stack(t),
            "featured": featured(t, mode),
            "learning": learning(t),
            "button-portfolio": button(c["portfolio"][0], "globe", t, mode, primary=True),
            "button-linkedin": button(c["linkedin"][0], "linkedin", t, mode, primary=False),
            "footer": footer(t, mode),
        }
        for n, label in enumerate(SECTIONS, 1):
            files[f"section-{n}"] = section_header(n, label, t)
        for i, p in enumerate(c["projects"]):
            files[f"project-{slug(p['name'])}"] = card(p, t, "left" if i % 2 == 0 else "right", H)
        for name, svg in files.items():
            path = ASSETS / f"{name}-{mode}.svg"
            path.write_text(svg, encoding="utf-8")
            sizes.append(len(svg))
    (ROOT / "README.md").write_text(readme(), encoding="utf-8")
    print(f"Wrote README.md and {len(sizes)} images to assets/ ({sum(sizes) // 1024} KB).")


if __name__ == "__main__":
    main()
