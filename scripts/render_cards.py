#!/usr/bin/env python3
"""Render the animated SVG cards used by the profile README."""

from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARDS = ROOT / "cards"
DATA_PATH = ROOT / "data" / "contributions.json"
FONT_PATH = Path(os.environ.get("FONT_PATH", ROOT / "fonts" / "Outfit-Variable.ttf"))

BG = "#09090b"
CARD = "#121114"
TEXT = "#f4f1ef"
MUTED = "#a9a2a0"
BORDER = "#2b2729"
ACCENT = "#f4b860"
GREEN = "#9bbf74"
MONO = "Geist Mono, monospace"
STATIC = os.environ.get("STATIC") == "1"
PORTRAIT = os.environ.get("PORTRAIT_URL", "")


def esc(value: object) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def font_data_uri() -> str:
    if not FONT_PATH.exists():
        raise FileNotFoundError(
            f"Missing {FONT_PATH}. Download Outfit-Variable.ttf or set FONT_PATH."
        )
    pyftsubset = shutil.which("pyftsubset")
    if not pyftsubset:
        raise RuntimeError("pyftsubset is required. Install fonttools before rendering cards.")
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory) / "outfit.woff"
        subprocess.run(
            [
                pyftsubset,
                str(FONT_PATH),
                f"--output-file={output}",
                "--flavor=woff",
                "--layout-features=*",
                "--unicodes=U+0000-00FF,U+2013-2014,U+2018-2019,U+201C-201D,U+2022,U+2197",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        encoded = base64.b64encode(output.read_bytes()).decode("ascii")
    return f"data:font/woff;base64,{encoded}"


def shell(title: str, delay: float = 0.0) -> str:
    return f"""
  <style>
    @font-face {{ font-family: Outfit; src: url('{FONT_URI}') format('woff'); font-weight: 100 900; }}
    @keyframes rise {{ from {{ opacity: 0; transform: translateY(14px); }} to {{ opacity: 1; transform: translateY(0); }} }}
    @keyframes draw {{ from {{ stroke-dashoffset: 900; }} to {{ stroke-dashoffset: 0; }} }}
    @keyframes pulse {{ 0%, 100% {{ opacity: .45; }} 50% {{ opacity: 1; }} }}
    .rise {{ animation: rise .75s cubic-bezier(.22,1,.36,1) both; animation-delay: {delay:.2f}s; }}
    .draw {{ stroke-dasharray: 900; animation: draw 1.4s ease-out both; animation-delay: {delay + .25:.2f}s; }}
    .pulse {{ animation: pulse 2.4s ease-in-out infinite; animation-delay: {delay + .5:.2f}s; }}
    {"*, *::before, *::after { animation: none !important; }" if STATIC else ""}
    @media (prefers-reduced-motion: reduce) {{
      *, *::before, *::after {{ animation: none !important; transition: none !important; }}
    }}
  </style>
  <rect width="100%" height="100%" rx="24" fill="{BG}" />
  <rect x="1" y="1" width="calc(100% - 2px)" height="calc(100% - 2px)" rx="23" fill="{CARD}" stroke="{BORDER}" />
  <text x="42" y="45" fill="{MUTED}" font-family="{MONO}" font-size="12" letter-spacing="2">{esc(title.upper())}</text>
"""


def svg(title: str, width: int, height: int, body: str, delay: float = 0.0) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
  <title id="title">{esc(title)}</title><desc id="desc">Animated profile card for Suman Dey</desc>
  {shell(title, delay)}{body}
</svg>
"""


def load_data() -> dict:
    if not DATA_PATH.exists():
        return {"contributionCalendar": {"totalContributions": 0, "weeks": []}}
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def days_from_data(data: dict) -> list[dict]:
    days = []
    for week in data.get("contributionCalendar", {}).get("weeks", []):
        days.extend(week.get("contributionDays", []))
    return days


def contribution_summary(data: dict) -> tuple[list[tuple[str, int]], int, int, str, list[dict]]:
    days = days_from_data(data)
    months: dict[str, int] = {}
    for day in days:
        month = day["date"][:7]
        months[month] = months.get(month, 0) + int(day.get("contributionCount", 0))
    chart = list(months.items())[-12:]
    active = sum(int(day.get("contributionCount", 0)) > 0 for day in days)
    streak = 0
    for day in reversed(days):
        if int(day.get("contributionCount", 0)) > 0:
            streak += 1
        elif streak:
            break
    busiest = max(days, key=lambda day: int(day.get("contributionCount", 0)), default={"date": "—", "contributionCount": 0})
    return chart, streak, active, busiest["date"], days


def render_hero() -> str:
    portrait = (
        f'<image href="{esc(PORTRAIT)}" x="976" y="88" width="84" height="84" clip-path="url(#portrait)"/>'
        if PORTRAIT
        else '<circle class="pulse" cx="1018" cy="130" r="48" fill="#f4b860" opacity=".16"/><circle cx="1018" cy="130" r="31" fill="#f4b860" opacity=".9"/><text x="1018" y="137" text-anchor="middle" fill="#09090b" font-family="Outfit, sans-serif" font-size="22" font-weight="700">SD</text>'
    )
    return svg(
        "Suman Dey",
        1100,
        260,
        f"""
  <g class="rise">
    <text x="42" y="124" fill="{TEXT}" font-family="Outfit, sans-serif" font-size="64" font-weight="650" letter-spacing="-2">Suman Dey</text>
    <text x="45" y="166" fill="{ACCENT}" font-family="Outfit, sans-serif" font-size="20">AIML at MindBrain Innovation · building useful things, one percent better every day.</text>
    <text x="45" y="211" fill="{MUTED}" font-family="{MONO}" font-size="13">sumandey.in  /  github.com/sumandey7684</text>
  </g>
  <defs><clipPath id="portrait"><circle cx="1018" cy="130" r="42"/></clipPath></defs>
  {portrait}
""",
        0.0,
    )


def render_link_tile(label: str, value: str, url: str, delay: float) -> str:
    return svg(
        label,
        340,
        150,
        f"""  <a href="{esc(url)}">
    <g class="rise">
      <rect x="1" y="1" width="338" height="148" rx="23" fill="{CARD}" stroke="{BORDER}"/>
      <text x="24" y="45" fill="{ACCENT}" font-family="{MONO}" font-size="11" letter-spacing="1.5">{esc(label)}</text>
      <text x="24" y="88" fill="{TEXT}" font-family="Outfit, sans-serif" font-size="20" font-weight="550">{esc(value)}</text>
      <text x="308" y="88" fill="{MUTED}" font-family="{MONO}" font-size="18">↗</text>
    </g>
  </a>""",
        delay,
    )


def render_activity(data: dict) -> str:
    chart, streak, active, busiest, _ = contribution_summary(data)
    max_value = max((value for _, value in chart), default=1)
    bars = []
    for index, (month, value) in enumerate(chart):
        x = 55 + index * 60
        height = max(4, round(value / max_value * 104))
        bars.append(
            f"""<rect class="rise" style="animation-delay:{.55 + index * .04:.2f}s" x="{x}" y="{164 - height}" width="30" height="{height}" rx="7" fill="{ACCENT}" opacity="{.42 + (index / max(len(chart), 1)) * .5:.2f}"/>
  <text x="{x + 15}" y="190" text-anchor="middle" fill="{MUTED}" font-family="{MONO}" font-size="10">{esc(month[5:])}</text>"""
        )
    return svg(
        "Build log",
        1100,
        260,
        f"""
  <g class="rise">
    <text x="42" y="84" fill="{TEXT}" font-family="Outfit, sans-serif" font-size="28" font-weight="600">A year in motion</text>
    <text x="42" y="108" fill="{MUTED}" font-family="Outfit, sans-serif" font-size="14">Small commits, compounding into useful work.</text>
  </g>
  <g>{''.join(bars)}</g>
  <g class="rise" style="animation-delay:.9s">
    <text x="810" y="105" fill="{MUTED}" font-family="{MONO}" font-size="11">CURRENT STREAK</text>
    <text x="810" y="136" fill="{TEXT}" font-family="Outfit, sans-serif" font-size="28" font-weight="650">{streak} days</text>
    <text x="810" y="165" fill="{MUTED}" font-family="{MONO}" font-size="11">ACTIVE DAYS  {active}   ·   PEAK  {esc(busiest)}</text>
  </g>
""",
        0.5,
    )


def render_repo(repo: dict, index: int) -> str:
    language = repo.get("language", "Code")
    stars = repo.get("stars", 0)
    return svg(
        repo.get("name", "Featured project"),
        1100,
        190,
        f"""
  <a href="{esc(repo.get('url', '#'))}">
    <g class="rise" style="animation-delay:{index * .12:.2f}s">
      <text x="42" y="91" fill="{TEXT}" font-family="Outfit, sans-serif" font-size="29" font-weight="600">{esc(repo.get("name", "Featured project"))}</text>
      <text x="42" y="124" fill="{MUTED}" font-family="Outfit, sans-serif" font-size="15">{esc(repo.get("description", "A project I am proud to build."))}</text>
      <text x="42" y="158" fill="{ACCENT}" font-family="{MONO}" font-size="11">{esc(language.upper())}   ·   ★ {stars}</text>
      <text x="1018" y="113" text-anchor="middle" fill="{ACCENT}" font-family="{MONO}" font-size="21">↗</text>
    </g>
  </a>
""",
        1.1 + index * .2,
    )


def render_graph(data: dict) -> str:
    _, _, _, _, days = contribution_summary(data)
    cells = []
    for index, day in enumerate(days[-365:]):
        col, row = index // 7, index % 7
        count = int(day.get("contributionCount", 0))
        color = ["#211e20", "#5a4930", "#98733c", "#d39a4e", ACCENT][min(4, count // 3 + (1 if count else 0))]
        cells.append(f'<rect x="{44 + col * 15}" y="{76 + row * 15}" width="10" height="10" rx="2" fill="{color}"/>')
    return svg(
        "Contribution map",
        1100,
        220,
        f"""
  <g class="rise">
    <text x="42" y="45" fill="{MUTED}" font-family="{MONO}" font-size="12" letter-spacing="2">CONTRIBUTION MAP · LAST 365 DAYS</text>
  </g>
  <g class="rise" style="animation-delay:1.5s">{''.join(cells)}</g>
  <text x="44" y="204" fill="{MUTED}" font-family="{MONO}" font-size="11">less</text>
  <rect x="76" y="196" width="10" height="10" rx="2" fill="#211e20"/><rect x="91" y="196" width="10" height="10" rx="2" fill="#98733c"/><rect x="106" y="196" width="10" height="10" rx="2" fill="{ACCENT}"/>
  <text x="126" y="204" fill="{MUTED}" font-family="{MONO}" font-size="11">more</text>
""",
        1.7,
    )


def main() -> None:
    global FONT_URI
    FONT_URI = font_data_uri()
    data = load_data()
    profile = {
        "featured_repos": [
            {"name": "AstraDB", "language": "C++", "stars": 2, "url": "https://github.com/sumandey7684/AstraDB", "description": "A custom vector database with ANN indexing and semantic search."},
            {"name": "Podcast-buddy", "language": "Python", "stars": 1, "url": "https://github.com/sumandey7684/Podcast-buddy", "description": "An AI-powered news-to-podcast platform with natural two-host episodes."},
            {"name": "PDFly", "language": "TypeScript", "stars": 2, "url": "https://github.com/sumandey7684/PDFly", "description": "A privacy-focused PDF toolkit that runs entirely in your browser."},
        ]
    }
    CARDS.mkdir(exist_ok=True)
    (CARDS / "hero.svg").write_text(render_hero(), encoding="utf-8")
    links = [
        ("WEBSITE", "sumandey.in", "https://sumandey.in"),
        ("LINKEDIN", "in/sumandey7684", "https://linkedin.com/in/sumandey7684"),
        ("X / TWITTER", "@sumxnnn", "https://x.com/sumxnnn"),
    ]
    for index, link in enumerate(links, 1):
        (CARDS / f"links-{index}.svg").write_text(render_link_tile(*link, .35 + index * .12), encoding="utf-8")
    (CARDS / "activity.svg").write_text(render_activity(data), encoding="utf-8")
    (CARDS / "contributions.svg").write_text(render_graph(data), encoding="utf-8")
    for index, repo in enumerate(profile["featured_repos"], 1):
        (CARDS / f"repo-{index}.svg").write_text(render_repo(repo, index), encoding="utf-8")
    print(f"Rendered {len(list(CARDS.glob('*.svg')))} cards to {CARDS}")


if __name__ == "__main__":
    main()
