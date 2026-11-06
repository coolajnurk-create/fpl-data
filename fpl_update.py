#!/usr/bin/env python3
"""
FPL data updater. Needs only Python 3.8+ (no pip installs).

Pulls live data from the official FPL API and saves it as ONE file (fpl_data.json)
that you can upload to Claude.

Usage:
  python fpl_update.py                 # players + fixtures
  python fpl_update.py --top 80        # also per-gameweek history of the 80 highest scoring players
  python fpl_update.py --out moje.json # different output file name
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

BASE = "https://fantasy.premierleague.com/api"
# FPL sometimes rejects requests that do not look like a browser.
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; fpl-update-script)"}


def get(url, retries=3):
    """Download JSON from a URL, retrying a few times on temporary errors."""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.load(resp)
        except (urllib.error.URLError, TimeoutError) as err:
            if attempt == retries - 1:
                raise SystemExit(f"Failed to download {url}\n  {err}")
            time.sleep(2 * (attempt + 1))


def local_tz():
    """Europe/Sarajevo if the system knows it, otherwise plain UTC+1."""
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo("Europe/Sarajevo")
    except Exception:
        return timezone(timedelta(hours=1))


def print_summary(boot, fixtures):
    tz = local_tz()
    cur = next((e for e in boot["events"] if e.get("is_current")), None)
    nxt = next((e for e in boot["events"] if e.get("is_next")), None)
    if cur:
        print(f"Current gameweek: GW{cur['id']}")
    if nxt:
        dl = datetime.fromisoformat(nxt["deadline_time"].replace("Z", "+00:00")).astimezone(tz)
        print(f"Next deadline:    GW{nxt['id']}  {dl.strftime('%a %d %b %H:%M')}")

    teams = {t["id"]: t["short_name"] for t in boot["teams"]}
    flagged = [
        p for p in boot["elements"]
        if (p.get("news") or p.get("chance_of_playing_next_round") not in (None, 100))
        and float(p["selected_by_percent"]) >= 5
    ]
    flagged.sort(key=lambda p: -float(p["selected_by_percent"]))
    print(f"\nFlagged players owned by 5%+ ({len(flagged)}):")
    for p in flagged[:25]:
        chance = p.get("chance_of_playing_next_round")
        chance = "?" if chance is None else f"{chance}%"
        print(f"  {p['web_name']:<14}{teams[p['team']]:<5}{chance:<6}{p['news']}")


def main():
    ap = argparse.ArgumentParser(description="Download FPL data into one JSON file.")
    ap.add_argument("--top", type=int, default=0,
                    help="also fetch per-gameweek history for the N highest scoring players")
    ap.add_argument("--out", default="fpl_data.json", help="output file (default fpl_data.json)")
    ap.add_argument("--base", default=BASE, help=argparse.SUPPRESS)  # used for testing
    args = ap.parse_args()

    print("Downloading players and teams...")
    boot = get(f"{args.base}/bootstrap-static/")
    print("Downloading fixtures...")
    fixtures = get(f"{args.base}/fixtures/")

    summaries = {}
    if args.top > 0:
        best = sorted(boot["elements"], key=lambda p: -p["total_points"])[: args.top]
        for i, p in enumerate(best, 1):
            print(f"  history {i}/{len(best)}: {p['web_name']}", end="\r")
            data = get(f"{args.base}/element-summary/{p['id']}/")
            summaries[str(p["id"])] = {"name": p["web_name"], "history": data.get("history", [])}
            time.sleep(0.3)  # be polite to the server
        print()

    out = {
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "bootstrap": boot,
        "fixtures": fixtures,
        "summaries": summaries,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    size_mb = len(json.dumps(out, ensure_ascii=False)) / 1_000_000
    print(f"\nSaved {args.out} ({size_mb:.1f} MB). Upload this file to Claude.\n")
    print_summary(boot, fixtures)


if __name__ == "__main__":
    sys.exit(main())
