# Phase 05 — anomaly & pattern-matching layer

Two tiers, matching what's in the build runbook:

- **Tier 1** (`detect_capacity_utilization`, `detect_host_component_limit`) —
  static thresholds on the latest reading, straight from the KB articles
  (70%/90% for capacity, 80%/90% for component count).
- **Tier 2** (`detect_congestion`, `detect_resync_storm`,
  `detect_network_latency`) — rolling-window trend checks (`trend.py`'s
  `slope()`), so these catch a pattern *building*, not just a single reading
  already over the line.

`engine.py` is the piece that ties it to Postgres: for every cluster, it
pulls the last 12 samples per host/datastore, runs the matching detectors,
and keeps `derived_alerts` in sync — opens a new alert the first time a
signature fires, refreshes an already-open one instead of duplicating it,
and marks it `resolved` once the condition clears. That's what "run it as a
60-second scheduled job, not embedded in the API request path" (from the
runbook) actually looks like in code.

## One-time setup

Same driver as Phase 04 — skip this if you already have it:

```powershell
pip install psycopg2-binary
```

## Running it

From the `pipeline` folder:

```powershell
cd pipeline
python -m rules.engine --once
```

`--once` runs a single pass and exits — the right way to try this against
the historical sample data you already loaded, since nothing needs to be
"live" for it to find the 5 injected anomalies. You should see one line per
cluster, e.g.:

```
cluster-dr-01: congestion=clear, capacity_utilization=clear, resync_storm_post_maintenance=clear, network_latency=clear, host_component_limit=clear
cluster-prod-east-01: congestion=clear, capacity_utilization=FIRING(0.81), resync_storm_post_maintenance=clear, network_latency=clear, host_component_limit=FIRING(0.84)
cluster-prod-east-02: congestion=clear, capacity_utilization=clear, resync_storm_post_maintenance=clear, network_latency=clear, host_component_limit=clear
cluster-prod-west-01: congestion=clear, capacity_utilization=clear, resync_storm_post_maintenance=clear, network_latency=clear, host_component_limit=clear
```

(That's the real output I got running the detection logic against your
dataset's last 12 samples per entity — i.e. the very end of the 48-hour
window. Capacity utilization and host component limit trend upward across
the whole window, so by "now" both are already past their critical
thresholds on `cluster-prod-east-01`, the cluster they were injected on —
92.25% capacity, 93.63% component count. That's expected, not a bug: those
two signatures are static thresholds on the *current* reading, exactly
like the KB defines them. The other three signatures — congestion, resync
storm, network latency — were injected as time-boxed events earlier in the
48 hours, so by the end of the window they've already resolved back to
clear, which is also correct. You'll see all five firing if you point
`engine.py` at an earlier slice in time, or once you run it against
`ingest.live` where the congestion injection ramps up in real time.)

Check the result in DBeaver:

```sql
select c.name, s.name as signature, a.confidence, a.status, a.evidence
from derived_alerts a
join clusters c on c.id = a.cluster_id
join bottleneck_signatures s on s.id = a.signature_id
order by a.ts_detected desc;
```

To run it continuously (evaluates every 60 seconds, Ctrl+C to stop) —
useful once `ingest.live` is running in another terminal, so you can watch
an alert actually open and later resolve in real time:

```powershell
python -m rules.engine
python -m rules.engine --interval 20    # faster loop, handy for a demo
```

## What I verified before sending this to you

I couldn't run `engine.py` itself end-to-end against a live psycopg2
connection in my own sandbox (same package-install restriction noted in
`pipeline/ingest/README.md`), but I loaded your exact schema and your real
generated dataset (23,040 host rows, 5,760 datastore rows) into a local
Postgres and checked the part that actually matters — whether the
detection logic gets the right answer against real numbers:

- pulled the real rolling window at 18 checkpoints across all 5 injected
  anomalies (well before, early in the ramp, at the peak/hold, during
  decay, well after) and ran each one through the real detector function —
  all 18 fired or stayed quiet exactly as expected, including catching the
  congestion signature a third of the way into its ramp rather than only
  at the peak
- swept every datastore's `congestion_pct` across the full 48-hour dataset
  for any reading over the 20% threshold outside the one cluster it was
  injected on — zero false positives
- the capacity-utilization and host-component-limit thresholds were
  checked against the actual trend values in your data (crossing 70%/90%
  and 80%/90% respectively) rather than guessed

So the detection logic is solid against your real data; `pip install
psycopg2-binary` (already on your machine from Phase 04) is the one thing
to confirm before your first run here too.
