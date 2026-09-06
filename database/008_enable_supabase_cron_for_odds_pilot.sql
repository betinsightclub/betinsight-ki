-- BetInsight KI – enable Supabase Cron for the odds pilot
-- Stand: 2026-09-06

create extension if not exists pg_cron with schema pg_catalog;
grant usage on schema cron to postgres;
grant all privileges on all tables in schema cron to postgres;
