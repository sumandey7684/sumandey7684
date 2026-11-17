#!/usr/bin/env python3
"""Render the animated SVG profile cards."""

from __future__ import annotations

import base64
import html
import json
import os
import re
import shutil
import tempfile
from pathlib import Path

from fontTools.subset import Options, Subsetter
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
FONTS = ROOT / "fonts"
OUT = ROOT / ("cards-preview" if os.environ.get("STATIC") == "1" else "cards")
STATIC = os.environ.get("STATIC") == "1"
WIDTH = 880
BG = "#0b0b0d"
PANEL = "#121216"
TEXT = "#f4f1ed"
MUTED = "#9c9893"
LINE = "#2b292a"
ACCENT = "#e3a34f"
ACCENT_DARK = "#765126"
GREEN = "#9abf78"

REPOS = [
    {
        "name": "Podcast-buddy",
        "slug": "Podcast-buddy",
        "language": "Python",
    }
]


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def font_sources() -> dict[str, Path]:
    return {
        "instrument": FONTS / "InstrumentSerif-Regular.source.woff",
        "instrument-italic": FONTS / "InstrumentSerif-Italic.source.woff",
        "geist": FONTS / "Geist-400.source.woff",
        "geist-semibold": FONTS / "Geist-600.source.woff",
        "mono": FONTS / "GeistMono-400.source.woff",
    }


def subset_fonts(text: str, families: tuple[str, ...] | None = None) -> dict[str, str]:
    unicodes = {ord(char) for char in text if ord(char) <= 0xFFFF}
    result = {}
    with tempfile.TemporaryDirectory() as directory:
        sources = font_sources()
        for family in families or tuple(sources):
            source = sources[family]
            if not source.exists():
                raise FileNotFoundError(f"Missing font source: {source}")
            output = Path(directory) / f"{family}.woff"
            font = TTFont(source)
            options = Options()
            options.flavor = "woff"
            options.layout_features = ["*"]
            options.name_IDs = ["*"]
            subsetter = Subsetter(options=options)
            subsetter.populate(unicodes=unicodes)
            subsetter.subset(font)
            font.flavor = "woff"
            font.save(output)
            result[family] = base64.b64encode(output.read_bytes()).decode("ascii")
    return result


def body_text(body: str, title: str) -> str:
    visible = re.findall(r">([^<>]+)<", body)
    return title + "".join(visible)


def style(fonts: dict[str, str], delay: float) -> str:
    animation = "" if STATIC else "animation: rise .75s cubic-bezier(.22,1,.36,1) both;"
    faces = []
    if "instrument" in fonts:
        faces.append(f'@font-face{{font-family:Instrument Serif;src:url(data:font/woff;base64,{fonts["instrument"]}) format("woff");}}')
    if "instrument-italic" in fonts:
        faces.append(f'@font-face{{font-family:Instrument Serif;src:url(data:font/woff;base64,{fonts["instrument-italic"]}) format("woff");font-style:italic;}}')
    if "geist" in fonts:
        faces.append(f'@font-face{{font-family:Geist;src:url(data:font/woff;base64,{fonts["geist"]}) format("woff");font-weight:400;}}')
    if "geist-semibold" in fonts:
        faces.append(f'@font-face{{font-family:Geist;src:url(data:font/woff;base64,{fonts["geist-semibold"]}) format("woff");font-weight:600;}}')
    if "mono" in fonts:
        faces.append(f'@font-face{{font-family:Geist Mono;src:url(data:font/woff;base64,{fonts["mono"]}) format("woff");}}')
    return f"""<style>
{''.join(faces)}
@keyframes rise{{from{{opacity:0;transform:translateY(12px)}}to{{opacity:1;transform:translateY(0)}}}}
.animate{{{animation}animation-delay:{delay:.2f}s}}
@media (prefers-reduced-motion:reduce){{.animate{{animation:none!important}}}}
</style>"""


def card(title: str, body: str, height: int, delay: float = 0, families: tuple[str, ...] | None = None) -> str:
    fonts = subset_fonts(body_text(body, title), families)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" viewBox="0 0 {WIDTH} {height}" role="img" aria-labelledby="card-title card-desc">
<title id="card-title">{esc(title)}</title>
<desc id="card-desc">Suman profile card</desc>
{style(fonts, delay)}
<rect width="{WIDTH}" height="{height}" rx="20" fill="{BG}"/>
{body}
</svg>
"""


def write(name: str, content: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    path.write_text(content, encoding="utf-8")
    size = path.stat().st_size
    print(f"{name}: {size} bytes")
    if size >= 100_000:
        raise RuntimeError(f"{name} exceeds 100 KB.")


def render_hero(stats: dict) -> None:
    body = f"""<g class="animate">
