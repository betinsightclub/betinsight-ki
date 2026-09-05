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

## Auswirkungen auf bestehendes BetInsight

Keine. Es wurde keine Verbindung zu `app.betinsight.club`, Make, Google Sheets oder bestehenden produktiven Repositories hergestellt.

## Technische Dateien

- `docs/ARCHITECTURE_v0.1.md`
- `docs/DATA_MODEL_v0.1.md`
- `docs/API_FOOTBALL_FREE_TEST_2026-09-06.md`
- `database/001_initial_schema.sql`
- `database/002_seed_v04.sql`
- `database/002_harden_trigger_search_path.sql`
- `database/003_api_football_probe_support.sql`
- `database/004_fix_api_football_http_headers.sql`

## Nächster Schritt

Den Master-Datensatz zunächst in eine kontrollierte Import-/Staging-Pipeline übernehmen und vor Normalisierung die Kickoff-Zeitzonen der Quelle verifizieren. Parallel die laufende API-Football-Ingestion so planen, dass Odds-Snapshots zukünftig selbst gespeichert werden. Der Backtest v0.4 und insbesondere der 2025/26-Hold-out bleiben davon unberührt.
