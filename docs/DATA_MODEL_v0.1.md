# Datenmodell v0.1

Stand: 06.09.2026

Ausgangspunkt ist `BetInsight_Backtest_Master_2021-2026.xlsx` mit 8.758 regulären Ligaspielen und den Spalten:

`id, kickoff, Country, League, Season, homeTeam, awayTeam, referee, FTHG, FTAG, FTR, H, D, A, O05, U05, O15, U15, O25, U25, O35, U35, O45, U45, BTTSY, BTTSN, DataFlag`.

## Normalisierung

Der Master wird nicht als eine einzige breite Dauertabelle übernommen. Stattdessen werden Stammdaten, Spiele, Odds und Qualitätsinformationen getrennt gespeichert.

### Kernobjekte

- `data_sources` – Datenanbieter/Quellexporte
- `import_batches` – einzelne Imports mit Dateiname, Hash und Status
- `raw_import_rows` – optionale unveränderte Rohzeilen als JSONB
- `countries`
- `competitions`
- `seasons`
- `teams`
- `fixtures`
- `fixture_external_ids` – externe IDs je Anbieter
- `odds_quotes` – eine Quote pro Markt/Auswahl/Linie/Snapshot
- `data_quality_issues`

### Modell-/Backtestobjekte

- `model_versions`
- `feature_snapshots` – Feature-Stand je Spiel mit `as_of_utc`
- `backtest_runs`
- `backtest_bets`
- `analysis_candidates` – spätere interne Freigabeebene

### Spätere Erweiterungen

- `coaches`
- `team_coach_tenures`
- `players`
- `team_player_stints`
- `transfers`
- später Verletzungen, Lineups, xG, Wetter und weitere Pflichtspiele

## Mapping des aktuellen Masters

| Master-Spalte | Ziel |
|---|---|
| `id` | `fixture_external_ids.external_id` für die aktuelle Quelle |
| `kickoff` | `fixtures.kickoff_utc` |
| `Country` | `countries.name` |
| `League` | `competitions.name` |
| `Season` | `seasons.label` |
| `homeTeam` | `teams.name` + `fixtures.home_team_id` |
| `awayTeam` | `teams.name` + `fixtures.away_team_id` |
| `referee` | `fixtures.referee_name` |
| `FTHG` | `fixtures.home_goals` |
| `FTAG` | `fixtures.away_goals` |
| `FTR` | `fixtures.full_time_result` |
| `H`,`D`,`A` | `odds_quotes`, market=`1X2`, selection=`H/D/A` |
| `O05`…`U45` | `odds_quotes`, market=`TOTAL_GOALS`, selection=`OVER/UNDER`, line=`0.5…4.5` |
| `BTTSY`,`BTTSN` | `odds_quotes`, market=`BTTS`, selection=`YES/NO` |
| `DataFlag` | `fixtures.data_flag` und bei Bedarf `data_quality_issues` |

## Odds-Regel

Die historischen Footiqo-Odds des Masters werden als **Closing Odds** behandelt. Fehlende Preise bleiben `NULL`; es werden keine synthetischen Werte ergänzt.

## Hold-out-Regel

`seasons.dataset_role` unterscheidet:

- `development` → 2021/22–2023/24
- `validation` → 2024/25
- `holdout` → 2025/26

Dadurch lässt sich der finale Hold-out technisch eindeutig sperren bzw. separat auswerten.
