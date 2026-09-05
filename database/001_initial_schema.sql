-- BetInsight KI-/Datenplattform
-- Initial PostgreSQL/Supabase schema v0.1
-- Stand: 2026-09-06
-- No secrets. No connection to the existing BetInsight customer system.

create schema if not exists analysis;

-- -------------------------
-- Sources / Imports
-- -------------------------

create table if not exists analysis.data_sources (
  id bigint generated always as identity primary key,
  code text not null unique,
  name text not null,
  source_type text not null default 'provider',
  base_url text,
  notes text,
  created_at timestamptz not null default now()
);

create table if not exists analysis.import_batches (
  id bigint generated always as identity primary key,
  source_id bigint not null references analysis.data_sources(id),
  file_name text,
  file_sha256 text,
  imported_at timestamptz not null default now(),
  status text not null default 'pending' check (status in ('pending','running','completed','failed','rejected')),
  row_count integer,
  notes text
);

create table if not exists analysis.raw_import_rows (
  id bigint generated always as identity primary key,
  import_batch_id bigint not null references analysis.import_batches(id) on delete cascade,
  source_row_number integer,
  payload jsonb not null,
  created_at timestamptz not null default now(),
  unique(import_batch_id, source_row_number)
);

-- -------------------------
-- Core football entities
-- -------------------------

create table if not exists analysis.countries (
  id bigint generated always as identity primary key,
  name text not null unique,
  iso2 text,
  iso3 text
);

create table if not exists analysis.competitions (
  id bigint generated always as identity primary key,
  country_id bigint references analysis.countries(id),
  name text not null,
  competition_type text not null default 'league',
  tier integer,
  active boolean not null default true,
  unique(country_id, name)
);

create table if not exists analysis.seasons (
  id bigint generated always as identity primary key,
  competition_id bigint not null references analysis.competitions(id),
  label text not null,
  start_date date,
  end_date date,
  dataset_role text not null default 'unassigned'
    check (dataset_role in ('development','validation','holdout','unassigned')),
  locked_for_model_selection boolean not null default false,
  unique(competition_id, label)
);

create table if not exists analysis.teams (
  id bigint generated always as identity primary key,
  country_id bigint references analysis.countries(id),
  name text not null,
  normalized_name text,
  active boolean not null default true,
  unique(country_id, name)
);

