# BetInsight KI-/Datenplattform

Separates Repository für die neue BetInsight Analyse- und KI-Plattform.

## Trennung vom bestehenden System

Dieses Repository gehört **nicht** zur bestehenden Kunden-/Mitglieder-App.

- `app.betinsight.club` → bestehende Kunden-App im Repository `profil` – nicht verändern
- `betinsight.club` → öffentliche Website im Repository `website` – nicht verändern
- `betinsight.network` → bestehender Network-Bereich – nicht verändern
- `ki.betinsight.club` → neue interne Analyse-/KI-Oberfläche aus diesem Repository
- `api.betinsight.club` → später geplante serverseitige API-/Backend-Schnittstelle

## Zielarchitektur

`Football-Datenanbieter → Import/Backend → PostgreSQL-Datenbank → Feature-/Modellberechnung → ki.betinsight.club → Freigabe → bestehendes BetInsight-Tippsystem`

## Datenbankentscheidung v0.1

- PostgreSQL wird Hauptdatenbank der Analyseplattform.
- Supabase PostgreSQL ist der bevorzugte erste Managed-Postgres-Test.
- Google Sheets wird nicht als Hauptdatenbank für Match-/Odds-Massendaten verwendet.
- Das vorbereitete Schema liegt unter `database/`.
- Architektur und Datenmodell liegen unter `docs/`.

## Sicherheitsregeln

- Keine API-Schlüssel, Passwörter oder Service-Keys im Browsercode oder Repository speichern.
- Secrets ausschließlich serverseitig bzw. in dafür vorgesehenen Secret-/Environment-Systemen verwalten.
- Keine produktiven Make-Szenarien, Google-Sheets-Strukturen oder bestehenden BetInsight-Repositories aus diesem Projekt heraus überschreiben.
- Vor jeder späteren produktiven Verbindung zuerst den aktuellen Live-Stand prüfen.
- API-Football zunächst nur im kostenlosen Testbetrieb prüfen.
- Öffentliche Browserzugriffe auf Analyse-Datenbanktabellen standardmäßig sperren.

## Aktueller Stand

- `ki.betinsight.club` → GitHub Pages aktiv, DNS erfolgreich, HTTPS erzwungen.
- PostgreSQL-/Supabase-Architektur v0.1 → vorbereitet.
- Initiales Datenbankschema und v0.4-Seed → vorbereitet, noch nicht in einer externen Datenbank ausgeführt.
- `api.betinsight.club` → noch nicht eingerichtet.
- Keine produktive Verbindung zu Make, Google Sheets oder `app.betinsight.club`.

## Nächster Schritt

Supabase-Testprojekt verbinden/anlegen, Migrationen aus `database/` ausführen und danach den historischen Master über eine kontrollierte Staging-Pipeline importieren. Vor der Normalisierung der Kickoff-Zeitpunkte wird die Zeitzonenbasis der Quelldaten verifiziert.
