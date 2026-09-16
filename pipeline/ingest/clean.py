"""Validation/cleaning rules for incoming telemetry rows.

Each function returns the row unchanged if it's valid, or None if the row
should be dropped. Callers are responsible for logging what gets dropped
(see batch.py and live.py) — silently swallowing bad rows would hide real
pipeline problems.

Rules, matching Phase 04 of the runbook:
  - required numeric fields must be present (not null/empty)
  - latency fields must not be negative
  - percentage fields must be within 0-100
  - single-sample spikes that revert within one interval are left ALONE
    here — that's a job for the trend detector in Phase 05, not the
    cleaning layer. Clamping them here would erase the exact signal the
    anomaly engine is built to catch.
"""

HOST_REQUIRED = ["host_id", "ts", "cpu_usage_pct", "cpu_ready_pct", "mem_usage_pct"]
HOST_PCT_FIELDS = ["cpu_usage_pct", "cpu_ready_pct", "mem_usage_pct", "component_count_pct"]
HOST_LATENCY_FIELDS = ["network_latency_ms"]

DATASTORE_REQUIRED = ["datastore_id", "ts", "read_latency_ms", "write_latency_ms"]
DATASTORE_PCT_FIELDS = ["congestion_pct", "used_capacity_pct", "cache_tier_usage_pct"]
DATASTORE_LATENCY_FIELDS = ["read_latency_ms", "write_latency_ms"]


def _missing_required(row, required_fields):
    for f in required_fields:
        v = row.get(f)
        if v is None or v == "":
            return f
    return None


def _out_of_range_pct(row, pct_fields):
    for f in pct_fields:
        v = row.get(f)
        if v is None:
            continue
        if float(v) < 0 or float(v) > 100:
            return f, v
    return None


def _negative_latency(row, latency_fields):
    for f in latency_fields:
        v = row.get(f)
        if v is None:
            continue
        if float(v) < 0:
            return f, v
    return None


def clean_host_row(row):
    """Returns (row, None) if valid, or (None, reason) if dropped."""
    missing = _missing_required(row, HOST_REQUIRED)
    if missing:
        return None, f"missing required field '{missing}'"

    bad_pct = _out_of_range_pct(row, HOST_PCT_FIELDS)
    if bad_pct:
        return None, f"{bad_pct[0]}={bad_pct[1]} out of 0-100 range"

    bad_latency = _negative_latency(row, HOST_LATENCY_FIELDS)
    if bad_latency:
        return None, f"{bad_latency[0]}={bad_latency[1]} is negative"

    return row, None


def clean_datastore_row(row):
    missing = _missing_required(row, DATASTORE_REQUIRED)
    if missing:
        return None, f"missing required field '{missing}'"

    bad_pct = _out_of_range_pct(row, DATASTORE_PCT_FIELDS)
    if bad_pct:
        return None, f"{bad_pct[0]}={bad_pct[1]} out of 0-100 range"

    bad_latency = _negative_latency(row, DATASTORE_LATENCY_FIELDS)
    if bad_latency:
        return None, f"{bad_latency[0]}={bad_latency[1]} is negative"

    return row, None
