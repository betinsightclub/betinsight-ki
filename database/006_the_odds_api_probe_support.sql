-- BetInsight KI – The Odds API probe support
-- Stand: 2026-09-06
-- API key remains only in Supabase Vault as the_odds_api_key.

alter table analysis.api_probe_results
  add column if not exists quota_last integer,
  add column if not exists quota_used integer,
  add column if not exists quota_remaining integer;

insert into analysis.data_sources(code,name,source_type,base_url,notes)
values ('the_odds_api','The Odds API','provider','https://api.the-odds-api.com',
        'Current/live odds provider pilot. API key stored only in Supabase Vault as the_odds_api_key.')
on conflict (code) do update set
  name=excluded.name,
  source_type=excluded.source_type,
  base_url=excluded.base_url,
  notes=excluded.notes;

create or replace function analysis.the_odds_api_get(
  p_path text,
  p_params jsonb default '{}'::jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = analysis, extensions, vault, pg_catalog
as $$
declare
  v_key text;
  v_url text;
  v_response extensions.http_response;
  v_body jsonb;
  v_headers jsonb := '{}'::jsonb;
  v_results integer;
  v_errors jsonb;
  v_sample jsonb;
  v_quota_last integer;
  v_quota_used integer;
  v_quota_remaining integer;
begin
  if not (
    p_path = 'sports'
    or p_path ~ '^sports/[a-z0-9_]+/(odds|events)$'
    or p_path ~ '^sports/[a-z0-9_]+/events/[A-Za-z0-9_-]+/(odds|markets)$'
  ) then
    raise exception 'Path % is not allowed', p_path;
  end if;

  select decrypted_secret into v_key
  from vault.decrypted_secrets
  where name = 'the_odds_api_key'
  order by created_at desc
  limit 1;

  if v_key is null or length(v_key) = 0 then
    raise exception 'The Odds API key is not configured in Supabase Vault as the_odds_api_key';
  end if;

  v_url := 'https://api.the-odds-api.com/v4/' || p_path || '?' ||
           extensions.urlencode(p_params || jsonb_build_object('apiKey', v_key));

  select * into v_response
  from extensions.http((
    'GET',
    v_url,
    array[row('accept','application/json')::extensions.http_header],
    null,
    null
  )::extensions.http_request);

  begin
    v_body := v_response.content::jsonb;
  exception when others then
    v_body := jsonb_build_object('raw', v_response.content);
  end;

  select coalesce(jsonb_object_agg(lower(h.field), h.value), '{}'::jsonb)
  into v_headers
  from unnest(v_response.headers) h;

  v_quota_last := nullif(v_headers->>'x-requests-last','')::integer;
  v_quota_used := nullif(v_headers->>'x-requests-used','')::integer;
  v_quota_remaining := nullif(v_headers->>'x-requests-remaining','')::integer;

  if jsonb_typeof(v_body) = 'array' then
    v_results := jsonb_array_length(v_body);
    v_errors := '[]'::jsonb;
    v_sample := case when jsonb_array_length(v_body) > 0 then v_body->0 else '[]'::jsonb end;
  else
    v_results := case when v_response.status between 200 and 299 then 1 else 0 end;
    v_errors := case when v_response.status between 200 and 299 then '[]'::jsonb else v_body end;
    v_sample := v_body;
  end if;

  insert into analysis.api_probe_results(
    provider, endpoint, params, http_status, results_count, errors, paging, response_sample,
    quota_last, quota_used, quota_remaining
  ) values (
    'the-odds-api', p_path, p_params, v_response.status, v_results, v_errors, null,
    jsonb_build_object('sample', v_sample),
    v_quota_last, v_quota_used, v_quota_remaining
  );

  return jsonb_build_object(
    'http_status', v_response.status,
    'quota_last', v_quota_last,
    'quota_used', v_quota_used,
    'quota_remaining', v_quota_remaining,
    'body', v_body
  );
end;
$$;

revoke all on function analysis.the_odds_api_get(text, jsonb) from public, anon, authenticated;
