-- BetInsight KI – schedule Bundesliga odds pilot
-- Stand: 2026-09-06
-- The cron job waits until 2026-09-10 17:30 UTC before external checks begin.
-- It auto-completes and unschedules after 2026-09-14 02:00 UTC.

create or replace function analysis.run_bundesliga_odds_pilot_cron()
returns jsonb
language plpgsql
security definer
set search_path = analysis, cron, pg_catalog
as $$
declare
  v_now timestamptz := now();
  v_result jsonb;
begin
  if v_now < '2026-09-10T17:30:00Z'::timestamptz then
    return jsonb_build_object('status','waiting','next_active_window','2026-09-10T17:30:00Z');
  end if;

  if v_now > '2026-09-14T02:00:00Z'::timestamptz then
    update analysis.odds_capture_profiles
    set status='completed', updated_at=now()
    where code='bundesliga_the_odds_api_pilot';

    if exists (select 1 from cron.job where jobname='betinsight_bundesliga_odds_pilot_due') then
      perform cron.unschedule('betinsight_bundesliga_odds_pilot_due');
    end if;

    return jsonb_build_object('status','completed','cron_unscheduled',true);
  end if;

  select analysis.capture_the_odds_api_due('bundesliga_the_odds_api_pilot', false)
  into v_result;
  return v_result;
end;
$$;

revoke all on function analysis.run_bundesliga_odds_pilot_cron() from public, anon, authenticated;

update analysis.odds_capture_profiles
set status='active', updated_at=now()
where code='bundesliga_the_odds_api_pilot';

do $$
begin
  if exists (select 1 from cron.job where jobname='betinsight_bundesliga_odds_pilot_due') then
    perform cron.unschedule('betinsight_bundesliga_odds_pilot_due');
  end if;
end
$$;

select cron.schedule(
  'betinsight_bundesliga_odds_pilot_due',
  '*/10 * * * *',
  $cron$select analysis.run_bundesliga_odds_pilot_cron();$cron$
);
