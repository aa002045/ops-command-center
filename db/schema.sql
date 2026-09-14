-- Ops Command Center schema.
-- host_metrics carries two fields (network_latency_ms, component_count_pct)
-- added after grounding Phase 01's signatures in real vSAN KB articles —
-- see db/signatures.sql for the citations.

create extension if not exists pgcrypto;  -- for gen_random_uuid()

create table clusters (
  id            uuid primary key default gen_random_uuid(),
  name          text not null,
  site          text,
  vsan_type     text check (vsan_type in ('OSA','ESA')),
  node_count    int,
  created_at    timestamptz not null default now()
);

create table hosts (
  id            uuid primary key default gen_random_uuid(),
  cluster_id    uuid references clusters(id),
  name          text not null,
  cpu_cores     int,
  mem_total_gb  numeric
);

create table datastores (
  id                uuid primary key default gen_random_uuid(),
  cluster_id        uuid references clusters(id),
  name              text not null,
  type              text check (type in ('vSAN','VMFS','NFS')),
  total_capacity_gb numeric
);

create table host_metrics (
  id                    bigint generated always as identity primary key,
  host_id               uuid references hosts(id),
  ts                    timestamptz not null,
  cpu_usage_pct         numeric,
  cpu_ready_pct         numeric,
  mem_usage_pct         numeric,
  network_latency_ms    numeric,  -- KB 315544 Network Latency Check: warning >5ms
  component_count_pct   numeric   -- KB 315533 Host component limit: yellow 80-90%, red >90%
);
create index on host_metrics (host_id, ts desc);

create table datastore_metrics (
  id                    bigint generated always as identity primary key,
  datastore_id          uuid references datastores(id),
  ts                    timestamptz not null,
  read_latency_ms       numeric,
  write_latency_ms      numeric,
  iops_read             numeric,
  iops_write            numeric,
  congestion_pct        numeric,
  used_capacity_pct     numeric,  -- KB 326889 Capacity utilization: yellow 70%, red 90%
  cache_tier_usage_pct  numeric,
  resync_backlog_gb     numeric
);
create index on datastore_metrics (datastore_id, ts desc);

create table alert_log (          -- raw vendor-style feed (vCenter / Skyline Health)
  id          bigint generated always as identity primary key,
  cluster_id  uuid references clusters(id),
  ts          timestamptz not null,
  severity    text,
  source      text,
  message     text
);

create table bottleneck_signatures ( -- Phase 01 table, as data
  id                uuid primary key default gen_random_uuid(),
  name              text not null,
  description       text,
  detection_rule    jsonb not null,
  default_severity  text,
  source_reference  text  -- the Broadcom/VMware KB article(s) this signature is grounded in
);

create table derived_alerts (      -- your own pattern-matching engine's output
  id            bigint generated always as identity primary key,
  cluster_id    uuid references clusters(id),
  signature_id  uuid references bottleneck_signatures(id),
  ts_detected   timestamptz not null default now(),
  confidence    numeric,
  status        text default 'open',
  evidence      jsonb
);
