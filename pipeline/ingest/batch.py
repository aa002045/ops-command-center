"""Phase 04 batch ingestion: read CSV files, clean them, load into Postgres
with idempotent upserts — safe to rerun without creating duplicates.

This replaces the manual `\\copy` commands from Phase 02 with a real
pipeline: every row is validated (clean.py) before it's allowed near the
database, and every insert is ON CONFLICT DO NOTHING keyed on the natural
key (host_id+ts, datastore_id+ts, cluster_id+ts+message) rather than
relying on the file only ever being loaded once.

Run:
    python3 -m ingest.batch
    python3 -m ingest.batch --dir ../out    # if not running from pipeline/

Requires: pip install psycopg2-binary
"""
import argparse
import csv
import os
import sys

from psycopg2.extras import execute_values

from ingest.clean import clean_datastore_row, clean_host_row
from ingest.db import get_connection

HOST_COLUMNS = ["host_id", "ts", "cpu_usage_pct", "cpu_ready_pct", "mem_usage_pct",
                "network_latency_ms", "component_count_pct"]
DATASTORE_COLUMNS = ["datastore_id", "ts", "read_latency_ms", "write_latency_ms",
                      "iops_read", "iops_write", "congestion_pct", "used_capacity_pct",
                      "cache_tier_usage_pct", "resync_backlog_gb"]
ALERT_COLUMNS = ["cluster_id", "ts", "severity", "source", "message"]


def read_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def load_rows(conn, table, columns, conflict_columns, rows, label):
    if not rows:
        print(f"{label}: nothing to load")
        return

    values = [tuple(r[c] if r[c] != "" else None for c in columns) for r in rows]
    cols_sql = ", ".join(columns)
    conflict_sql = ", ".join(conflict_columns)

    with conn.cursor() as cur:
        # `returning 1` + fetch=True is required for an accurate count here:
        # execute_values splits large inserts into multiple pages (one INSERT
        # per page), and cur.rowcount after it only reflects the LAST page's
        # result, not the true total. Rows that hit "on conflict do nothing"
        # produce no RETURNING row, so counting what comes back across every
        # page gives the real number of rows actually inserted.
        inserted_rows = execute_values(
            cur,
            f"insert into {table} ({cols_sql}) values %s "
            f"on conflict ({conflict_sql}) do nothing "
            f"returning 1",
            values,
            page_size=1000,
            fetch=True,
        )
        inserted = len(inserted_rows)
    conn.commit()
    print(f"{label}: {len(rows)} rows read, {inserted} newly inserted "
          f"({len(rows) - inserted} already present, skipped)")


def run(data_dir):
    conn = get_connection()

    # ---- host_metrics ----
    raw = read_csv(os.path.join(data_dir, "host_metrics.csv"))
    clean_rows, dropped = [], []
    for row in raw:
        cleaned, reason = clean_host_row(row)
        if cleaned:
            clean_rows.append(cleaned)
        else:
            dropped.append((row, reason))
    for row, reason in dropped[:10]:
        print(f"  dropped host_metrics row: {reason} -> {row}", file=sys.stderr)
    if len(dropped) > 10:
        print(f"  ... and {len(dropped) - 10} more dropped rows", file=sys.stderr)
    load_rows(conn, "host_metrics", HOST_COLUMNS, ["host_id", "ts"], clean_rows, "host_metrics")

    # ---- datastore_metrics ----
    raw = read_csv(os.path.join(data_dir, "datastore_metrics.csv"))
    clean_rows, dropped = [], []
    for row in raw:
        cleaned, reason = clean_datastore_row(row)
        if cleaned:
            clean_rows.append(cleaned)
        else:
            dropped.append((row, reason))
    for row, reason in dropped[:10]:
        print(f"  dropped datastore_metrics row: {reason} -> {row}", file=sys.stderr)
    if len(dropped) > 10:
        print(f"  ... and {len(dropped) - 10} more dropped rows", file=sys.stderr)
    load_rows(conn, "datastore_metrics", DATASTORE_COLUMNS, ["datastore_id", "ts"],
              clean_rows, "datastore_metrics")

    # ---- alert_log (no cleaning rules needed — it's just text) ----
    raw = read_csv(os.path.join(data_dir, "alert_log.csv"))
    load_rows(conn, "alert_log", ALERT_COLUMNS, ["cluster_id", "ts", "message"],
              raw, "alert_log")

    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", default=os.path.join(os.path.dirname(__file__), "..", "out"))
    args = parser.parse_args()
    run(args.dir)
