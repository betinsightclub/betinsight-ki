-- BetInsight KI – Bundesliga capture pilot via The Odds API
-- Stand: 2026-09-06

alter table analysis.odds_capture_profiles
  add column if not exists capture_window_start_utc timestamptz,
  add column if not exists capture_window_end_utc timestamptz;

with src as (
  select id from analysis.data_sources where code='the_odds_api'
), upsert_profile as (
  insert into analysis.odds_capture_profiles(
    code,provider_source_id,provider_league_id,season,competition_label,status,request_budget_daily,notes,
    capture_window_start_utc,capture_window_end_utc
  )
  select 'bundesliga_the_odds_api_pilot',id,'soccer_germany_bundesliga',2026,'Bundesliga','prepared',null,
         'Pilot matchday 2026-09-11 through 2026-09-13. Free plan has 500 monthly credits. first_observed is not opening; t_minus_30m is not automatically closing.',
         '2026-09-11T00:00:00Z'::timestamptz,
         '2026-09-14T00:00:00Z'::timestamptz
  from src
  on conflict (code) do update set
    provider_source_id=excluded.provider_source_id,
    provider_league_id=excluded.provider_league_id,
    season=excluded.season,
    competition_label=excluded.competition_label,
    request_budget_daily=null,
    notes=excluded.notes,
    capture_window_start_utc=excluded.capture_window_start_utc,
    capture_window_end_utc=excluded.capture_window_end_utc,
    updated_at=now()
  returning id
), p as (
  select id from upsert_profile
), seed(stage_code,target_offset_minutes,tolerance_minutes,sort_order,notes) as (
  values
    ('first_observed',null::integer,0,1,'First quote observed by BetInsight; never label automatically as opening odds.'),
    ('t_minus_24h',1440,60,2,'Target capture approximately 24 hours before kickoff.'),
    ('t_minus_3h',180,30,3,'Target capture approximately 3 hours before kickoff.'),
    ('t_minus_30m',30,20,4,'Target capture approximately 30 minutes before kickoff; last observed pre-kickoff can later be derived from actual captured_at.')
)
insert into analysis.odds_capture_stages(profile_id,stage_code,target_offset_minutes,tolerance_minutes,sort_order,notes)
select p.id,s.stage_code,s.target_offset_minutes,s.tolerance_minutes,s.sort_order,s.notes from p cross join seed s
on conflict (profile_id,stage_code) do update set
 target_offset_minutes=excluded.target_offset_minutes,
 tolerance_minutes=excluded.tolerance_minutes,
 sort_order=excluded.sort_order,
 notes=excluded.notes;

create index if not exists idx_odds_raw_snapshots_lookup
  on analysis.odds_raw_snapshots(profile_id, fixture_external_id, stage_code, capture_status);

create or replace function analysis.capture_the_odds_api_due(
  p_profile_code text default 'bundesliga_the_odds_api_pilot',
  p_force_first_observed boolean default false
)
returns jsonb
language plpgsql
security definer
set search_path = analysis, extensions, vault, pg_catalog
as $$
declare
  v_profile record;
  v_events_result jsonb;
  v_events jsonb;
  v_event jsonb;
  v_event_id text;
  v_kickoff timestamptz;
  v_stage record;
  v_target timestamptz;
  v_due boolean;
  v_detail jsonb;
  v_body jsonb;
  v_http integer;
  v_bookmakers integer;
  v_capture_status text;
  v_now timestamptz := now();
  v_captured integer := 0;
  v_failed integer := 0;
  v_credits integer := 0;
  v_event_count integer := 0;
