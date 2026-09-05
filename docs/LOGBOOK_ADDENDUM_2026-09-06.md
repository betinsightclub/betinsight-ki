# Logbuch-Addendum – 06.09.2026

Dieses Addendum ersetzt keine frühere Logbuchversion. Es dokumentiert ausschließlich die neue technische Architekturentscheidung.

## Änderung

Backend-/Datenbank-Architektur v0.1 festgelegt.

## Entscheidung

- PostgreSQL wird Hauptdatenbank der KI-/Fußballanalyseplattform.
- Supabase PostgreSQL wird als bevorzugter erster Managed-Postgres-Test festgelegt.
- Google Sheets wird nicht als Hauptspeicher für Match-/Odds-Massendaten verwendet.
- Browser und GitHub Pages erhalten keine geheimen API-/Service-Schlüssel.
- `api.betinsight.club` wird erst eingerichtet, wenn der konkrete serverseitige Backend-Endpunkt feststeht.
- Die Datenbank erhält getrennte Ebenen für Raw Import, Core Football, Odds, Datenqualität, Features, Backtests und spätere Freigabe.
- 2025/26 wird technisch als `holdout` mit `locked_for_model_selection = true` markiert.
- Historische Footiqo-Odds des bestehenden Masters werden als Closing Odds behandelt.
- Fehlende Werte bleiben NULL; keine Schätzwerte werden erzeugt.

## Begründung

Die vorhandenen 8.758 Spiele sind bereits größer und strukturierter als ein sinnvoller Google-Sheets-Hauptbestand. Zukünftige API-Daten, Odds-Snapshots, Spieler, Trainer, Transfers, Lineups und Feature-Snapshots erhöhen die Zeilenzahl stark. PostgreSQL bietet dafür Constraints, Indizes, Transaktionen und zeitpunktbezogene Abfragen.

## Auswirkungen auf bestehendes BetInsight

Keine. Es wurde keine Verbindung zu `app.betinsight.club`, Make, Google Sheets oder bestehenden produktiven Repositories hergestellt.

## Technische Dateien

- `docs/ARCHITECTURE_v0.1.md`
- `docs/DATA_MODEL_v0.1.md`
- `database/001_initial_schema.sql`
- `database/002_seed_v04.sql`

## Nächster Schritt

Supabase-Testprojekt verbinden/anlegen und die vorbereiteten Migrationen dort ausführen. Danach den Master-Datensatz zunächst in eine kontrollierte Import-/Staging-Pipeline übernehmen und vor Normalisierung die Kickoff-Zeitzonen der Quelle verifizieren.
