# fpl-data

## Instructions for AI assistants (read this first)

All the information is on a small website, updated automatically every few hours. Open the start page and read it:
https://coolajnurk-create.github.io/fpl-data/

The start page is a summary (Holand Company mini league table, points per gameweek for every manager with rank in the league, chips used, every manager's current squad with captain, injury flags, top players). It links to pages with ALL the data as plain HTML tables, in the same domain:
- league_full.html: standings, and for every manager the full history, chips, picks and all transfers
- players_gk.html, players_def.html, players_mid.html, players_fwd.html: every player with every field
- fixtures.html: all fixtures, results, FDR, goal scorers and assists
- history_gk.html, history_def.html, history_mid.html, history_fwd.html: gameweek-by-gameweek stats of the top 100 players
- teams_events.html: teams, gameweeks and a glossary of field names
If the user asks about the league or their team, answer from these pages. Do not guess. If a page does not load, say so and ask the user to paste its text.

Raw JSON (only if you can run code): https://coolajnurk-create.github.io/fpl-data/league.json and https://coolajnurk-create.github.io/fpl-data/fpl_data.json (3.3 MB, often fails to load in chat tools). They are also on the `data` branch.

Who is who (league Holand Company, ID 322114):
- baklava taktika = Ajnur Kurtović, entry 2124129
- ManUtd = Amar Aganović, entry 1479223
- deva_utd = Emir Devic, entry 2757164
- Ne_da_mi_igrica = Ajdin Beg, entry 1742021
- Sedrenik FC (user may call it "Sedrenik city") = Admir Kurtovic, entry 1696365
- Royal Kings 8881832, Beton Ligaši 1699329, VAR 3023199, Irgeti FC 1849551, Pomahnitali 2741325, Mustajbegalickog 1918336

## Where the files are

- Player and fixture data (auto-updated, large, 3.3 MB): `fpl_data.json` on the `data` branch: https://raw.githubusercontent.com/coolajnurk-create/fpl-data/data/fpl_data.json
- Updater script: `fpl_update.py` on the `main` branch
- Workflow: `.github/workflows/update.yml` on the `main` branch
- Schedule (UTC): light update every 20 minutes at :07, :27 and :47, full update every 3 hours at :30

## Mini-league Holand Company (league ID 322114)

The files in `league/` on `main` are one-time snapshots and do not update by themselves. Snapshot taken: 2026-11-08 18:38 UTC (old snapshot, use league.json on the data branch instead)

- Standings table: `league/standings.json`, live: https://fantasy.premierleague.com/api/leagues-classic/322114/standings/

| Team | Entry ID | Snapshot file | Live link |
|---|---|---|---|
| baklava taktika | 2124129 | `league/managers/2124129_baklava-taktika_history.json` | https://fantasy.premierleague.com/api/entry/2124129/history/ |
| ManUtd | 1479223 | `league/managers/1479223_manutd_history.json` | https://fantasy.premierleague.com/api/entry/1479223/history/ |
| deva_utd | 2757164 | `league/managers/2757164_deva-utd_history.json` | https://fantasy.premierleague.com/api/entry/2757164/history/ |
| Ne_da_mi_igrica | 1742021 | `league/managers/1742021_ne-da-mi-igrica_history.json` | https://fantasy.premierleague.com/api/entry/1742021/history/ |
| Royal Kings | 8881832 | `league/managers/8881832_royal-kings_history.json` | https://fantasy.premierleague.com/api/entry/8881832/history/ |
| Beton Ligaši | 1699329 | `league/managers/1699329_beton-ligasi_history.json` | https://fantasy.premierleague.com/api/entry/1699329/history/ |
| VAR | 3023199 | `league/managers/3023199_var_history.json` | https://fantasy.premierleague.com/api/entry/3023199/history/ |
| Sedrenik FC | 1696365 | `league/managers/1696365_sedrenik-fc_history.json` | https://fantasy.premierleague.com/api/entry/1696365/history/ |
| Irgeti FC | 1849551 | `league/managers/1849551_irgeti-fc_history.json` | https://fantasy.premierleague.com/api/entry/1849551/history/ |
| Pomahnitali | 2741325 | `league/managers/2741325_pomahnitali_history.json` | https://fantasy.premierleague.com/api/entry/2741325/history/ |
| Mustajbegalickog | 1918336 | `league/managers/1918336_mustajbegalickog_history.json` | https://fantasy.premierleague.com/api/entry/1918336/history/ |

Other live endpoints (replace the entry ID and the gameweek number):
- Picks of a gameweek: https://fantasy.premierleague.com/api/entry/2124129/event/10/picks/
- Transfers: https://fantasy.premierleague.com/api/entry/2124129/transfers/
- Entry info and leagues: https://fantasy.premierleague.com/api/entry/2124129/
