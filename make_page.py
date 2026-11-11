#!/usr/bin/env python3
"""Builds a small plain-HTML site from fpl_data.json: summary page (index.html) plus pages with ALL the data.
Usage: python make_page.py fpl_data.json outdir"""
import os
import html
import json
import sys
from datetime import datetime, timedelta, timezone

POS = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}


def tz():
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo("Europe/Sarajevo")
    except Exception:
        return timezone(timedelta(hours=1))


def esc(x):
    return html.escape(str(x))


def table(head, rows):
    out = ["<table border='1' cellpadding='4' cellspacing='0'>", "<tr>" + "".join(f"<th>{esc(h)}</th>" for h in head) + "</tr>"]
    for r in rows:
        out.append("<tr>" + "".join(f"<td>{esc(c)}</td>" for c in r) + "</tr>")
    out.append("</table>")
    return "\n".join(out)


NAV = ("<p><b>All pages:</b> <a href='index.html'>summary</a> | <a href='league_full.html'>league full data</a> | "
       "<a href='players_gk.html'>players GK</a> | <a href='players_def.html'>players DEF</a> | "
       "<a href='players_mid.html'>players MID</a> | <a href='players_fwd.html'>players FWD</a> | "
       "<a href='fixtures.html'>fixtures</a> | <a href='history_gk.html'>player history GK</a> | "
       "<a href='history_def.html'>history DEF</a> | <a href='history_mid.html'>history MID</a> | "
       "<a href='history_fwd.html'>history FWD</a> | <a href='teams_events.html'>teams, gameweeks, glossary</a> | "
       "<a href='league.json'>league.json</a> | <a href='fpl_data.json'>fpl_data.json</a></p>")


def cell(v):
    if isinstance(v, (list, dict)):
        return json.dumps(v, ensure_ascii=False)
    return "" if v is None else v


def full_table(rows, first=None):
    """Table with every key of every row (first = keys shown first)."""
    keys = list(first or [])
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    out = ["<table border='1' cellpadding='3' cellspacing='0'>", "<tr>" + "".join(f"<th>{esc(k)}</th>" for k in keys) + "</tr>"]
    for r in rows:
        out.append("<tr>" + "".join(f"<td>{esc(cell(r.get(k)))}</td>" for k in keys) + "</tr>")
    out.append("</table>")
    return "\n".join(out)


def page(path, title, intro, body):
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"<!doctype html><html><head><meta charset='utf-8'><title>{esc(title)}</title></head><body>"
                f"<h1>{esc(title)}</h1>{NAV}<p>{intro}</p>{body}{NAV}</body></html>")


