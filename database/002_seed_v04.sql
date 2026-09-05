-- BetInsight KI – seed data for the frozen v0.4 starting point
-- Run only after 001_initial_schema.sql

insert into analysis.data_sources (code, name, source_type, notes)
values (
  'footiqo_master_2021_2026',
  'Footiqo historical master export 2021/22–2025/26',
  'historical_export',
  'Historical odds from this master must be treated as closing odds. Missing values remain NULL.'
)
on conflict (code) do update
set name = excluded.name,
    source_type = excluded.source_type,
    notes = excluded.notes;

insert into analysis.countries (name, iso2, iso3) values
  ('England','GB','GBR'),
  ('Germany','DE','DEU'),
  ('Spain','ES','ESP'),
  ('Italy','IT','ITA'),
  ('Portugal','PT','PRT')
on conflict (name) do update
set iso2 = excluded.iso2,
    iso3 = excluded.iso3;

insert into analysis.competitions (country_id, name, competition_type, tier)
select c.id, x.league, 'league', 1
from (values
  ('England','Premier League'),
  ('Germany','Bundesliga'),
  ('Spain','LaLiga'),
  ('Italy','Serie A'),
  ('Portugal','Liga Portugal')
) as x(country, league)
join analysis.countries c on c.name = x.country
on conflict (country_id, name) do update
set competition_type = excluded.competition_type,
    tier = excluded.tier;

-- Development seasons: 2021/22–2023/24
insert into analysis.seasons (competition_id, label, dataset_role, locked_for_model_selection)
select comp.id, s.label, 'development', false
from analysis.competitions comp
cross join (values ('2021/22'),('2022/23'),('2023/24')) as s(label)
where comp.name in ('Premier League','Bundesliga','LaLiga','Serie A','Liga Portugal')
on conflict (competition_id, label) do update
set dataset_role = excluded.dataset_role,
    locked_for_model_selection = excluded.locked_for_model_selection;

-- Validation season: 2024/25
insert into analysis.seasons (competition_id, label, dataset_role, locked_for_model_selection)
select comp.id, '2024/25', 'validation', false
from analysis.competitions comp
where comp.name in ('Premier League','Bundesliga','LaLiga','Serie A','Liga Portugal')
on conflict (competition_id, label) do update
set dataset_role = excluded.dataset_role,
    locked_for_model_selection = excluded.locked_for_model_selection;

-- Final hold-out: 2025/26. Locked for model selection.
insert into analysis.seasons (competition_id, label, dataset_role, locked_for_model_selection)
select comp.id, '2025/26', 'holdout', true
from analysis.competitions comp
where comp.name in ('Premier League','Bundesliga','LaLiga','Serie A','Liga Portugal')
on conflict (competition_id, label) do update
set dataset_role = excluded.dataset_role,
    locked_for_model_selection = excluded.locked_for_model_selection;

insert into analysis.model_versions (code, name, status, rules, frozen_at, notes)
values (
  'v0.4',
  'BetInsight Backtest-Regelwerk v0.4',
  'frozen',
  '{
    "chronology": "strict_pre_kickoff",
    "holdout": "2025/26",
    "market_odds": "closing",
    "safety_value_separate": true,
    "no_bet_allowed": true,
    "core_signals": ["margin_adjusted_market_probability","rolling_elo_difference","league_base_rate","long_term_goal_profiles","home_away_splits"],
    "last5_role": "weak_additional_signal"
  }'::jsonb,
  now(),
  'Seeded from the frozen project logbook. Changing the rule requires a new version; do not silently overwrite v0.4.'
)
on conflict (code) do nothing;
