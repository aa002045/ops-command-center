"""Phase 05 anomaly engine — evaluates every signature against every
cluster's most recent data and keeps derived_alerts in sync.

This is your own pattern-matching layer, separate from alert_log (the raw
vendor-style feed ingested in Phase 04) — see db/schema.sql's note on why
those two tables are deliberately split.

Run once (good for checking it against the historical sample data you
already loaded, since nothing needs to be "live" for this):
    python3 -m rules.engine --once

By default the engine always looks at each entity's most recent rows —
so once ingest.live has been running, "most recent" means the live
stream, not your Sept 12-14 historical sample data. Use --before to pin
it to a point in time instead, e.g. to see the historical anomalies:
    python3 -m rules.engine --once --before "2026-09-13 23:00:00"

Run continuously (evaluates every 60s, Ctrl+C to stop):
    python3 -m rules.engine
    python3 -m rules.engine --interval 30

Requires: pip install psycopg2-binary (same as Phase 04)
"""
import argparse
import json
import time

from .db import get_connection
from .detectors import DATASTORE_DETECTORS, HOST_DETECTORS

WINDOW_SAMPLES = 12  # how many recent rows per entity each detector sees
DS_COLUMNS = ["congestion_pct", "cache_tier_usage_pct", "iops_write",
              "used_capacity_pct", "resync_backlog_gb"]
HOST_COLUMNS = ["network_latency_ms", "component_count_pct"]


def fetch_signature_ids(conn):
    with conn.cursor() as cur:
        cur.execute("select name, id from bottleneck_signatures")
        return dict(cur.fetchall())


def fetch_clusters(conn):
    with conn.cursor() as cur:
        cur.execute("select id, name from clusters order by name")
        return cur.fetchall()


def fetch_entity_ids(conn, table, cluster_id):
    with conn.cursor() as cur:
        cur.execute(f"select id from {table} where cluster_id = %s", (cluster_id,))
        return [r[0] for r in cur.fetchall()]


def fetch_window(conn, table, id_column, entity_id, columns, before=None):
    cols_sql = ", ".join(columns)
    with conn.cursor() as cur:
        if before:
            cur.execute(
                f"select {cols_sql} from {table} where {id_column} = %s and ts <= %s "
                f"order by ts desc limit %s",
                (entity_id, before, WINDOW_SAMPLES),
            )
        else:
            cur.execute(
                f"select {cols_sql} from {table} where {id_column} = %s "
                f"order by ts desc limit %s",
                (entity_id, WINDOW_SAMPLES),
            )
        rows = cur.fetchall()
    rows.reverse()  # oldest -> newest, what the detectors expect
    # psycopg2 returns Postgres `numeric` columns as decimal.Decimal, not
    # float — and Decimal can't be multiplied with a plain float (which is
    # what trend.py's slope() produces from its own arithmetic). Converting
    # here means every detector downstream only ever sees plain floats.
    return [
        dict(zip(columns, (float(v) if v is not None else 0.0 for v in row)))
        for row in rows
    ]


def best_result(results_by_entity):
    """Given [(matched, confidence, evidence), ...] across every entity in
    a cluster, keep the single strongest match (or the clearest non-match)
    — one alert per cluster per signature, not one per host/datastore."""
    firing = [r for r in results_by_entity if r[0]]
    if firing:
        return max(firing, key=lambda r: r[1])
    return False, 0.0, {}


def upsert_alert(conn, cluster_id, signature_id, matched, confidence, evidence):
    with conn.cursor() as cur:
        cur.execute(
            "select id from derived_alerts "
            "where cluster_id = %s and signature_id = %s and status = 'open'",
            (cluster_id, signature_id),
        )
        existing = cur.fetchone()

        if matched:
            if existing:
                cur.execute(
                    "update derived_alerts set confidence = %s, evidence = %s, "
                    "ts_detected = now() where id = %s",
                    (confidence, json.dumps(evidence), existing[0]),
                )
            else:
                cur.execute(
                    "insert into derived_alerts (cluster_id, signature_id, confidence, "
                    "status, evidence) values (%s, %s, %s, 'open', %s)",
                    (cluster_id, signature_id, confidence, json.dumps(evidence)),
                )
        elif existing:
            # condition cleared — close out the alert rather than leaving it
            # open forever or spamming a fresh row every pass
            cur.execute("update derived_alerts set status = 'resolved' where id = %s",
                        (existing[0],))
    conn.commit()


def evaluate_cluster(conn, cluster_id, cluster_name, signature_ids, before=None):
    summary = {}

    datastore_ids = fetch_entity_ids(conn, "datastores", cluster_id)
    for sig_name, detector in DATASTORE_DETECTORS.items():
        results = [detector(fetch_window(conn, "datastore_metrics", "datastore_id", d, DS_COLUMNS, before))
                   for d in datastore_ids]
        summary[sig_name] = best_result(results)

    host_ids = fetch_entity_ids(conn, "hosts", cluster_id)
    for sig_name, detector in HOST_DETECTORS.items():
        results = [detector(fetch_window(conn, "host_metrics", "host_id", h, HOST_COLUMNS, before))
                   for h in host_ids]
        summary[sig_name] = best_result(results)

    for sig_name, (matched, confidence, evidence) in summary.items():
        if sig_name not in signature_ids:
            continue  # signature row missing from bottleneck_signatures — skip rather than crash
        upsert_alert(conn, cluster_id, signature_ids[sig_name], matched, confidence, evidence)

    status = ", ".join(
        f"{name}={'FIRING(' + str(conf) + ')' if matched else 'clear'}"
        for name, (matched, conf, _) in summary.items()
    )
    print(f"{cluster_name}: {status}")


def run_once(conn, before=None):
    signature_ids = fetch_signature_ids(conn)
    for cluster_id, cluster_name in fetch_clusters(conn):
        evaluate_cluster(conn, cluster_id, cluster_name, signature_ids, before)


def run(interval):
    conn = get_connection()
    print(f"anomaly engine: evaluating every {interval}s, window = last {WINDOW_SAMPLES} samples/entity. Ctrl+C to stop.")
    try:
        while True:
            run_once(conn)
            print("-" * 60)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nstopped.")
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="evaluate a single pass and exit")
    parser.add_argument("--interval", type=float, default=60.0, help="seconds between passes")
    parser.add_argument("--before", default=None,
                         help="only look at rows at or before this timestamp, e.g. "
                              "'2026-09-13 23:00:00' — use with --once to check the "
                              "historical sample data instead of whatever ingest.live "
                              "has appended most recently")
    args = parser.parse_args()

    if args.once:
        conn = get_connection()
        run_once(conn, args.before)
        conn.close()
    else:
        run(args.interval)