<text x="44" y="76" fill="{ACCENT}" font-family="Geist Mono" font-size="12" letter-spacing="2">PROFILE / SUMAN</text>
<text x="44" y="145" fill="{TEXT}" font-family="Instrument Serif" font-size="78">Suman</text>
<text x="46" y="183" fill="{MUTED}" font-family="Geist" font-size="18">B.Tech CSE student at Trident Academy of Technology (BPUT),</text>
<text x="46" y="211" fill="{MUTED}" font-family="Geist" font-size="18">class of 2027, building full-stack and AI agent systems</text>
<text x="46" y="252" fill="{TEXT}" font-family="Geist Mono" font-size="13">Bhubaneswar, India</text>
<circle cx="794" cy="144" r="66" fill="{ACCENT_DARK}" opacity=".28"/>
<circle cx="794" cy="144" r="37" fill="{ACCENT}"/>
<text x="794" y="153" text-anchor="middle" fill="{BG}" font-family="Instrument Serif" font-size="32">S</text>
</g>"""
    write("hero.svg", card("Suman profile", body, 290, 0))


def render_heatmap(data: dict) -> None:
    days = data["days"]
    start_offset = 0
    if days:
        start_offset = __import__("datetime").date.fromisoformat(days[0]["date"]).weekday()
    cells = []
    colors = {"NONE": "#1c1b1d", "FIRST_QUARTILE": "#59442c", "SECOND_QUARTILE": "#906633", "THIRD_QUARTILE": "#bd813c", "FOURTH_QUARTILE": ACCENT}
    for index in range(53 * 7):
        day_index = index - start_offset
        if 0 <= day_index < len(days):
            day = days[day_index]
            color = colors.get(day["level"], colors["NONE"])
        else:
            color = "#111114"
        col, row = divmod(index, 7)
        cells.append(f'<rect class="animate" style="animation-delay:{.25 + col * .01:.2f}s" x="{44 + col * 15}" y="{76 + row * 15}" width="10" height="10" rx="2" fill="{color}"/>')
    current = data["current_streak"]
    longest = data["longest_streak"]
    best = data["best_day"]
    body = f"""<g class="animate">
<text x="44" y="45" fill="{MUTED}" font-family="Geist Mono" font-size="12" letter-spacing="2">CONTRIBUTIONS / LAST 365 DAYS</text>
<text x="44" y="62" fill="{TEXT}" font-family="Geist" font-size="13">{data["total_contributions"]} contributions across {data["active_days"]} active days</text>
</g>
<g>{''.join(cells)}</g>
<g class="animate">
<text x="44" y="204" fill="{MUTED}" font-family="Geist Mono" font-size="11">LESS</text>
<rect x="78" y="196" width="10" height="10" rx="2" fill="#1c1b1d"/><rect x="93" y="196" width="10" height="10" rx="2" fill="#906633"/><rect x="108" y="196" width="10" height="10" rx="2" fill="{ACCENT}"/>
<text x="126" y="204" fill="{MUTED}" font-family="Geist Mono" font-size="11">MORE</text>
<text x="300" y="204" fill="{MUTED}" font-family="Geist Mono" font-size="11">CURRENT {current["length"]}d</text>
<text x="410" y="204" fill="{MUTED}" font-family="Geist Mono" font-size="11">LONGEST {longest["length"]}d</text>
<text x="540" y="204" fill="{MUTED}" font-family="Geist Mono" font-size="11">BEST {esc(best["date"])} / {best["count"]}</text>
</g>"""
    write("heatmap.svg", card("Contribution heatmap", body, 250, .4, ("geist", "geist-semibold", "mono")))


def render_activity(data: dict) -> None:
    monthly = list(data["monthly"].items())
    total = sum(value for _, value in monthly)
    if total != data["total_contributions"]:
        raise RuntimeError("Activity bars do not sum to total contributions.")
    values = [value for _, value in monthly]
    peak = max(values) if values else 1
    best_index = values.index(peak) if values else 0
    bars = []
    chart_width = 610
    bar_width = chart_width / max(len(monthly), 1)
    for index, (month, value) in enumerate(monthly):
        height = 14 + (value / peak * 105 if peak else 0)
        x = 44 + index * bar_width
        color = ACCENT if index == best_index else ACCENT_DARK
        bars.append(f'<rect class="animate" style="animation-delay:{.7 + index * .04:.2f}s" x="{x + 3:.2f}" y="{228 - height:.2f}" width="{max(8, bar_width - 7):.2f}" height="{height:.2f}" rx="5" fill="{color}"/><text x="{x + bar_width / 2:.2f}" y="250" text-anchor="middle" fill="{MUTED}" font-family="Geist Mono" font-size="10">{esc(month[5:])}</text>')
    body = f"""<g class="animate">