def build_full_pages(d, outdir):
    b = d["bootstrap"]
    teams = {t["id"]: t["short_name"] for t in b["teams"]}
    players = {p["id"]: p for p in b["elements"]}
    pname = lambda i: f"{players[i]['web_name']} ({teams[players[i]['team']]})" if i in players else str(i)
    j = lambda *a: os.path.join(outdir, *a)

    # players, one page per position, ALL fields (price in millions, team as short name)
    for t, short in ((1, "gk"), (2, "def"), (3, "mid"), (4, "fwd")):
        rows = []
        for p in sorted((p for p in b["elements"] if p["element_type"] == t), key=lambda p: -p["total_points"]):
            r = dict(p)
            r["team"] = teams[p["team"]]
            r["element_type"] = POS[t]
            r["price_m"] = p["now_cost"] / 10
            rows.append(r)
        first = ["id", "web_name", "first_name", "second_name", "team", "element_type", "price_m", "total_points", "form", "selected_by_percent", "minutes"]
        page(j(f"players_{short}.html"), f"All {POS[t]} players, every field",
             "Sorted by season points. price_m is the price in millions (now_cost / 10). Field meanings are on the glossary page (teams_events.html).",
             full_table(rows, first))

    # fixtures, with player names inside stats
    rows = []
    for f in d["fixtures"]:
        r = {k: v for k, v in f.items() if k != "stats"}
        r["home"] = teams.get(f["team_h"])
        r["away"] = teams.get(f["team_a"])
        st = []
        for s in f.get("stats") or []:
            parts = [f"{pname(x['element'])} {x['value']} (h)" for x in s.get("h", [])] + [f"{pname(x['element'])} {x['value']} (a)" for x in s.get("a", [])]
            if parts:
                st.append(f"{s['identifier']}: " + ", ".join(parts))
        r["stats"] = " | ".join(st)
        rows.append(r)
    rows.sort(key=lambda r: (r.get("event") is None, r.get("event") or 0, r.get("kickoff_time") or ""))
    page(j("fixtures.html"), "All fixtures (results and upcoming)",
         "team_h_difficulty / team_a_difficulty are the FDR values (1 easy to 5 hard). event is the gameweek.",
         full_table(rows, ["event", "kickoff_time", "home", "away", "team_h_score", "team_a_score", "finished", "team_h_difficulty", "team_a_difficulty", "stats"]))

    # per-player per-gameweek history (top 100 players by season points, from the full runs)
    sums = d.get("summaries") or {}
    for t, short in ((1, "gk"), (2, "def"), (3, "mid"), (4, "fwd")):
        rows = []
        for pid, s in sums.items():
            p = players.get(int(pid))
            if not p or p["element_type"] != t:
                continue
            for hrow in s.get("history", []):
                r = {"player": p["web_name"], "team": teams[p["team"]], "player_id": p["id"]}
                r["opponent_team"] = teams.get(hrow.get("opponent_team"), hrow.get("opponent_team"))
                r.update({k: v for k, v in hrow.items() if k != "opponent_team"})
                rows.append(r)
        rows.sort(key=lambda r: (r["player"], r.get("round") or 0))
        page(j(f"history_{short}.html"), f"Gameweek history of top {POS[t]} players",
             f"One row per player per gameweek, all stats. Only the top 100 players by season points have history. Summaries fetched at: {esc(d.get('summaries_fetched_at'))}.",
             full_table(rows, ["player", "team", "round", "opponent_team", "was_home", "minutes", "total_points"]))

    # teams, gameweeks, glossary
    body = "<h2>Teams</h2>" + full_table(b["teams"])
    body += "<h2>Gameweeks (deadlines, averages, top players)</h2>" + full_table(b["events"])
    body += "<h2>Position types</h2>" + full_table(b.get("element_types", []))
    body += "<h2>Player field glossary (field name = meaning)</h2>" + full_table(b.get("element_stats", []))
    page(j("teams_events.html"), "Teams, gameweeks and field glossary", "Reference tables from the FPL API.", body)

    # league, all of it
    lg = d.get("league")
    body = "<p>No league data.</p>"
    if lg:
        names = {str(s["entry"]): s["team"] for s in lg["standings"]}
        body = "<h2>Standings</h2>" + full_table(lg["standings"])
        body += "<h2>Per gameweek: net points and rank in league (net = points minus transfer hits)</h2>"
        rows = []
        for g in lg["per_gw"]:
            r = {"gw": g["gw"], "best": f"{g['best_points']} ({names.get(str(g['best_entry']))})"}
            for e, n in names.items():
                r[n] = f"{g['net_points'].get(e)} (rank {g['rank_in_league'].get(e)})"
            rows.append(r)
        body += full_table(rows, ["gw", "best"])
        for e, n in names.items():
            m = lg["managers"].get(e)
            if not m:
                continue
            body += f"<h2>{esc(n)} (entry {e})</h2>"
            body += "<h3>History per gameweek (points is before transfer hits; value is in tenths of millions)</h3>" + full_table(m["history"]["current"])
            body += "<h3>Chips</h3>" + (full_table(m["history"]["chips"]) if m["history"]["chips"] else "<p>none</p>")
            pk = m.get("picks")
            if pk:
                rows = []
                for p in pk["picks"]:
                    pl = players[p["element"]]
                    rows.append({"squad_position": p["position"], "player": pname(p["element"]), "pos": POS[pl["element_type"]], "multiplier": p["multiplier"],
                                 "captain": p["is_captain"], "vice": p["is_vice_captain"], "price_m": pl["now_cost"] / 10, "season_pts": pl["total_points"]})
                body += f"<h3>Picks of GW{pk['event']} (positions 1-11 play, 12-15 bench; chip: {esc(pk.get('active_chip') or 'none')})</h3>" + full_table(rows)
                body += "<h3>Entry history of that GW</h3>" + full_table([pk.get("entry_history") or {}])
                if pk.get("automatic_subs"):
                    body += "<h3>Automatic subs</h3>" + full_table([{**a, "element_in": pname(a["element_in"]), "element_out": pname(a["element_out"])} for a in pk["automatic_subs"]])
            tr = m.get("transfers") or []
            rows = [{"gw": x["event"], "time": x["time"], "in": pname(x["element_in"]), "in_cost_m": x["element_in_cost"] / 10,
                     "out": pname(x["element_out"]), "out_cost_m": x["element_out_cost"] / 10} for x in tr]
            body += "<h3>All transfers</h3>" + (full_table(rows) if rows else "<p>none</p>")
    page(j("league_full.html"), "Holand Company mini league, all data",
         f"League id {lg['id'] if lg else '?'}. Standings, per-gameweek table, and for every manager: full history, chips, latest picks, all transfers.", body)


