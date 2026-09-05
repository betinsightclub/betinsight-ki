# BetInsight KI-/Datenplattform

Separates Repository für die neue BetInsight Analyse- und KI-Oberfläche.

## Trennung vom bestehenden System

Dieses Repository gehört **nicht** zur bestehenden Kunden-/Mitglieder-App.

- `app.betinsight.club` → bestehende Kunden-App im Repository `profil` – nicht verändern
- `betinsight.club` → öffentliche Website im Repository `website` – nicht verändern
- `betinsight.network` → bestehender Network-Bereich – nicht verändern
- `ki.betinsight.club` → geplante neue Analyse-/KI-Oberfläche aus diesem Repository
- `api.betinsight.club` → später geplante serverseitige API-/Backend-Schnittstelle

## Geplante Architektur

`Football-Datenanbieter → Import/Backend → PostgreSQL-Datenbank → Feature-/Modellberechnung → ki.betinsight.club → Freigabe → bestehendes BetInsight-Tippsystem`

## Sicherheitsregeln

- Keine API-Schlüssel, Passwörter oder Service-Keys im Browsercode oder Repository speichern.
- Secrets ausschließlich serverseitig bzw. in dafür vorgesehenen Secret-/Environment-Systemen verwalten.
- Keine produktiven Make-Szenarien, Google-Sheets-Strukturen oder bestehenden BetInsight-Repositories aus diesem Projekt heraus überschreiben.
- Vor jeder späteren produktiven Verbindung zuerst den aktuellen Live-Stand prüfen.
- API-Football zunächst nur im kostenlosen Testbetrieb prüfen.

## Aktueller Stand

Phase 1 – technische Grundstruktur. Noch keine produktive API-, Datenbank-, DNS- oder Make-Verbindung.