begin
  select p.*, d.code as provider_code
  into v_profile
  from analysis.odds_capture_profiles p
  join analysis.data_sources d on d.id = p.provider_source_id
  where p.code = p_profile_code;

  if not found then
    raise exception 'Capture profile % not found', p_profile_code;
  end if;

  if v_profile.provider_code <> 'the_odds_api' then
    raise exception 'Profile % is not configured for The Odds API', p_profile_code;
  end if;

  if v_profile.status not in ('prepared','active') then
    return jsonb_build_object('status','skipped','reason','profile_not_active','profile_status',v_profile.status);
  end if;

  if v_profile.capture_window_start_utc is null or v_profile.capture_window_end_utc is null then
    raise exception 'Capture window is not configured for profile %', p_profile_code;
  end if;

  if v_now > v_profile.capture_window_end_utc + interval '2 hours' then
    update analysis.odds_capture_profiles
    set status='completed', updated_at=now()
    where id=v_profile.id;
    return jsonb_build_object('status','completed','reason','capture_window_finished');
  end if;

  v_events_result := analysis.the_odds_api_get(
    'sports/' || v_profile.provider_league_id || '/events',
    jsonb_build_object('dateFormat','iso')
  );

  if coalesce((v_events_result->>'http_status')::integer,0) not between 200 and 299 then
    return jsonb_build_object('status','failed','reason','events_request_failed','http_status',v_events_result->>'http_status');
  end if;

  v_events := v_events_result->'body';

  for v_event in select value from jsonb_array_elements(coalesce(v_events,'[]'::jsonb))
  loop
    v_event_id := v_event->>'id';
    v_kickoff := (v_event->>'commence_time')::timestamptz;

    if v_kickoff < v_profile.capture_window_start_utc or v_kickoff >= v_profile.capture_window_end_utc then
      continue;
    end if;

    v_event_count := v_event_count + 1;

    for v_stage in
      select * from analysis.odds_capture_stages
      where profile_id = v_profile.id
      order by sort_order
    loop
      if exists (
        select 1 from analysis.odds_raw_snapshots s
        where s.profile_id = v_profile.id
          and s.fixture_external_id = v_event_id
          and s.stage_code = v_stage.stage_code
          and s.capture_status = 'successful'
      ) then
        continue;
      end if;

      if v_stage.stage_code = 'first_observed' then
        v_due := p_force_first_observed and v_now < v_kickoff;
      else
        v_target := v_kickoff - make_interval(mins => v_stage.target_offset_minutes);
        v_due := v_now between
          v_target - make_interval(mins => v_stage.tolerance_minutes)
          and v_target + make_interval(mins => v_stage.tolerance_minutes);
      end if;

      if not v_due then
        continue;
      end if;

      v_detail := analysis.the_odds_api_get(
        'sports/' || v_profile.provider_league_id || '/events/' || v_event_id || '/odds',
        jsonb_build_object(
          'regions','eu',
          'markets','h2h,totals,btts,alternate_totals',
          'oddsFormat','decimal',
          'dateFormat','iso'
        )
      );

      v_http := coalesce((v_detail->>'http_status')::integer,0);
      v_body := v_detail->'body';
      v_credits := v_credits + coalesce((v_detail->>'quota_last')::integer,0);

      if jsonb_typeof(v_body)='object' and jsonb_typeof(v_body->'bookmakers')='array' then
        v_bookmakers := jsonb_array_length(v_body->'bookmakers');
      else
        v_bookmakers := 0;
      end if;

      if v_http between 200 and 299 and v_bookmakers > 0 then
        v_capture_status := 'successful';
        v_captured := v_captured + 1;
      elsif v_http between 200 and 299 then
        v_capture_status := 'empty';
      else
        v_capture_status := 'failed';
        v_failed := v_failed + 1;
      end if;

      insert into analysis.odds_raw_snapshots(
        profile_id, provider_source_id, fixture_external_id, kickoff_utc, stage_code,
        captured_at, request_params, http_status, results_count, errors, capture_status, response_payload
      ) values (
        v_profile.id,
        v_profile.provider_source_id,
        v_event_id,
        v_kickoff,
        v_stage.stage_code,
        now(),
        jsonb_build_object(
          'regions','eu',
          'markets','h2h,totals,btts,alternate_totals',
          'oddsFormat','decimal',
          'dateFormat','iso'
        ),
        v_http,
        v_bookmakers,
        case when v_capture_status='failed' then v_body else '[]'::jsonb end,
        v_capture_status,
        jsonb_build_object('event_meta', v_event, 'odds', v_body)
      );
    end loop;
  end loop;

  return jsonb_build_object(
    'status','ok',
    'profile',p_profile_code,
    'events_in_window',v_event_count,
    'captures_written',v_captured,
    'failed_captures',v_failed,
    'credits_used_this_run',v_credits,
    'run_at',v_now
  );
end;
$$;

revoke all on function analysis.capture_the_odds_api_due(text, boolean) from public, anon, authenticated;
