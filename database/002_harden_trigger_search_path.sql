-- BetInsight KI-/Datenplattform
-- Security hardening migration
-- Stand: 2026-09-06

alter function analysis.enforce_feature_asof_before_kickoff()
  set search_path = pg_catalog, analysis;

alter function analysis.enforce_decision_before_kickoff()
  set search_path = pg_catalog, analysis;
