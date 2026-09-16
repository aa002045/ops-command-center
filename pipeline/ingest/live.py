"""Phase 04 "live" ingestion mode — appends one new batch of telemetry to
Postgres every LIVE_INTERVAL_SECONDS, using the same signal shapes as the
Phase 03 generator but reading real entity IDs from the database instead of
regenerating fake ones. This is what makes the React dashboard (Phase 07)
feel alive during a demo instead of showing a static, already-loaded dataset.

Run:
    python3 -m ingest.live
    python3 -m ingest.live --inject congestion --inject-after 1

Stop with Ctrl+C.
"""
import argparse
import math
import random
import time
from datetime import datetime, timezone

from psycopg2.extras import execute_values

from ingest.db import get_connection

LIVE_INTERVAL_SECONDS = 12
RAMP_MINUTES = 2  # injected anomaly: ramps up over this long, then back down


def fetch_entities(conn):
    with conn.cursor() as cur:
        cur.execute("select id, cluster_id from hosts")
        hosts = cur.fetchall()
        cur.execute("select id, cluster_id from datastores")
        datastores = cur.fetchall()
    return hosts, datastores


def diurnal_load(ts):
    hour = ts.hour + ts.minute / 60
    return max(0.05, 0.5 + 0.42 * math.sin((hour - 7) / 24 * 2 * math.pi))


def host_row(host_id, ts, load):
    return (
        host_id, ts,
        round(min(99, 18 + load * 55 + random.gauss(0, 3)), 2),
        round(max(0, 1 + load * 4 + random.gauss(0, 0.6)), 2),
        round(min(97, 40 + load * 30 + random.gauss(0, 2)), 2),
        round(max(0.1, 0.6 + load * 0.4 + random.gauss(0, 0.15)), 2),
        round(35 + random.gauss(0, 2), 2),
    )


def datastore_row(ds_id, ts, load, inject_frac=0.0):
    congestion = round(max(0, load * 12 + random.gauss(0, 1.8)) + inject_frac * 55, 2)
    write_latency = round(3 + load * 3.5 + random.gauss(0, 0.45) + inject_frac * 17, 2)
    cache = round(38 + load * 18 + random.gauss(0, 2.5) + inject_frac * 40, 2)
    iops_write = round(max(50, (500 + load * 2200 + random.gauss(0, 90)) * (1 - inject_frac * 0.5)))
    return (
        ds_id, ts,
        round(2 + load * 2.5 + random.gauss(0, 0.35), 2),
        write_latency,
        round(800 + load * 3500 + random.gauss(0, 120)),
        iops_write,
        congestion,
        58.0,
        cache,
        0.0,
    )


def injected_fraction(elapsed_min, inject_after):
    """Triangular ramp: up over RAMP_MINUTES, back down over the next RAMP_MINUTES."""
    t = elapsed_min - inject_after
    if t < 0:
        return 0.0
    if t < RAMP_MINUTES:
        return t / RAMP_MINUTES
    if t < RAMP_MINUTES * 2:
        return 1.0 - (t - RAMP_MINUTES) / RAMP_MINUTES
    return 0.0


def run(inject, inject_after):
    conn = get_connection()
    hosts, datastores = fetch_entities(conn)
    if not hosts or not datastores:
        print("No hosts/datastores found — run db/seed_entities.sql first.")
        return

    print(f"live mode: {len(hosts)} hosts, {len(datastores)} datastores, "
          f"new batch every {LIVE_INTERVAL_SECONDS}s. Ctrl+C to stop.")
    if inject:
        print(f"will inject a '{inject}' pattern on one datastore starting "
              f"~{inject_after} min from now, ramping over {RAMP_MINUTES} min each way")

    inject_target = datastores[0][0] if inject else None
    start = time.monotonic()

    try:
        while True:
            ts = datetime.now(timezone.utc)
            load = diurnal_load(ts)
            elapsed_min = (time.monotonic() - start) / 60
            inject_frac = injected_fraction(elapsed_min, inject_after) if inject_target else 0.0

            host_rows = [host_row(h[0], ts, load) for h in hosts]
            ds_rows = [
                datastore_row(d[0], ts, load, inject_frac if d[0] == inject_target else 0.0)
                for d in datastores
            ]

            with conn.cursor() as cur:
                execute_values(
                    cur,
                    "insert into host_metrics (host_id, ts, cpu_usage_pct, cpu_ready_pct, "
                    "mem_usage_pct, network_latency_ms, component_count_pct) values %s "
                    "on conflict (host_id, ts) do nothing",
                    host_rows,
                )
                execute_values(
                    cur,
                    "insert into datastore_metrics (datastore_id, ts, read_latency_ms, "
                    "write_latency_ms, iops_read, iops_write, congestion_pct, used_capacity_pct, "
                    "cache_tier_usage_pct, resync_backlog_gb) values %s "
                    "on conflict (datastore_id, ts) do nothing",
                    ds_rows,
                )
            conn.commit()

            tag = f"  [{inject} injecting, frac={inject_frac:.2f}]" if inject_frac > 0 else ""
            print(f"{ts.isoformat()}  +{len(host_rows)} host rows, +{len(ds_rows)} datastore rows{tag}")
            time.sleep(LIVE_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("\nstopped.")
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--inject", choices=["congestion"], default=None,
                         help="ramp a congestion-style anomaly on one datastore during the run")
    parser.add_argument("--inject-after", type=float, default=1.0,
                         help="minutes after start before the injected anomaly begins")
    args = parser.parse_args()
    run(args.inject, args.inject_after)
