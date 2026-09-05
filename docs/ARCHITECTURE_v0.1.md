# BetInsight KI-/Datenplattform – Architektur v0.1

Stand: 06.09.2026

## Ziel

Vollständig getrennte interne Analyseplattform für historische Fußballanalyse, Backtests, Modellberechnung und spätere Freigabe von Tipps.

## Feste Trennung

- `app.betinsight.club` = bestehende Kunden-/Mitglieder-App – nicht verändern
- `ki.betinsight.club` = internes Analyse-Backoffice
- `api.betinsight.club` = spätere serverseitige API-/Backend-Schnittstelle
- PostgreSQL = zentrale Datenquelle für Match-, Odds-, Feature- und Backtestdaten
- Google Sheets = höchstens Export/Admin-Hilfsmittel, nicht Hauptdatenbank

## Zielarchitektur

`Fußball-Datenanbieter → Import/Backend → PostgreSQL → Feature-/Modellberechnung → ki.betinsight.club → Freigabe → bestehendes BetInsight-Tippsystem`

## Technologieentscheidung v0.1

### Datenbank

Bevorzugt: **Supabase PostgreSQL**.

Gründe:

- echtes PostgreSQL statt Tabellenkalkulation
- geeignet für hunderttausende bis Millionen normalisierte Match-/Odds-Zeilen bei sauberer Indizierung
- SQL, Views, Constraints, JSONB und Transaktionen
- später erweiterbar um Auth, Storage, Realtime und serverseitige Funktionen
- kostenloser Testbetrieb ist für den technischen Pilot vorgesehen; produktive Kapazität wird erst nach realem Datenvolumen bewertet

### Backend

Die Browser-Oberfläche auf `ki.betinsight.club` bekommt **keine geheimen Provider- oder Service-Schlüssel**.

Geplantes Muster:

`Browser → api.betinsight.club → serverseitige Logik → PostgreSQL / Fußball-API`

Für den ersten Supabase-Test darf die technische Backend-Adresse zunächst providerseitig bleiben. Die endgültige Zuordnung von `api.betinsight.club` wird erst vorgenommen, wenn der Backend-Dienst feststeht.

## Datenebenen

1. **Raw/Staging** – unveränderte Importzeilen und Import-Batches
2. **Core** – Länder, Wettbewerbe, Saisons, Teams, Fixtures, Ergebnisse
3. **Odds** – einzelne Markt-/Auswahlquoten mit Zeitbezug und Snapshot-Typ
4. **Quality** – bekannte Datenlücken und Validierungsstatus
5. **Model** – Modellversionen und streng zeitpunktbezogene Feature-Snapshots
6. **Backtest** – Runs, Bets, Resultate, ROI/Drawdown-Basisdaten
7. **Future** – Trainer, Spieler, Transfers, Verletzungen, Lineups, xG, Wetter
8. **Release** – Analyse-Kandidaten vor Übergabe an das bestehende Tippsystem

## Backtest-Schutz

Die Datenbankstruktur muss den eingefrorenen v0.4-Grundsatz unterstützen:

- strikt nach tatsächlichem Kickoff
- Feature-Werte erhalten einen `as_of_utc`-Zeitpunkt
- keine zukünftigen Informationen
- 2025/26 bleibt als finaler Hold-out gekennzeichnet
- Closing Odds werden nicht als Opening Odds umgedeutet
- fehlende Werte bleiben NULL und werden nicht erfunden

## Sicherheitsregeln

- keine API-Football-Schlüssel in GitHub Pages oder Browser-JavaScript
- keine Supabase-Service-Role-Keys im Repository
- `.env`-Dateien bleiben durch `.gitignore` ausgeschlossen
- öffentliche Browserzugriffe auf Datenbanktabellen standardmäßig sperren
- Row Level Security für analysebezogene Tabellen aktivieren; serverseitiger Zugriff erfolgt kontrolliert
- keine direkte Schreibverbindung zum bestehenden BetInsight-Kundensystem in Phase 1

## Nicht Teil dieses Schritts

- keine Änderung an Make
- keine Änderung an Google Sheets
- kein `api.betinsight.club` DNS-Eintrag
- keine produktive Übergabe an `app.betinsight.club`
- kein neues Backtest-Regelwerk