def main(src, outdir):
    os.makedirs(outdir, exist_ok=True)
    dst = os.path.join(outdir, "index.html")
    d = json.load(open(src, encoding="utf-8"))
    b = d["bootstrap"]
    lg = d.get("league")
    local = tz()
    players = {p["id"]: p for p in b["elements"]}
    teams = {t["id"]: t["short_name"] for t in b["teams"]}
    cur = next((e for e in b["events"] if e.get("is_current")), None)
    nxt = next((e for e in b["events"] if e.get("is_next")), None)
    fetched = datetime.fromisoformat(d["fetched_at"]).astimezone(local)
    h = []
    h.append("<!doctype html><html><head><meta charset='utf-8'><title>FPL data: Holand Company mini league</title></head><body>")
    h.append("<h1>FPL 2026/27: Holand Company mini league and player data</h1>")
    h.append(NAV)
    h.append(f"<p>Updated: {fetched.strftime('%a %d %b %Y %H:%M')} (Sarajevo time). Auto-updated every few hours. "
             "This one page has everything: league table, points per gameweek, chips, every manager's squad, and key player stats.</p>")
    if cur:
        h.append(f"<p>Current gameweek: GW{cur['id']}.</p>")
    if nxt:
        dl = datetime.fromisoformat(nxt["deadline_time"].replace("Z", "+00:00")).astimezone(local)
        h.append(f"<p>Next deadline: GW{nxt['id']}, {dl.strftime('%a %d %b %H:%M')} Sarajevo time.</p>")

    if lg:
        names = {str(s["entry"]): s["team"] for s in lg["standings"]}
        h.append("<h2>Who is who</h2><p>Sedrenik FC may be called 'Sedrenik city'. baklava taktika is Ajnur.</p>")
        h.append(table(["Rank", "Team", "Manager", "Entry ID", "Total", "Last GW (net)", "Last rank"],
                       [[s["rank"], s["team"], s["manager"], s["entry"], s["total"], s["event_total"], s["last_rank"]] for s in lg["standings"]]))

        h.append("<h2>Points per gameweek (net of transfer hits) and rank in the league</h2>")
        entries = [str(s["entry"]) for s in lg["standings"]]
        rows = []
        for g in lg["per_gw"]:
            rows.append([f"GW{g['gw']}"] + [f"{g['net_points'].get(e, '-')} ({g['rank_in_league'].get(e, '-')}.)" for e in entries]
                        + [f"{g['best_points']} ({names.get(str(g['best_entry']), '?')})"])
        h.append(table(["GW"] + [names[e] for e in entries] + ["League best"], rows))

        h.append("<h2>Chips used</h2>")
        rows = []
        for e in entries:
            m = lg["managers"].get(e)
            if not m:
                continue
            hist = {x["event"]: x for x in m["history"]["current"]}
            used = []
            for c in m["history"]["chips"]:
                x = hist.get(c["event"])
                net = x["points"] - x["event_transfers_cost"] if x else "?"
                used.append(f"{c['name']} GW{c['event']} ({net} pts)")
            rows.append([names[e], ", ".join(used) or "none"])
        h.append(table(["Team", "Chips (bboost=Bench Boost, wildcard, 3xc=Triple Captain, freehit)"], rows))

        h.append("<h2>Squads (latest gameweek picks)</h2>")
        for e in entries:
            m = lg["managers"].get(e)
            if not m or not m.get("picks"):
                continue
            pk = m["picks"]
            hist = m["history"]["current"]
            hits = sum(x["event_transfers_cost"] for x in hist)
            bench = sum(x["points_on_bench"] for x in hist)
            h.append(f"<h3>{esc(names[e])} (GW{pk['event']}, chip: {esc(pk.get('active_chip') or 'none')})</h3>")
            h.append(f"<p>Total transfers: {sum(x['event_transfers'] for x in hist)}, hit points: {hits}, points left on bench: {bench}.</p>")
            rows = []
            for p in pk["picks"]:
                pl = players[p["element"]]
                tag = "C" if p["is_captain"] else ("VC" if p["is_vice_captain"] else "")
                role = "XI" if p["position"] <= 11 else "bench"
                rows.append([role, POS[pl["element_type"]], pl["web_name"], teams[pl["team"]], f"{pl['now_cost']/10:.1f}", tag, pl["total_points"], pl["form"]])
            h.append(table(["Role", "Pos", "Player", "Team", "Price", "Armband", "Season pts", "Form"], rows))

    h.append("<h2>Players flagged (injury / doubt), owned by 5%+</h2>")
    fl = [p for p in b["elements"] if (p.get("news") or p.get("chance_of_playing_next_round") not in (None, 100)) and float(p["selected_by_percent"]) >= 5]
    fl.sort(key=lambda p: -float(p["selected_by_percent"]))
    h.append(table(["Player", "Team", "Owned %", "Chance next GW", "News"],
                   [[p["web_name"], teams[p["team"]], p["selected_by_percent"],
                     "?" if p.get("chance_of_playing_next_round") is None else f"{p['chance_of_playing_next_round']}%", p["news"]] for p in fl[:25]]))

    for t in (1, 2, 3, 4):
        h.append(f"<h2>Top 15 {POS[t]} by season points</h2>")
        ps = sorted([p for p in b["elements"] if p["element_type"] == t], key=lambda p: -p["total_points"])[:15]
        h.append(table(["Player", "Team", "Price", "Pts", "Form", "Owned %", "Mins", "xGI/90", "DefCon/90", "Status"],
                       [[p["web_name"], teams[p["team"]], f"{p['now_cost']/10:.1f}", p["total_points"], p["form"], p["selected_by_percent"],
                         p["minutes"], p.get("expected_goal_involvements_per_90", ""), p.get("defensive_contribution_per_90", ""),
                         p["status"] + (": " + p["news"] if p["news"] else "")] for p in ps]))

    h.append(NAV)
    h.append("</body></html>")
    open(dst, "w", encoding="utf-8").write("\n".join(h))
    build_full_pages(d, outdir)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
