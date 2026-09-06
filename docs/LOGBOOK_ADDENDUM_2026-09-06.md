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

Ein zusätzlicher Live-Test bestätigte: API-Football verlangt bei liga-spezifischen Pre-Match-Odds den Season-Parameter; Saison 2026 wird im Free-Plan blockiert. Das Bundesliga-Pilotprofil bleibt deshalb technisch auf `prepared` und wird noch nicht automatisch aktiviert.

### Neue Tabellen / Funktion

- `analysis.odds_capture_profiles`
- `analysis.odds_capture_stages`
- `analysis.odds_raw_snapshots`
- `analysis.capture_api_football_fixture_odds(...)`

Es wurde keine automatische kostenpflichtige Nutzung eingerichtet.

## Auswirkungen auf bestehendes BetInsight

Keine. Es wurde keine Verbindung zu `app.betinsight.club`, Make, Google Sheets oder bestehenden produktiven Repositories hergestellt.

## Technische Dateien

- `docs/ARCHITECTURE_v0.1.md`
- `docs/DATA_MODEL_v0.1.md`
- `docs/API_FOOTBALL_FREE_TEST_2026-09-06.md`
- `docs/ODDS_CAPTURE_PILOT_v0.1.md`
- `database/001_initial_schema.sql`
- `database/002_seed_v04.sql`
- `database/002_harden_trigger_search_path.sql`
- `database/003_api_football_probe_support.sql`
- `database/004_fix_api_football_http_headers.sql`
- `database/005_odds_capture_pilot_provider_neutral.sql`

## Nächster Schritt

Noch keine kostenpflichtige Aktivierung. Als nächstes die Provider-Optionen für den aktuellen Bundesliga-Spieltag vergleichen: entweder günstiges API-Football-Upgrade oder ein zweiter Anbieter mit aktuellem Fixture-/Pre-Match-Odds-Zugriff. Die vorbereitete Capture-Pipeline bleibt dafür unverändert. Parallel kann der historische Master kontrolliert über Staging importiert werden. Der Backtest v0.4 und insbesondere der 2025/26-Hold-out bleiben davon unberührt.