create table if not exists analysis.fixtures (
  id bigint generated always as identity primary key,
  competition_id bigint not null references analysis.competitions(id),
  season_id bigint not null references analysis.seasons(id),
  kickoff_utc timestamptz not null,
  home_team_id bigint not null references analysis.teams(id),
  away_team_id bigint not null references analysis.teams(id),
  referee_name text,
  status text not null default 'finished',
  home_goals smallint,
  away_goals smallint,
  full_time_result char(1) check (full_time_result in ('H','D','A') or full_time_result is null),
  data_flag text,
  source_batch_id bigint references analysis.import_batches(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (home_team_id <> away_team_id),
  unique(competition_id, kickoff_utc, home_team_id, away_team_id)
);

create table if not exists analysis.fixture_external_ids (
  fixture_id bigint not null references analysis.fixtures(id) on delete cascade,
  source_id bigint not null references analysis.data_sources(id),
  external_id text not null,
  primary key (source_id, external_id),
  unique(fixture_id, source_id)
);

-- -------------------------
-- Odds
-- -------------------------

create table if not exists analysis.odds_quotes (
  id bigint generated always as identity primary key,
  fixture_id bigint not null references analysis.fixtures(id) on delete cascade,
  source_id bigint not null references analysis.data_sources(id),
  bookmaker text,
  market_code text not null,
  selection_code text not null,
  line numeric(6,2),
  decimal_odds numeric(10,4) not null check (decimal_odds > 1),
  snapshot_type text not null default 'unknown'
    check (snapshot_type in ('opening','closing','prematch','live','unknown')),
  captured_at timestamptz,
  is_verified boolean not null default true,
  source_batch_id bigint references analysis.import_batches(id),
  created_at timestamptz not null default now()
);

create unique index if not exists uq_odds_quote_identity
  on analysis.odds_quotes (
    fixture_id,
    source_id,
    coalesce(bookmaker,''),
    market_code,
    selection_code,
    coalesce(line,-999::numeric),
    snapshot_type,
    coalesce(captured_at,'1900-01-01 00:00:00+00'::timestamptz)
  );

-- -------------------------
-- Data quality
-- -------------------------

create table if not exists analysis.data_quality_issues (
  id bigint generated always as identity primary key,
  fixture_id bigint references analysis.fixtures(id) on delete cascade,
  competition_id bigint references analysis.competitions(id),
  season_id bigint references analysis.seasons(id),
  issue_type text not null,
  status text not null default 'open' check (status in ('open','accepted','resolved','excluded')),
  affected_field text,
  description text not null,
  source_id bigint references analysis.data_sources(id),
  created_at timestamptz not null default now(),
  resolved_at timestamptz
);

-- -------------------------
-- Model / features
-- -------------------------

create table if not exists analysis.model_versions (
  id bigint generated always as identity primary key,
  code text not null unique,
  name text not null,
  status text not null default 'draft' check (status in ('draft','frozen','retired')),
  rules jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  frozen_at timestamptz,
  notes text
);

create table if not exists analysis.feature_snapshots (
  id bigint generated always as identity primary key,
  fixture_id bigint not null references analysis.fixtures(id) on delete cascade,
  model_version_id bigint not null references analysis.model_versions(id),
  as_of_utc timestamptz not null,
  feature_schema_version text not null,
  features jsonb not null,
  calculated_at timestamptz not null default now(),
  check (as_of_utc <= calculated_at),
  unique(fixture_id, model_version_id, as_of_utc, feature_schema_version)
);

-- -------------------------
-- Backtests
-- -------------------------

create table if not exists analysis.backtest_runs (
  id bigint generated always as identity primary key,
  model_version_id bigint not null references analysis.model_versions(id),
  run_code text not null unique,
  dataset_role text not null check (dataset_role in ('development','validation','holdout')),
  started_at timestamptz not null default now(),
  completed_at timestamptz,
  parameters jsonb not null default '{}'::jsonb,
  metrics jsonb not null default '{}'::jsonb,
  notes text
);

create table if not exists analysis.backtest_bets (
  id bigint generated always as identity primary key,
  backtest_run_id bigint not null references analysis.backtest_runs(id) on delete cascade,
  fixture_id bigint not null references analysis.fixtures(id),
  decision_time_utc timestamptz not null,
  market_code text not null,
  selection_code text not null,
  line numeric(6,2),
  decimal_odds numeric(10,4),
  model_probability numeric(10,8),
  market_probability numeric(10,8),
  edge numeric(10,8),
  stake_units numeric(12,4) not null default 1,
  result text check (result in ('win','loss','push','void','pending','no_bet')),
  pnl_units numeric(12,4),
  reason jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  check (decision_time_utc <= (select kickoff_utc from analysis.fixtures where id = fixture_id))
);

-- PostgreSQL CHECK constraints cannot safely use a subquery in all managed environments.
-- Replace the previous time-order rule with a trigger in a later migration if required.
-- The DDL above is intentionally kept provider-portable; remove/recreate the constraint if the provider rejects it.

create table if not exists analysis.analysis_candidates (
  id bigint generated always as identity primary key,
  fixture_id bigint not null references analysis.fixtures(id),
  model_version_id bigint references analysis.model_versions(id),
  created_at timestamptz not null default now(),
  valid_until timestamptz,
  market_code text not null,
  selection_code text not null,
  line numeric(6,2),
  decimal_odds numeric(10,4),
  confidence numeric(10,8),
  edge numeric(10,8),
  status text not null default 'draft'
    check (status in ('draft','approved','rejected','published','expired')),
  approved_at timestamptz,
  published_at timestamptz,
  payload jsonb not null default '{}'::jsonb
);

-- -------------------------
-- Future v0.5 entities
-- -------------------------

create table if not exists analysis.coaches (
  id bigint generated always as identity primary key,
  name text not null,
  birth_date date,
  nationality_country_id bigint references analysis.countries(id)
);

create table if not exists analysis.team_coach_tenures (
  id bigint generated always as identity primary key,
  team_id bigint not null references analysis.teams(id),
  coach_id bigint not null references analysis.coaches(id),
  started_at timestamptz not null,
  ended_at timestamptz,
  source_id bigint references analysis.data_sources(id),
  check (ended_at is null or ended_at >= started_at)
);

create table if not exists analysis.players (
  id bigint generated always as identity primary key,
  name text not null,
  birth_date date,
  nationality_country_id bigint references analysis.countries(id)
);

create table if not exists analysis.team_player_stints (
  id bigint generated always as identity primary key,
  team_id bigint not null references analysis.teams(id),
  player_id bigint not null references analysis.players(id),
  started_at timestamptz not null,
  ended_at timestamptz,
  source_id bigint references analysis.data_sources(id),
  check (ended_at is null or ended_at >= started_at)
);

create table if not exists analysis.transfers (
  id bigint generated always as identity primary key,
  player_id bigint not null references analysis.players(id),
  from_team_id bigint references analysis.teams(id),
  to_team_id bigint references analysis.teams(id),
  transfer_date date not null,
  transfer_type text,
  fee_amount numeric(18,2),
  fee_currency char(3),
  source_id bigint references analysis.data_sources(id),
  source_external_id text,
  created_at timestamptz not null default now()
);

-- -------------------------
-- Indexes
-- -------------------------

create index if not exists idx_fixtures_kickoff on analysis.fixtures(kickoff_utc);
create index if not exists idx_fixtures_comp_season_kickoff on analysis.fixtures(competition_id, season_id, kickoff_utc);
create index if not exists idx_fixtures_home_kickoff on analysis.fixtures(home_team_id, kickoff_utc);
create index if not exists idx_fixtures_away_kickoff on analysis.fixtures(away_team_id, kickoff_utc);
create index if not exists idx_odds_fixture_market on analysis.odds_quotes(fixture_id, market_code, snapshot_type);
create index if not exists idx_odds_captured_at on analysis.odds_quotes(captured_at);
create index if not exists idx_feature_fixture_model_asof on analysis.feature_snapshots(fixture_id, model_version_id, as_of_utc);
create index if not exists idx_backtest_bets_run on analysis.backtest_bets(backtest_run_id);
create index if not exists idx_candidates_status on analysis.analysis_candidates(status, created_at);

-- -------------------------
-- RLS: deny public/browser table access by default
-- -------------------------

alter table analysis.data_sources enable row level security;
alter table analysis.import_batches enable row level security;
alter table analysis.raw_import_rows enable row level security;
alter table analysis.countries enable row level security;
alter table analysis.competitions enable row level security;
alter table analysis.seasons enable row level security;
alter table analysis.teams enable row level security;
alter table analysis.fixtures enable row level security;
alter table analysis.fixture_external_ids enable row level security;
alter table analysis.odds_quotes enable row level security;
alter table analysis.data_quality_issues enable row level security;
alter table analysis.model_versions enable row level security;
alter table analysis.feature_snapshots enable row level security;
alter table analysis.backtest_runs enable row level security;
alter table analysis.backtest_bets enable row level security;
alter table analysis.analysis_candidates enable row level security;
alter table analysis.coaches enable row level security;
alter table analysis.team_coach_tenures enable row level security;
alter table analysis.players enable row level security;
alter table analysis.team_player_stints enable row level security;
alter table analysis.transfers enable row level security;
