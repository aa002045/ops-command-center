-- Run this once against your existing database from Phase 02.
-- Adds the unique constraints the Phase 04 ingestion pipeline needs to
-- upsert idempotently (ON CONFLICT DO NOTHING on host_id+ts / datastore_id+ts).
-- Safe to run even though data is already loaded — your existing rows don't
-- have duplicate (host_id, ts) or (datastore_id, ts) pairs.

alter table host_metrics
  add constraint host_metrics_host_id_ts_key unique (host_id, ts);

alter table datastore_metrics
  add constraint datastore_metrics_datastore_id_ts_key unique (datastore_id, ts);

alter table alert_log
  add constraint alert_log_cluster_id_ts_message_key unique (cluster_id, ts, message);
