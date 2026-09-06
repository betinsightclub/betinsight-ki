# Odds-Capture-Pilot v0.1

Stand: 06.09.2026

## Ziel

Einen vollständigen Bundesliga-Spieltag mit wenigen, klar definierten Pre-Match-Odds-Snapshots erfassen, bevor mehrere Ligen oder kostenpflichtige API-Tarife angebunden werden.

## Anbieterneutralität

Die Capture-Struktur ist absichtlich nicht exklusiv an API-Football gekoppelt. Ein späterer zweiter Anbieter oder ein Upgrade kann als zusätzliche `data_source` angebunden werden, ohne das Odds-Datenmodell neu zu bauen.

## Pilotprofil

- Liga: Bundesliga
- API-Football League ID: 78
- Saison: 2026
- Status: `prepared`
- Tagesbudget im Free-Test: 100 Requests

Das Profil bleibt vorerst `prepared`, weil der API-Football-Free-Plan aktuelle Saisonabfragen mit Liga/Season-Filter blockiert. Es wird erst aktiviert, wenn aktueller Zugriff vorhanden ist oder der Provider gewechselt wird.

## Vier Capture-Stufen

1. `first_observed` – erster von BetInsight tatsächlich beobachteter Wert. Niemals automatisch als Opening Odds bezeichnen.
2. `t_minus_24h` – ungefähr 24 Stunden vor Kickoff.
3. `t_minus_3h` – ungefähr 3 Stunden vor Kickoff.
4. `t_minus_30m` – ungefähr 30 Minuten vor Kickoff.

`last_pre_kickoff` wird später aus dem tatsächlich letzten Snapshot vor dem Kickoff abgeleitet und nicht als künstlicher fünfter Pflichtabruf erzeugt.

## Rohdatenprinzip

Jeder Capture speichert serverseitig:

- Provider
- externe Fixture-ID
- erwarteten Kickoff
- Capture-Stufe
- tatsächliches `captured_at`
- Request-Parameter
- HTTP-Status
- Ergebniszahl / Fehler
- unveränderte Provider-Response

Erst danach erfolgt Normalisierung in einzelne Bookmaker-/Market-/Selection-Quotes.

## Sicherheitsregeln

- Keine API-Keys in GitHub oder Browsercode.
- Keine Werte rückwirkend umetikettieren.
- `first_observed` ist nicht automatisch `opening`.
- `t_minus_30m` ist nicht automatisch `closing`.
- Ein Closing-/Last-Observed-Wert darf niemals als Opening verwendet werden.
- Fehlende Snapshots bleiben fehlend.
- Keine automatische kostenpflichtige Aktivierung.

## Aktueller technischer Stand

Supabase enthält die Tabellen:

- `analysis.odds_capture_profiles`
- `analysis.odds_capture_stages`
- `analysis.odds_raw_snapshots`

Zusätzlich existiert die serverseitige Funktion `analysis.capture_api_football_fixture_odds(...)` für kontrollierte Fixture-Captures.
