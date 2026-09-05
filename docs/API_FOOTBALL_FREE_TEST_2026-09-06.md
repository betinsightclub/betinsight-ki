# API-Football Free-Test – 06.09.2026

## Zweck

Technischer Eignungstest von API-Football für die neue BetInsight KI-/Datenplattform. Kein Backtest und keine Änderung am eingefrorenen Regelwerk v0.4.

Der API-Key liegt ausschließlich verschlüsselt im Supabase Vault unter `api_football_key`. Er ist weder in GitHub noch im Browsercode gespeichert.

## Getestete Hauptligen

Alle folgenden League-IDs wurden über den echten API-Zugang mit HTTP 200 bestätigt:

- Premier League – ID 39 – England
- Championship – ID 40 – England
- Bundesliga – ID 78 – Deutschland
- 2. Bundesliga – ID 79 – Deutschland
- 3. Liga – ID 80 – Deutschland
- Primeira Liga / Liga Portugal – ID 94 – Portugal
- Serie A – ID 135 – Italien
- La Liga – ID 140 – Spanien

Für die aktuelle Saison 2026 meldet die League-Metadatenabfrage bei allen acht Wettbewerben Odds- und Lineup-Coverage. Injury-Coverage ist laut Metadaten vorhanden bei Premier League, Championship, Bundesliga, Serie A und La Liga; bei 2. Bundesliga, 3. Liga und Primeira Liga wurde `injuries=false` gemeldet.

## Zusätzlich geprüfte europäische Ligen

Ebenfalls HTTP 200 und aktuelle League-Metadaten bestätigt:

- Eredivisie – ID 88 – Niederlande
- Jupiler Pro League – ID 144 – Belgien
- Super League – ID 207 – Schweiz
- Bundesliga – ID 218 – Österreich

Bei allen vier meldet die aktuelle Saison Odds- und Lineup-Coverage. Injury-Coverage wurde bei Eredivisie als verfügbar, bei Belgien, Schweiz und Österreich als nicht verfügbar gemeldet.

## Free-Plan-Saisonzugriff

Wichtiger Live-Test:

- `fixtures`, Bundesliga, Saison 2026 → abgelehnt mit Plan-Hinweis: Free-Zugang erlaubt derzeit Saisons 2022 bis 2024.
- `fixtures`, Bundesliga, Saison 2024, Datumsfenster 23.–25.08.2024 → erfolgreich, 9 Spiele.
- `fixtures`, Bundesliga, Saison 2022, Datumsfenster 05.–07.08.2022 → erfolgreich, 9 Spiele.
- Der Parameter `last` ist im Free-Plan nicht verfügbar.

Folgerung: Der Free-Zugang eignet sich zum technischen Testen, aber nicht für den vollständigen historischen BetInsight-Zeitraum 2021/22 bis 2025/26.

## Getestete Endpoints mit echtem Datenabruf

An einem Bundesliga-Spiel vom 23.08.2024 (Borussia Mönchengladbach – Bayer Leverkusen) wurden folgende Endpoints geprüft:

- `/fixtures/lineups` → erfolgreich, 2 Aufstellungen; Formation u. a. 4-2-3-1.
- `/injuries` → erfolgreich, 4 Einträge.
- `/players` → erfolgreich, 20 Einträge auf Seite 1; Pagination vorhanden.
- `/coachs` → erfolgreich.
- `/transfers` → erfolgreich; umfangreicher Transferbestand vorhanden.

## Odds

### Pre-Match Odds

- `/odds` für das historische Bundesliga-Spiel vom 23.08.2024 → HTTP 200, aber 0 Ergebnisse.
- `/odds` für das aktuelle Datum 06.09.2026 → erfolgreich, 10 Ergebnisse auf Seite 1, insgesamt 57 Seiten; Beispielantwort mit William Hill und 44 angebotenen Bet-Typen.
- Anfrage für 12.09.2026 wurde im Free-Plan mit einem Datumsfenster-Hinweis abgelehnt; zum Testzeitpunkt war im Free-Zugang nur 04.–06.09.2026 freigegeben.

Die offizielle API-Football-Dokumentation weist zusätzlich darauf hin, dass Pre-Match-Odds nur sieben Tage historisch vorgehalten werden. Historische Odds müssen deshalb laufend gespeichert werden; sie können nicht Jahre später aus API-Football rekonstruiert werden.

### Live Odds

- `/odds/live` ohne Filter → erfolgreich, 25 Live-Odds-Datensätze zum Testzeitpunkt.
- Laut offizieller API-Football-Dokumentation werden Live-Odds nicht historisch gespeichert. Für spätere Analysen müssen sie in Echtzeit aufgenommen werden.

## Technische Bewertung

API-Football ist geeignet für:

- League-/Season-Metadaten
- Fixtures und Ergebnisse innerhalb des gebuchten Saisonumfangs
- Lineups
- Spieler
- Trainer
- Transfers
- Verletzungen, sofern die jeweilige Liga dies unterstützt
- laufende Pre-Match-Odds-Erfassung
- laufende Live-Odds-Erfassung

API-Football ist **nicht** geeignet, um fehlende historische BetInsight-Odds aus mehreren vergangenen Jahren rückwirkend zu beschaffen, da die Odds-Historie nur sehr kurz vorgehalten wird.

## Konsequenz für BetInsight

1. Den bestehenden historischen Master nicht durch API-Football-Odds ersetzen.
2. Bestehende historische Odds weiterhin als eigene historische Quelle behandeln.
3. API-Football kann künftig als laufende Datenquelle dienen.
4. Neue Pre-Match- und Live-Odds müssen ab dem Startzeitpunkt selbst in PostgreSQL gesnapshottet werden.
5. Opening und Closing bleiben getrennte Snapshot-Typen. Niemals Closing als Opening umdeuten.
6. 2025/26 bleibt im Backtest unangetasteter Hold-out; dieser Infrastrukturtest ändert daran nichts.

## Verbrauch

Für den Test wurden 27 serverseitig protokollierte API-Probes ausgeführt. Der Free-Tarif hat 100 Requests pro Tag und 10 Requests pro Minute; die Tests wurden entsprechend gedrosselt.
