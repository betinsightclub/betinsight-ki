# Logbuch-Addendum – 06.09.2026

Dieses Addendum ersetzt keine frühere Logbuchversion. Es dokumentiert ausschließlich neue technische Architekturentscheidungen und Testergebnisse.

## Änderung 1 – Backend-/Datenbank-Architektur v0.1

### Entscheidung

- PostgreSQL wird Hauptdatenbank der KI-/Fußballanalyseplattform.
- Supabase PostgreSQL wird als bevorzugter erster Managed-Postgres-Test festgelegt.
- Google Sheets wird nicht als Hauptspeicher für Match-/Odds-Massendaten verwendet.
- Browser und GitHub Pages erhalten keine geheimen API-/Service-Schlüssel.
- `api.betinsight.club` wird erst eingerichtet, wenn der konkrete serverseitige Backend-Endpunkt feststeht.
- Die Datenbank erhält getrennte Ebenen für Raw Import, Core Football, Odds, Datenqualität, Features, Backtests und spätere Freigabe.
- 2025/26 wird technisch als `holdout` mit `locked_for_model_selection = true` markiert.
- Historische Footiqo-Odds des bestehenden Masters werden als Closing Odds behandelt.
- Fehlende Werte bleiben NULL; keine Schätzwerte werden erzeugt.

### Begründung

Die vorhandenen 8.758 Spiele sind bereits größer und strukturierter als ein sinnvoller Google-Sheets-Hauptbestand. Zukünftige API-Daten, Odds-Snapshots, Spieler, Trainer, Transfers, Lineups und Feature-Snapshots erhöhen die Zeilenzahl stark. PostgreSQL bietet dafür Constraints, Indizes, Transaktionen und zeitpunktbezogene Abfragen.

## Änderung 2 – Supabase-Testdatenbank eingerichtet

- Separates Schema `analysis` angelegt.
- 21 fachliche Tabellen für Datenquellen, Imports, Fußball-Kerndaten, Odds, Datenqualität, Modell-/Feature-Snapshots, Backtests, Analyse-Kandidaten sowie spätere Trainer-/Spieler-/Transferdaten angelegt.
- RLS auf allen `analysis`-Tabellen aktiviert.
- Direkter Zugriff für `anon` und `authenticated` auf das interne Schema entzogen.
- Trigger verhindern Feature-Snapshots bzw. Backtest-Entscheidungen nach dem tatsächlichen Kickoff.
- API-Schlüssel bleiben außerhalb von GitHub und Browsercode.

## Änderung 3 – API-Football Free-Test

### Getestete Hauptligen

Mit echtem API-Zugang erfolgreich als Wettbewerbe bestätigt:

- Premier League (39)
- Championship (40)
- Bundesliga (78)
- 2. Bundesliga (79)
- 3. Liga (80)
- Primeira Liga / Liga Portugal (94)
- Serie A (135)
- La Liga (140)

Zusätzlich geprüft: Eredivisie (88), Jupiler Pro League (144), Schweizer Super League (207), Österreichische Bundesliga (218).

### Free-Plan-Grenzen

- Der Free-Zugang erlaubte beim Fixture-Test aktuell Saisons 2022 bis 2024.
- Bundesliga 2022 und 2024 wurden erfolgreich mit echten Fixtures getestet.
- Saison 2026 wurde beim Fixture-Abruf durch den Free-Plan abgelehnt.
- Der Parameter `last` war im Free-Plan nicht verfügbar.

### Endpoints

Erfolgreich mit echten Antworten getestet:

- Leagues / Season-Coverage
- Fixtures / Ergebnisse
- Lineups
- Injuries
- Players
- Coachs
- Transfers
- Pre-Match Odds
- Live Odds

### Kritische Odds-Erkenntnis

Ein historischer Bundesliga-Fixture vom 23.08.2024 lieferte über `/odds` keine historischen Odds mehr. Dagegen lieferte der aktuelle Pre-Match-Odds-Endpunkt echte Daten. Die offizielle API-Football-Dokumentation nennt eine Pre-Match-Odds-Historie von nur sieben Tagen; Live-Odds werden nicht historisch gespeichert.

**Konsequenz:** API-Football kann fehlende historische BetInsight-Odds aus mehreren Jahren nicht rückwirkend ersetzen. Für zukünftige Analysen müssen Pre-Match- und Live-Odds ab dem Startzeitpunkt selbst in PostgreSQL als zeitgestempelte Snapshots gespeichert werden. Opening und Closing bleiben strikt getrennt.

## Änderung 4 – Anbieterneutraler Bundesliga-Odds-Pilot vorbereitet

### Entscheidung

- Zunächst nur ein kompletter Bundesliga-Spieltag als Pilot.
- Vier Pre-Match-Capture-Stufen: `first_observed`, `t_minus_24h`, `t_minus_3h`, `t_minus_30m`.
- `first_observed` wird ausdrücklich nicht automatisch als Opening Odds bezeichnet.
- Der tatsächlich letzte Snapshot vor Kickoff wird später aus `captured_at` abgeleitet und nicht künstlich als Closing umetikettiert.
- Rohantworten werden zuerst unverändert gespeichert und erst danach normalisiert.
- Die Capture-Struktur ist provider-neutral, damit später API-Football, ein zweiter Anbieter oder ein Upgrade ohne neues Datenmodell genutzt werden kann.

