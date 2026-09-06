# The Odds API Free-Test – 06.09.2026

## Zweck

Technischer Odds-Pilot für die BetInsight KI-/Fußballanalyseplattform. Kein Backtest und keine Änderung am eingefrorenen Regelwerk v0.4.

Der API-Key liegt ausschließlich im Supabase Vault unter `the_odds_api_key` und wird weder in GitHub noch im Browsercode gespeichert.

## Free-Plan

- 500 Credits pro Monat.
- Historical Odds sind im Free-Plan nicht enthalten.
- Der Sports-Endpunkt kostet 0 Credits.

## Bundesliga-Abdeckung

Live über den echten API-Zugang bestätigt:

- Bundesliga: `soccer_germany_bundesliga`
- 2. Bundesliga: `soccer_germany_bundesliga2`
- 3. Liga: `soccer_germany_liga3`

Alle drei wurden als aktiv gemeldet.

## Aktuelle Bundesliga-Odds

Für die Bundesliga wurden 11 aktuelle/kommende Events gefunden.

Ein EU-Regionsabruf mit `h2h` und `totals` lieferte:

- 24 Buchmacher
- 1X2 / Head-to-Head
- Over/Under Totals
- u. a. Total-Linien 2.5, 2.75, 3.0, 3.25, 3.5, 4.0 und 4.5

Zusätzlich getestete Märkte an HSV – Mainz:

- `btts` erfolgreich; 4 Buchmacher mit Yes/No-Quoten.
- `alternate_totals` erfolgreich; 6 Buchmacher.
- verfügbare Alternate-Total-Linien reichten von 0.5 bis 7.5 und enthielten insbesondere 0.5, 1.5, 2.5, 3.5 und 4.5.

Damit deckt The Odds API die für BetInsight wichtigen aktuellen 1X2-, Over/Under- und BTTS-Märkte grundsätzlich ab.

## Pilot-Spieltag

Ziel-Fenster: Bundesliga-Spiele vom 11.09.2026 bis 13.09.2026.

Vier Capture-Stufen:

1. `first_observed`
2. `t_minus_24h`
3. `t_minus_3h`
4. `t_minus_30m`

`first_observed` wird nicht als Opening Odds bezeichnet. `t_minus_30m` wird nicht automatisch als Closing Odds bezeichnet. Der tatsächliche letzte beobachtete Pre-Match-Snapshot wird später aus `captured_at` abgeleitet.

## Erster echter Snapshot

Am 06.09.2026 wurde `first_observed` für alle 9 Spiele des Ziel-Spieltags gespeichert.

Ergebnis:

- 9 erfolgreiche Captures
- 0 Fehler
- 0 leere Captures
- je Spiel 18 bis 20 Buchmacher
- Märkte vorhanden: `h2h`, `totals`, `btts`, `alternate_totals`; bei Exchanges zusätzlich `h2h_lay`

Der erste Spieltags-Snapshot verbrauchte 36 Credits.

Zusammen mit den vorherigen Tests waren danach 40 von 500 Credits verbraucht; 460 Credits blieben verfügbar.

## Automatisierung

Supabase Cron wurde aktiviert.

Job: `betinsight_bundesliga_odds_pilot_due`

- Intervall: alle 10 Minuten
- bis 10.09.2026 17:30 UTC nur Wartestatus, keine Odds-Abfragen
- danach werden nur tatsächlich fällige 24h-, 3h- und 30min-Stufen erfasst
- bereits erfolgreiche Stufen werden nicht erneut abgerufen
- nach 14.09.2026 02:00 UTC wird das Pilotprofil auf `completed` gesetzt und der Cron-Job selbstständig entfernt

## Architekturentscheidung

- The Odds API wird im Pilot als aktuelle Odds-Quelle verwendet.
- API-Football bleibt separat für Fixtures, Spieler, Trainer, Transfers, Lineups und weitere Fußballdaten.
- Die Odds-Capture-Struktur bleibt provider-neutral.
- Historische Master-Odds werden nicht durch aktuelle API-Daten überschrieben.
- Historical Odds von The Odds API werden erst geprüft, falls später bewusst ein kostenpflichtiger Tarif getestet wird.

## Auswirkungen auf bestehendes BetInsight

Keine. `app.betinsight.club`, Make, Google Sheets und die bestehenden produktiven Repositories wurden nicht verändert.
