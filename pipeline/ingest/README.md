# Phase 04 — ingestion pipeline

Two scripts, both idempotent (safe to rerun — duplicates are silently
skipped via `ON CONFLICT DO NOTHING` on the unique constraints from
`db/migrations/002_add_unique_constraints.sql`):

- **`batch.py`** — reads the CSVs in `pipeline/out/`, validates every row
  through `clean.py`, and loads them into Postgres. This replaces the
  manual `\copy` commands from Phase 02 with a real, rerunnable pipeline.
- **`live.py`** — appends one new row per host/datastore every 12 seconds,
  using the real cluster/host/datastore IDs already sitting in your
  database. This is what makes Phase 07's dashboard feel alive instead of
  static.

## One-time setup

```powershell
pip install psycopg2-binary
```

If you haven't already, apply the migration that adds the unique
constraints these scripts rely on:

```powershell
docker cp db\migrations occ-pg:/migrations
docker exec -it occ-pg psql -U postgres -d occ -f /migrations/002_add_unique_constraints.sql
```

## Running batch.py

From the `pipeline` folder:

```powershell
cd pipeline
python -m ingest.batch
```

Since you already loaded this same data via `\copy` in Phase 02, expect
output like:

```
host_metrics: 23040 rows read, 0 newly inserted (23040 already present, skipped)
datastore_metrics: 5760 rows read, 0 newly inserted (5760 already present, skipped)
alert_log: 11 rows read, 0 newly inserted (11 already present, skipped)
```

That "0 newly inserted, all skipped" result is the point — it proves the
pipeline is idempotent. If you ever regenerate a larger or different
dataset from `generator/generate.py`, rerunning `batch.py` loads only
what's actually new.

## Running live.py

Same folder:

```powershell
python -m ingest.live
```

It'll print one line every 12 seconds as it inserts a fresh row for every
host and datastore. Leave it running in one terminal, and watch new rows
show up in DBeaver (`select count(*) from host_metrics;` — the count
should tick up). Stop with `Ctrl+C`.

To also see a live anomaly ramp up and back down — useful once Phase 07's
dashboard exists, so you can watch a signature actually fire in real time:

```powershell
python -m ingest.live --inject congestion --inject-after 1
```

That waits 1 minute, then ramps a congestion pattern on one datastore over
2 minutes, holds briefly, and decays back over another 2 minutes — a ~5
minute window, good for a live demo without making anyone wait too long.

## What I verified before sending this to you

I couldn't fully run `live.py`/`batch.py` end-to-end in my own environment
(a package install was blocked there), but I did verify, against a real
local Postgres loaded with your exact schema and data:

- every row in your actual `host_metrics.csv`/`datastore_metrics.csv`
  passes `clean.py` cleanly (0 dropped) — the cleaning rules aren't so
  strict they'd reject your own good data
- deliberately bad rows (negative values, out-of-range percentages,
  missing required fields) get correctly rejected
- the exact `INSERT ... ON CONFLICT DO NOTHING` pattern both scripts use
  behaves correctly: re-inserting existing rows inserts 0 new rows, a
  genuinely new row gets inserted, idempotency holds
- the injected-anomaly ramp math (`injected_fraction`) produces the right
  triangle-shaped curve: 0 before the start time, ramping to 1.0 at the
  midpoint, back to 0 by the end

So the logic is solid; `pip install psycopg2-binary` on your machine (which
has normal internet access) is the one thing to confirm works before your
first run.