<text x="44" y="55" fill="{TEXT}" font-family="Instrument Serif" font-size="42">A year in motion</text>
<text x="46" y="78" fill="{MUTED}" font-family="Geist" font-size="14">Monthly contribution rhythm.</text>
<text x="46" y="98" fill="{MUTED}" font-family="Geist" font-size="14">The strongest complete month is highlighted.</text>
</g>
<g>{''.join(bars)}</g>
<g class="animate">
<text x="716" y="78" fill="{MUTED}" font-family="Geist Mono" font-size="11">TOTAL</text><text x="716" y="113" fill="{TEXT}" font-family="Geist" font-size="30" font-weight="600">{total}</text>
<text x="716" y="146" fill="{MUTED}" font-family="Geist Mono" font-size="11">ACTIVE DAYS</text><text x="716" y="174" fill="{TEXT}" font-family="Geist" font-size="20" font-weight="600">{data["active_days"]}</text>
<text x="716" y="204" fill="{MUTED}" font-family="Geist Mono" font-size="11">BEST MONTH</text><text x="716" y="228" fill="{ACCENT}" font-family="Geist" font-size="17" font-weight="600">{esc(monthly[best_index][0] if monthly else "TODO_BEST_MONTH")}</text>
</g>"""
    write("activity.svg", card("Monthly activity", body, 260, .8, ("instrument", "geist", "geist-semibold", "mono")))


def render_tile(kind: str, value: str, delay: float) -> None:
    width = 293.333
    value_size = 42 if len(value) <= 8 else 22
    body = f"""<g class="animate">
<rect x="4" y="4" width="285.333" height="152" rx="16" fill="{PANEL}" stroke="{LINE}"/>
<text x="22" y="44" fill="{ACCENT}" font-family="Geist Mono" font-size="11" letter-spacing="2">{esc(kind)}</text>
<text x="22" y="103" fill="{TEXT}" font-family="Instrument Serif" font-size="{value_size}">{esc(value)}</text>
<text x="22" y="133" fill="{MUTED}" font-family="Geist" font-size="12">hand-set profile signal</text>
</g>"""
    tile_fonts = subset_fonts(body_text(body, kind), ("instrument", "geist", "mono"))
    write(f"tile-{kind.lower()}.svg", f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="160" viewBox="0 0 {width} 160" role="img" aria-labelledby="tile-title tile-desc">
<title id="tile-title">{esc(kind)} profile tile</title><desc id="tile-desc">Profile tile for Suman</desc>
{style(tile_fonts, delay)}
<rect width="{width}" height="160" fill="{BG}"/>
{body}
</svg>
""")


def render_repo(stats: dict, repo: dict) -> None:
    description = stats["repo_descriptions"].get(repo["name"], "TODO_REPO_DESCRIPTION_PODCAST_BUDDY")
    body = f"""<g class="animate">
<text x="44" y="58" fill="{ACCENT}" font-family="Geist Mono" font-size="11" letter-spacing="2">FEATURED REPOSITORY</text>
<text x="44" y="112" fill="{TEXT}" font-family="Instrument Serif" font-size="46">{esc(repo["name"])}</text>
<text x="46" y="143" fill="{MUTED}" font-family="Geist" font-size="15">{esc(description)}</text>
<text x="46" y="176" fill="{ACCENT}" font-family="Geist Mono" font-size="12">{esc(repo["language"])}</text>
</g>"""
    write(f'repo-{repo["slug"].lower()}.svg', card(repo["name"], body, 210, 1.8))


def render_title(theme: str) -> None:
    background = "#f4f1ed" if theme == "light" else BG
    foreground = "#171517" if theme == "light" else TEXT
    body = f"""<text class="animate" x="44" y="78" fill="{foreground}" font-family="Instrument Serif" font-size="58">What I&apos;m building</text>"""
    title = f"What I'm building ({theme})"
    title_fonts = subset_fonts(body_text(body, title), ("instrument",))
    write(f"title-{theme}.svg", f"""<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="110" viewBox="0 0 {WIDTH} 110" role="img" aria-labelledby="title desc">
<title id="title">{esc(title)}</title><desc id="desc">Section title</desc>
{style(title_fonts, 1.5)}
<rect width="{WIDTH}" height="110" rx="20" fill="{background}"/>
{body}
</svg>
""")


def main() -> None:
    data = load_json(DATA / "contributions.json")
    stats = load_json(DATA / "stats.json")
    render_hero(stats)
    render_heatmap(data)
    render_activity(data)
    for index, kind in enumerate(("BUILD", "BRAND", "LEARN")):
        render_tile(kind, stats["tiles"][kind], 1.1 + index * .12)
    render_title("light")
    render_title("dark")
    for repo in REPOS:
        render_repo(stats, repo)


if __name__ == "__main__":
    main()
