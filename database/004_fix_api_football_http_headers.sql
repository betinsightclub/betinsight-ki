-- BetInsight KI – API-Football HTTP wrapper fix
-- Stand: 2026-09-06
-- Purpose: fix pgsql-http header construction; no secrets are stored here.

create or replace function analysis.api_football_get(p_endpoint text, p_params jsonb default '{}'::jsonb)
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
  v_allowed constant text[] := array[
    'leagues','fixtures','odds','odds/live','fixtures/lineups',
    'injuries','players','coachs','transfers'
  ];
begin
  if not (p_endpoint = any(v_allowed)) then
    raise exception 'Endpoint % is not allowed', p_endpoint;
  end if;

  select decrypted_secret into v_key
  from vault.decrypted_secrets
  where name = 'api_football_key'
  order by created_at desc
  limit 1;

  if v_key is null or length(v_key) = 0 then
    raise exception 'API-Football key is not configured in Supabase Vault as api_football_key';
  end if;

  v_url := 'https://v3.football.api-sports.io/' || p_endpoint;
  if p_params <> '{}'::jsonb then
    v_url := v_url || '?' || extensions.urlencode(p_params);
  end if;

  select * into v_response
  from extensions.http((
    'GET',
    v_url,
    array[
      ('x-apisports-key', v_key)::extensions.http_header,
      ('accept', 'application/json')::extensions.http_header
    ],
    null,
    null
  )::extensions.http_request);

  begin
    v_body := v_response.content::jsonb;
  exception when others then
    v_body := jsonb_build_object('raw', v_response.content);
  end;

  insert into analysis.api_probe_results(
    endpoint, params, http_status, results_count, errors, paging, response_sample
  ) values (
    p_endpoint,
    p_params,
    v_response.status,
    case when jsonb_typeof(v_body->'results') = 'number' then (v_body->>'results')::integer else null end,
    v_body->'errors',
    v_body->'paging',
    case when v_body ? 'response' then jsonb_build_object('response', v_body->'response') else v_body end
  );

  return jsonb_build_object('http_status', v_response.status, 'body', v_body);
end;
$$;

revoke all on function analysis.api_football_get(text,jsonb) from public, anon, authenticated;