### Free-Plan-Status

Ein zusätzlicher Live-Test bestätigte: API-Football verlangt bei liga-spezifischen Pre-Match-Odds den Season-Parameter; Saison 2026 wird im Free-Plan blockiert. Das ursprüngliche API-Football-Pilotprofil bleibt deshalb nur als vorbereitete Alternative bestehen.

### Neue Tabellen / Funktion

- `analysis.odds_capture_profiles`
- `analysis.odds_capture_stages`
- `analysis.odds_raw_snapshots`
- `analysis.capture_api_football_fixture_odds(...)`

Es wurde keine automatische kostenpflichtige Nutzung eingerichtet.

## Änderung 5 – The Odds API als zweite Odds-Quelle getestet und Bundesliga-Pilot aktiviert

### Free-Test

The Odds API wurde als zweite Datenquelle registriert. Der Schlüssel liegt ausschließlich im Supabase Vault unter `the_odds_api_key`.

Live bestätigt:

- Bundesliga: `soccer_germany_bundesliga`
- 2. Bundesliga: `soccer_germany_bundesliga2`
- 3. Liga: `soccer_germany_liga3`

Für die Bundesliga lieferte ein EU-Regionsabruf mit `h2h` und `totals` 11 aktuelle/kommende Spiele und 24 Buchmacher. Zusätzlich wurden `btts` und `alternate_totals` erfolgreich getestet.

Die Alternate Totals enthielten u. a. 0.5, 1.5, 2.5, 3.5 und 4.5 und decken damit die für BetInsight relevanten Over/Under-Linien grundsätzlich ab.

### Erster echter Spieltags-Snapshot

Ziel-Spieltag: 11.–13.09.2026.

`first_observed` wurde am 06.09.2026 für alle 9 Zielspiele gespeichert:

- 9 erfolgreiche Captures
- 0 Fehler
- 0 leere Captures
- 18 bis 20 Buchmacher je Spiel
- Märkte: `h2h`, `totals`, `btts`, `alternate_totals`; bei Exchanges zusätzlich `h2h_lay`

Der Snapshot-Lauf verbrauchte 36 Credits. Einschließlich der vorherigen Tests waren danach 40 von 500 Monats-Credits verbraucht; 460 blieben verfügbar.

### Automatisierung

Supabase Cron wurde aktiviert.

Job: `betinsight_bundesliga_odds_pilot_due`

- läuft technisch alle 10 Minuten
- bis 10.09.2026 17:30 UTC nur Wartestatus, keine Odds-Abfragen
- danach werden nur tatsächlich fällige `t_minus_24h`, `t_minus_3h` und `t_minus_30m` Captures geschrieben
- bereits erfolgreiche Stufen werden nicht erneut abgefragt
- nach 14.09.2026 02:00 UTC wird das Pilotprofil auf `completed` gesetzt und der Cron-Job selbstständig entfernt

### Anbietertrennung

- The Odds API: aktueller Odds-Pilot.
- API-Football: weiterhin für Fixtures, Spieler, Trainer, Transfers, Lineups und weitere Fußballdaten vorgesehen.
- Historische Master-Odds werden nicht überschrieben.
- Historical Odds von The Odds API sind im Free-Plan nicht enthalten und werden erst bei einer bewussten späteren Tarifentscheidung geprüft.

## Auswirkungen auf bestehendes BetInsight

Keine. Es wurde keine Verbindung zu `app.betinsight.club`, Make, Google Sheets oder bestehenden produktiven Repositories hergestellt.

## Technische Dateien

- `docs/ARCHITECTURE_v0.1.md`
- `docs/DATA_MODEL_v0.1.md`
- `docs/API_FOOTBALL_FREE_TEST_2026-09-06.md`
- `docs/THE_ODDS_API_FREE_TEST_2026-09-06.md`
- `docs/ODDS_CAPTURE_PILOT_v0.1.md`
- `database/001_initial_schema.sql`
- `database/002_seed_v04.sql`
- `database/002_harden_trigger_search_path.sql`
- `database/003_api_football_probe_support.sql`
- `database/004_fix_api_football_http_headers.sql`
- `database/005_odds_capture_pilot_provider_neutral.sql`
- `database/006_the_odds_api_probe_support.sql`
- `database/007_the_odds_api_bundesliga_pilot_capture.sql`
- `database/008_enable_supabase_cron_for_odds_pilot.sql`
- `database/009_schedule_bundesliga_odds_pilot.sql`

## Nächster Schritt

Den automatischen Bundesliga-Pilot bis nach dem Spieltag 11.–13.09.2026 laufen lassen und anschließend Vollständigkeit, tatsächliche Capture-Zeitpunkte, Buchmacherabdeckung und Quotenbewegungen vergleichen. Parallel kann der historische Master kontrolliert über Staging importiert werden. Keine Tarifentscheidung vor Auswertung des kostenlosen Piloten. Der Backtest v0.4 und insbesondere der 2025/26-Hold-out bleiben davon unberührt.
