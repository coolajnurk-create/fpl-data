#!/usr/bin/env python3
"""
FPL data updater. Needs only Python 3.8+ (no pip installs).

Pulls live data from the official FPL API and saves it as ONE file (fpl_data.json)
that you can upload to Claude.

Usage:
  python fpl_update.py                 # players + fixtures
  python fpl_update.py --top 80        # also per-gameweek history of the 80 highest scoring players
  python fpl_update.py --out moje.json # different output file name
  python fpl_update.py --keep-summaries old.json
                                       # light update: keep player histories from old.json
  python fpl_update.py --league 322114 --league-out league.json
                                       # also mini-league standings, manager histories, picks,
                                       # transfers and a per-gameweek table (league.json = small file)
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


def try_get(url):
    """Like get(), but returns None instead of stopping the script (used for league extras)."""
    try:
        return get(url, retries=2)
    except SystemExit as err:
        print(f"  skipped {url} ({err})")
        return None


def build_league(base, league_id, boot, old_league, full):
    """Mini-league standings (always) plus per-manager details (only on full runs)."""
    cur = next((e for e in boot["events"] if e.get("is_current")), None)
    cur_gw = cur["id"] if cur else None

    print(f"Downloading league {league_id} standings...")
    results, name, page = [], None, 1
    while page <= 5:
        data = try_get(f"{base}/leagues-classic/{league_id}/standings/?page_standings={page}")
        if not data:
            break
        name = data["league"]["name"]
        results += data["standings"]["results"]
        if not data["standings"].get("has_next"):
            break
        page += 1
    if not results:
        return old_league  # keep whatever we had

    standings = [
        {"rank": r["rank"], "last_rank": r["last_rank"], "entry": r["entry"],
         "team": r["entry_name"], "manager": r["player_name"],
         "event_total": r["event_total"], "total": r["total"]}
        for r in results
    ]
    managers = {}
    old_managers = (old_league or {}).get("managers") or {}
    managers_fetched_at = (old_league or {}).get("managers_fetched_at")

    if full:
        for i, r in enumerate(results, 1):
            e = r["entry"]
            print(f"  manager {i}/{len(results)}: {r['entry_name']}", end="\r")
            hist = try_get(f"{base}/entry/{e}/history/") or {}
            picks = try_get(f"{base}/entry/{e}/event/{cur_gw}/picks/") if cur_gw else None
            transfers = try_get(f"{base}/entry/{e}/transfers/")
            managers[str(e)] = {
                "history": {"current": hist.get("current", []), "chips": hist.get("chips", [])},
                "picks": {"event": cur_gw, **picks} if picks else None,
                "transfers": transfers,
            }
            time.sleep(0.3)
        print()
        managers_fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    else:
        managers = {k: v for k, v in old_managers.items() if int(k) in {r["entry"] for r in results}}

    # Per-gameweek table: net points (after transfer hits) and rank among the league's managers
    per_gw = []
    gws = sorted({h["event"] for m in managers.values() for h in m["history"]["current"]})
    for gw in gws:
        net = {}
        for e, m in managers.items():
            h = next((x for x in m["history"]["current"] if x["event"] == gw), None)
            if h:
                net[e] = h["points"] - h["event_transfers_cost"]
        order = sorted(net, key=lambda e: -net[e])
        ranks = {e: 1 + sum(1 for o in net if net[o] > net[e]) for e in order}
        per_gw.append({"gw": gw, "net_points": net, "rank_in_league": ranks,
                       "best_entry": order[0] if order else None,
                       "best_points": net[order[0]] if order else None})

    return {
        "id": league_id, "name": name, "current_gw": cur_gw,
        "standings": standings, "managers": managers,
        "managers_fetched_at": managers_fetched_at, "per_gw": per_gw,
    }


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
    ap.add_argument("--keep-summaries", metavar="FILE",
                    help="without --top: copy player histories (summaries) from this existing file")
    ap.add_argument("--league", type=int, default=0, metavar="ID",
                    help="also download this classic mini league (standings, histories, picks, transfers)")
    ap.add_argument("--league-out", metavar="FILE",
                    help="also write the league data alone to this small file")
    ap.add_argument("--base", default=BASE, help=argparse.SUPPRESS)  # used for testing
    args = ap.parse_args()

    print("Downloading players and teams...")
    boot = get(f"{args.base}/bootstrap-static/")
    print("Downloading fixtures...")
    fixtures = get(f"{args.base}/fixtures/")

    summaries = {}
    summaries_fetched_at = None
    if args.top > 0:
        best = sorted(boot["elements"], key=lambda p: -p["total_points"])[: args.top]
        for i, p in enumerate(best, 1):
            print(f"  history {i}/{len(best)}: {p['web_name']}", end="\r")
            data = get(f"{args.base}/element-summary/{p['id']}/")
            summaries[str(p["id"])] = {"name": p["web_name"], "history": data.get("history", [])}
            time.sleep(0.3)  # be polite to the server
        print()
        summaries_fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    elif args.keep_summaries:
        try:
            with open(args.keep_summaries, encoding="utf-8") as f:
                old = json.load(f)
            summaries = old.get("summaries") or {}
            summaries_fetched_at = old.get("summaries_fetched_at") or (old.get("fetched_at") if summaries else None)
            print(f"Kept {len(summaries)} player histories from {args.keep_summaries}")
        except (OSError, ValueError) as err:
            print(f"Could not read {args.keep_summaries}, no histories kept ({err})")

    league = None
    if args.league:
        old_league = None
        if args.keep_summaries:
            try:
                with open(args.keep_summaries, encoding="utf-8") as f:
                    old_league = json.load(f).get("league")
            except (OSError, ValueError):
                pass
        league = build_league(args.base, args.league, boot, old_league, full=args.top > 0)

    out = {
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "bootstrap": boot,
        "fixtures": fixtures,
        "summaries": summaries,
        "summaries_fetched_at": summaries_fetched_at,
    }
    if league:
        out["league"] = league
        if args.league_out:
            with open(args.league_out, "w", encoding="utf-8") as f:
                json.dump({"fetched_at": out["fetched_at"], **league}, f, ensure_ascii=False)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    size_mb = len(json.dumps(out, ensure_ascii=False)) / 1_000_000
    print(f"\nSaved {args.out} ({size_mb:.1f} MB). Upload this file to Claude.\n")
    print_summary(boot, fixtures)


if __name__ == "__main__":
    sys.exit(main())
