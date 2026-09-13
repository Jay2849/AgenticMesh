create extension if not exists vector;

create table services (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  current_image_tag text,
  stable_image_tag text,
  created_at timestamptz default now()
);

create table incidents (
  id uuid primary key default gen_random_uuid(),
  incident_id text unique not null,
  service_id uuid references services(id),
  fingerprint_hash text not null,
  occurrence_count int default 1,
  sample_stack_trace text,
  status text not null default 'NEW',
  -- NEW | DIAGNOSING | AWAITING_APPROVAL | APPROVED | REJECTED_OPEN | REMEDIATED | REMEDIATION_FAILED
  first_seen timestamptz,
  last_seen timestamptz,
  created_at timestamptz default now()
);

create table incident_embeddings (
  id uuid primary key default gen_random_uuid(),
  incident_id uuid references incidents(id),
  error_signature text,
  embedding vector(1536),
  created_at timestamptz default now()
);

create table rca_results (
  id uuid primary key default gen_random_uuid(),
  incident_id uuid references incidents(id),
  root_cause text,
  faulty_file text,
  faulty_function text,
  code_snippet text,
  confidence_score float,
  suggested_fix_diff text,
  rollback_target_tag text,
  created_at timestamptz default now()
);

create table approvals (
  id uuid primary key default gen_random_uuid(),
  incident_id uuid references incidents(id),
  decision text not null, -- APPROVED | REJECTED
  approved_by text,
  decided_at timestamptz default now()
);

create table remediation_log (
  id uuid primary key default gen_random_uuid(),
  incident_id uuid references incidents(id),
  action_taken text,
  success boolean,
  details text,
  github_pr_url text,
  resolved_at timestamptz
);

create index on incident_embeddings using ivfflat (embedding vector_cosine_ops) with (lists = 100);
