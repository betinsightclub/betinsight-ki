-- BetInsight KI – provider-neutral odds capture pilot
-- Stand: 2026-09-06
-- No secrets in this file. No automatic paid usage.

create table if not exists analysis.odds_capture_profiles (
  id bigint generated always as identity primary key,
  code text not null unique,
  provider_source_id bigint not null references analysis.data_sources(id),
  provider_league_id text,
  season integer,
  competition_label text not null,
  status text not null default 'prepared'
    check (status in ('prepared','active','paused','completed')),
  request_budget_daily integer check (request_budget_daily is null or request_budget_daily > 0),
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists analysis.odds_capture_stages (
  id bigint generated always as identity primary key,
  profile_id bigint not null references analysis.odds_capture_profiles(id) on delete cascade,
  stage_code text not null
    check (stage_code in ('first_observed','t_minus_24h','t_minus_3h','t_minus_30m')),
  target_offset_minutes integer,
  tolerance_minutes integer not null default 30 check (tolerance_minutes >= 0),
  sort_order integer not null,
  notes text,
  unique(profile_id, stage_code),
  check (
    (stage_code = 'first_observed' and target_offset_minutes is null)
    or (stage_code <> 'first_observed' and target_offset_minutes is not null and target_offset_minutes > 0)
  )
);

create table if not exists analysis.odds_raw_snapshots (
  id bigint generated always as identity primary key,
  profile_id bigint not null references analysis.odds_capture_profiles(id),
  provider_source_id bigint not null references analysis.data_sources(id),
  fixture_external_id text not null,
  kickoff_utc timestamptz,
  stage_code text not null,
  captured_at timestamptz not null default now(),
  request_params jsonb not null default '{}'::jsonb,
  http_status integer,
  results_count integer,
  errors jsonb,
  capture_status text not null check (capture_status in ('successful','empty','failed')),
  response_payload jsonb not null default '[]'::jsonb
);

create index if not exists idx_odds_raw_fixture_capture
  on analysis.odds_raw_snapshots(provider_source_id, fixture_external_id, captured_at);
create index if not exists idx_odds_raw_profile_stage
  on analysis.odds_raw_snapshots(profile_id, stage_code, captured_at);

alter table analysis.odds_capture_profiles enable row level security;
alter table analysis.odds_capture_stages enable row level security;
alter table analysis.odds_raw_snapshots enable row level security;

revoke all on analysis.odds_capture_profiles from anon, authenticated;
revoke all on analysis.odds_capture_stages from anon, authenticated;
revoke all on analysis.odds_raw_snapshots from anon, authenticated;
revoke all on all sequences in schema analysis from anon, authenticated;

insert into analysis.odds_capture_profiles (
  code, provider_source_id, provider_league_id, season, competition_label,
  status, request_budget_daily, notes
)
select
  'bundesliga_api_football_pilot', id, '78', 2026, 'Bundesliga',
  'prepared', 100,
  'Provider-neutral pilot profile. API-Football Free currently blocks season 2026 league-specific odds/fixtures; do not activate until access is available or provider is switched.'
from analysis.data_sources
where code = 'api_football'
on conflict (code) do update set
  provider_source_id = excluded.provider_source_id,
  provider_league_id = excluded.provider_league_id,
  season = excluded.season,
  competition_label = excluded.competition_label,
  request_budget_daily = excluded.request_budget_daily,
  notes = excluded.notes,
  updated_at = now();

insert into analysis.odds_capture_stages(profile_id, stage_code, target_offset_minutes, tolerance_minutes, sort_order, notes)
select p.id, s.stage_code, s.target_offset_minutes, s.tolerance_minutes, s.sort_order, s.notes
from analysis.odds_capture_profiles p
cross join (values
  ('first_observed'::text, null::integer, 0, 1, 'First quote observed by BetInsight; never label automatically as opening odds.'::text),
  ('t_minus_24h'::text, 1440, 60, 2, 'Target capture approximately 24 hours before kickoff.'::text),
  ('t_minus_3h'::text, 180, 30, 3, 'Target capture approximately 3 hours before kickoff.'::text),
  ('t_minus_30m'::text, 30, 20, 4, 'Target capture approximately 30 minutes before kickoff; last observed pre-kickoff can later be derived from actual captured_at.'::text)
) as s(stage_code, target_offset_minutes, tolerance_minutes, sort_order, notes)
where p.code = 'bundesliga_api_football_pilot'
on conflict (profile_id, stage_code) do update set
  target_offset_minutes = excluded.target_offset_minutes,
  tolerance_minutes = excluded.tolerance_minutes,
  sort_order = excluded.sort_order,
  notes = excluded.notes;

create or replace function analysis.capture_api_football_fixture_odds(
  p_profile_code text,
  p_fixture_external_id text,
  p_stage_code text,
  p_kickoff_utc timestamptz default null
)
returns jsonb
language plpgsql
security definer
set search_path = analysis, pg_catalog
as $$
declare
  v_profile analysis.odds_capture_profiles%rowtype;
  v_stage_exists boolean;
  v_result jsonb;
  v_body jsonb;
  v_http integer;
  v_count integer;
  v_errors jsonb;
  v_status text;
begin
  select * into v_profile
  from analysis.odds_capture_profiles
  where code = p_profile_code;

  if v_profile.id is null then
    raise exception 'Unknown capture profile %', p_profile_code;
  end if;

  select exists(
    select 1 from analysis.odds_capture_stages
    where profile_id = v_profile.id and stage_code = p_stage_code
  ) into v_stage_exists;

  if not v_stage_exists then
    raise exception 'Stage % is not configured for profile %', p_stage_code, p_profile_code;
  end if;

  v_result := analysis.api_football_get('odds', jsonb_build_object('fixture', p_fixture_external_id));
  v_http := (v_result->>'http_status')::integer;
  v_body := v_result->'body';
  v_count := coalesce((v_body->>'results')::integer, 0);
  v_errors := v_body->'errors';

  if v_http <> 200 or (v_errors is not null and v_errors <> '[]'::jsonb and v_errors <> '{}'::jsonb) then
    v_status := 'failed';
  elsif v_count = 0 then
    v_status := 'empty';
  else
    v_status := 'successful';
  end if;

  insert into analysis.odds_raw_snapshots(
    profile_id, provider_source_id, fixture_external_id, kickoff_utc, stage_code,
    request_params, http_status, results_count, errors, capture_status, response_payload
  ) values (
    v_profile.id, v_profile.provider_source_id, p_fixture_external_id, p_kickoff_utc, p_stage_code,
    jsonb_build_object('fixture', p_fixture_external_id), v_http, v_count, v_errors, v_status,
    coalesce(v_body->'response', '[]'::jsonb)
  );

  return jsonb_build_object(
    'profile', p_profile_code,
    'fixture_external_id', p_fixture_external_id,
    'stage', p_stage_code,
    'http_status', v_http,
    'results', v_count,
    'capture_status', v_status
  );
end;
$$;

revoke all on function analysis.capture_api_football_fixture_odds(text, text, text, timestamptz) from public, anon, authenticated;
