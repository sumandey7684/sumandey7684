#!/usr/bin/env python3
"""Fetch and normalize the profile owner's GitHub contribution calendar."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "contributions.json"
GRAPHQL_URL = "https://api.github.com/graphql"


def level_for_count(count: int) -> str:
    if count == 0:
        return "NONE"
    if count <= 2:
        return "FIRST_QUARTILE"
    if count <= 5:
        return "SECOND_QUARTILE"
    if count <= 10:
        return "THIRD_QUARTILE"
    return "FOURTH_QUARTILE"


def contribution_window() -> tuple[date, date]:
    end = datetime.now(timezone.utc).date()
    return end - timedelta(days=364), end


def streaks(days: list[dict]) -> tuple[dict, dict]:
    longest = {"length": 0, "start": None, "end": None}
    run_start: date | None = None
    run_length = 0
    for item in days:
        if item["count"] > 0:
            if run_start is None:
                run_start = date.fromisoformat(item["date"])
            run_length += 1
            if run_length > longest["length"]:
                longest = {
                    "length": run_length,
                    "start": run_start.isoformat(),
                    "end": item["date"],
                }
        else:
            run_start = None
            run_length = 0

    index = len(days) - 1
    if days[index]["count"] == 0:
        index -= 1
    current = {"length": 0, "start": None, "end": None}
    if index >= 0:
        end = days[index]["date"]
        while index >= 0 and days[index]["count"] > 0:
            current["length"] += 1
            current["start"] = days[index]["date"]
            index -= 1
        current["end"] = end
    return current, longest


def normalize(raw: dict, start: date, end: date) -> dict:
    calendar = raw.get("data", {}).get("user", {}).get("contributionsCollection", {})
    raw_days = [
        item
        for week in calendar.get("contributionCalendar", {}).get("weeks", [])
        for item in week.get("contributionDays", [])
    ]
    days = [
        {
            "date": item["date"],
            "count": int(item["contributionCount"]),
            "level": item.get("contributionLevel", level_for_count(int(item["contributionCount"]))),
        }
        for item in raw_days
        if start.isoformat() <= item["date"] <= end.isoformat()
    ]
    if not 360 <= len(days) <= 370:
        raise RuntimeError(f"Contribution day count {len(days)} is outside 360 to 370.")
    if sum(item["count"] for item in days) == 0:
        raise RuntimeError("Contribution data contains no contributions.")

    monthly: dict[str, int] = defaultdict(int)
    cursor = start.replace(day=1)
    last_month = end.replace(day=1)
    while cursor <= last_month:
        monthly[cursor.strftime("%Y-%m")] = 0
        cursor = (cursor.replace(day=28) + timedelta(days=4)).replace(day=1)
    for item in days:
        monthly[item["date"][:7]] += item["count"]

    total = int(calendar.get("contributionCalendar", {}).get("totalContributions", 0))
    day_total = sum(item["count"] for item in days)
    monthly_total = sum(monthly.values())
    if day_total != total or monthly_total != total:
        raise RuntimeError(
            f"Contribution totals disagree: days={day_total}, monthly={monthly_total}, total={total}."
        )

    current, longest = streaks(days)
    best = max(days, key=lambda item: item["count"])
    return {
        "total_contributions": total,
        "active_days": sum(item["count"] > 0 for item in days),
        "current_streak": current,
        "longest_streak": longest,
        "best_day": {"date": best["date"], "count": best["count"]},
        "monthly": dict(monthly),
        "days": days,
    }


def fixture(start: date, end: date) -> dict:
    raw_days = []
    for offset in range((end - start).days + 1):
        current = start + timedelta(days=offset)
        count = 0 if offset % 11 in (0, 1, 2) else (offset % 7) + 1
        raw_days.append(
            {
                "date": current.isoformat(),
                "contributionCount": count,
                "contributionLevel": level_for_count(count),
            }
        )
    total = sum(item["contributionCount"] for item in raw_days)
    raw = {
        "data": {
            "user": {
                "contributionsCollection": {
                    "contributionCalendar": {
                        "totalContributions": total,
                        "weeks": [{"contributionDays": raw_days}],
                    }
                }
            }
        }
    }
    return normalize(raw, start, end)


def fetch(login: str, token: str, start: date, end: date) -> dict:
    query = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                contributionCount
                contributionLevel
                date
              }
            }
          }
        }
      }
    }
    """
    payload = json.dumps(
        {
            "query": query,
            "variables": {
                "login": login,
                "from": datetime.combine(start, time.min, timezone.utc).isoformat(),
                "to": datetime.combine(end, time.max, timezone.utc).isoformat(),
            },
        }
    ).encode("utf-8")
    request = Request(
        GRAPHQL_URL,
        data=payload,
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "profile-readme-contributions",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            raw = json.load(response)
    except (HTTPError, URLError) as exc:
        raise RuntimeError(f"GitHub GraphQL request failed: {exc}") from exc
    if raw.get("errors"):
        raise RuntimeError(f"GitHub GraphQL returned errors: {raw['errors']}")
    if not raw.get("data", {}).get("user"):
        raise RuntimeError(f"GitHub user {login!r} was not found.")
    return normalize(raw, start, end)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", action="store_true", help="Use deterministic local data.")
    args = parser.parse_args()
    start, end = contribution_window()
    token = os.environ.get("GH_PAT")
    login = os.environ.get("GH_USER", "sumandey7684")
    if args.fixture:
        result = fixture(start, end)
    elif token:
        result = fetch(login, token, start, end)
    else:
        print("GH_PAT is not set. Pass --fixture for local verification.", file=sys.stderr)
        return 2
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
