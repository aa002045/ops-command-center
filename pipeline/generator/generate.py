"""
Ops Command Center — synthetic telemetry generator.

Produces fully fabricated vSAN/vSphere-shaped telemetry: no real customer
names, IPs, or values. Field names and ranges follow publicly documented
vSAN concepts (datastore latency, congestion score, cache-tier usage,
resync backlog, capacity %) — see the build runbook, Phase 01-03.

Run:
    python3 generate.py

Outputs (into ../out/):
    host_metrics.csv
    datastore_metrics.csv
    alert_log.csv

Also writes ../../db/seed_entities.sql and ../../db/signatures.sql so the
same IDs used here line up with what you load into Postgres.
"""

import csv
import json
import math
import os
import random
import uuid
from datetime import datetime, timedelta

random.seed(42)  # deterministic — rerun any time and get the same dataset

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "..", "out")
DB_DIR = os.path.join(HERE, "..", "..", "db")
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(DB_DIR, exist_ok=True)

START = datetime(2026, 9, 12, 0, 0, 0)
INTERVAL_MIN = 2
HOURS = 48
STEPS = HOURS * 60 // INTERVAL_MIN  # 1440 samples per entity

# Fixed, arbitrary namespace UUID used only to derive deterministic entity
# IDs below. uuid.uuid4() draws from OS randomness and is NOT made
# reproducible by random.seed(42) — that seed only controls the metric
# *values* (via the `random` module). Deriving entity IDs from their name
# with uuid.uuid5 instead means reruns always produce the same
# cluster/host/datastore IDs, so a re-generated CSV never goes stale
# against entities you already loaded into Postgres.
ID_NAMESPACE = uuid.UUID("7c9f0b1e-3a4d-4e5f-8a6b-1d2c3e4f5a6b")


def new_id(name):
    return str(uuid.uuid5(ID_NAMESPACE, name))


# --------------------------------------------------------------------------
# Entities — fabricated names, nothing tied to any real site or customer
# --------------------------------------------------------------------------
CLUSTERS = [
    {"id": new_id("cluster-prod-east-01"), "name": "cluster-prod-east-01", "site": "fake-dc-east", "vsan_type": "OSA", "node_count": 4},
    {"id": new_id("cluster-prod-east-02"), "name": "cluster-prod-east-02", "site": "fake-dc-east", "vsan_type": "OSA", "node_count": 4},
    {"id": new_id("cluster-prod-west-01"), "name": "cluster-prod-west-01", "site": "fake-dc-west", "vsan_type": "OSA", "node_count": 4},
    {"id": new_id("cluster-dr-01"), "name": "cluster-dr-01", "site": "fake-dc-west", "vsan_type": "OSA", "node_count": 4},
]

HOSTS = []
for c in CLUSTERS:
    for i in range(1, c["node_count"] + 1):
        host_name = f"{c['name']}-esx{i:02d}"
        HOSTS.append({
            "id": new_id(host_name),
            "cluster_id": c["id"],
            "name": host_name,
            "cpu_cores": 32,
            "mem_total_gb": 512,
        })

DATASTORES = [
    {
        "id": new_id(ds_name := f"{c['name']}-vsan-ds"),
        "cluster_id": c["id"],
        "name": ds_name,
        "type": "vSAN",
        "total_capacity_gb": 46080,
    }
    for c in CLUSTERS
]

DS_BY_CLUSTER = {d["cluster_id"]: d for d in DATASTORES}
HOSTS_BY_CLUSTER = {}
for h in HOSTS:
    HOSTS_BY_CLUSTER.setdefault(h["cluster_id"], []).append(h)

# --------------------------------------------------------------------------
# Injected anomaly windows — one per real, KB-cited Phase 01 signature (see
# db/signatures.sql for the citations). Everything outside these windows is
# ordinary diurnal noise.
# --------------------------------------------------------------------------
NETWORK_LATENCY_HOST = HOSTS_BY_CLUSTER[CLUSTERS[2]["id"]][1]   # one host, cluster-prod-west-01
COMPONENT_LIMIT_HOST = HOSTS_BY_CLUSTER[CLUSTERS[0]["id"]][0]   # one host, cluster-prod-east-01

ANOMALIES = {
    "congestion": {
        # KB 326479 "Understanding Congestion in vSAN" — SSD/cache-tier write
        # buffer fills, congestion score climbs, write IOPS get throttled.
        "cluster": CLUSTERS[1]["id"],          # cluster-prod-east-02
        "start_min": 600, "ramp_min": 60, "hold_min": 30, "decay_min": 30,
    },
    "resync_storm": {
        # KB 438821 "vSAN massive resync ... after exiting Maintenance Mode"
        # — usually benign delta-sync; the tell is backlog steadily draining,
        # not a real failure.
        "cluster": CLUSTERS[3]["id"],          # cluster-dr-01
        "start_min": 1800, "ramp_min": 40, "drain_min": 50,
    },
    "capacity_utilization": {
        # KB 326889 "vSAN Health Service - Capacity utilization" — Yellow at
        # 70%, Red at 90% of the relevant threshold.
        "cluster": CLUSTERS[0]["id"],          # cluster-prod-east-01
        "start_pct": 55.0, "end_pct": 92.0,    # trends across the full window
    },
    "network_latency": {
        # KB 315544 "vSAN Health Service - Network Health - Network Latency
        # Check" — Yellow warning above 5ms ping between vSAN hosts.
        "host": NETWORK_LATENCY_HOST["id"],
        "start_min": 900, "duration_min": 90,
    },
    "host_component_limit": {
        # KB 315533 "vSAN Health Service - Limits - Host component" — Green
        # <80%, Yellow 80-90%, Red >90% of 9,000 components (OSA).
        "host": COMPONENT_LIMIT_HOST["id"],
        "start_pct": 50.0, "end_pct": 93.0,    # trends across the full window
    },
}


def diurnal_load(ts):
    """0..1 load factor, busier 9am-6pm, quiet overnight."""
    hour = ts.hour + ts.minute / 60
    return max(0.05, 0.5 + 0.42 * math.sin((hour - 7) / 24 * 2 * math.pi))


def host_metric_row(host, ts, load, minute_offset, resync_side_effect=0.0):
    row = {
        "host_id": host["id"],
        "ts": ts.isoformat(),
        "cpu_usage_pct": round(min(99, 18 + load * 55 + resync_side_effect * 8 + random.gauss(0, 3)), 2),
        "cpu_ready_pct": round(max(0, 1 + load * 4 + resync_side_effect * 3 + random.gauss(0, 0.6)), 2),
        "mem_usage_pct": round(min(97, 40 + load * 30 + random.gauss(0, 2)), 2),
        "network_latency_ms": round(max(0.1, 0.6 + load * 0.4 + random.gauss(0, 0.15)), 2),
        "component_count_pct": round(35 + random.gauss(0, 2), 2),
    }

    nl = ANOMALIES["network_latency"]
    if host["id"] == nl["host"]:
        t = minute_offset - nl["start_min"]
        if 0 <= t < nl["duration_min"]:
            frac = math.sin((t / nl["duration_min"]) * math.pi)
            row["network_latency_ms"] = round(row["network_latency_ms"] + frac * 9.5, 2)  # crosses the 5ms KB threshold

    hc = ANOMALIES["host_component_limit"]
    if host["id"] == hc["host"]:
        frac = minute_offset / (STEPS * INTERVAL_MIN)
        row["component_count_pct"] = round(
            hc["start_pct"] + frac * (hc["end_pct"] - hc["start_pct"]) + random.gauss(0, 0.4), 2
        )

    return row


def datastore_baseline(ds, ts, load, minute_offset):
    row = {
        "datastore_id": ds["id"],
        "ts": ts.isoformat(),
        "read_latency_ms": round(2 + load * 2.5 + random.gauss(0, 0.35), 2),
        "write_latency_ms": round(3 + load * 3.5 + random.gauss(0, 0.45), 2),
        "iops_read": round(800 + load * 3500 + random.gauss(0, 120)),
        "iops_write": round(500 + load * 2200 + random.gauss(0, 90)),
        "congestion_pct": round(max(0, load * 12 + random.gauss(0, 1.8)), 2),
        "used_capacity_pct": 58.0,
        "cache_tier_usage_pct": round(38 + load * 18 + random.gauss(0, 2.5), 2),
        "resync_backlog_gb": 0.0,
    }

    # capacity utilization: slow linear trend across the whole run, crossing
    # the KB 326889 yellow (70%) and red (90%) thresholds near the end
    exh = ANOMALIES["capacity_utilization"]
    if ds["cluster_id"] == exh["cluster"]:
        frac = minute_offset / (STEPS * INTERVAL_MIN)
        row["used_capacity_pct"] = round(
            exh["start_pct"] + frac * (exh["end_pct"] - exh["start_pct"]) + random.gauss(0, 0.3), 2
        )

    # congestion (KB 326479): SSD/cache-tier write buffer fills (ramp -> hold
    # -> decay), congestion score climbs, write IOPS get throttled — the
    # multi-signal signature Phase 05 is built to catch.
    cs = ANOMALIES["congestion"]
    if ds["cluster_id"] == cs["cluster"]:
        t = minute_offset - cs["start_min"]
        ramp, hold, decay = cs["ramp_min"], cs["hold_min"], cs["decay_min"]
        if 0 <= t < ramp:
            frac = t / ramp
        elif ramp <= t < ramp + hold:
            frac = 1.0
        elif ramp + hold <= t < ramp + hold + decay:
            frac = 1.0 - (t - ramp - hold) / decay
        else:
            frac = None
        if frac is not None:
            row["cache_tier_usage_pct"] = round(row["cache_tier_usage_pct"] + frac * 40, 2)
            row["write_latency_ms"] = round(row["write_latency_ms"] + frac * 17, 2)
            row["congestion_pct"] = round(row["congestion_pct"] + frac * 55, 2)
            row["iops_write"] = round(max(50, row["iops_write"] * (1 - frac * 0.5)))

    # resync / rebalance storm: backlog ramps then drains
    rs = ANOMALIES["resync_storm"]
    resync_side_effect = 0.0
    if ds["cluster_id"] == rs["cluster"]:
        t = minute_offset - rs["start_min"]
        ramp, drain = rs["ramp_min"], rs["drain_min"]
        if 0 <= t < ramp:
            frac = t / ramp
        elif ramp <= t < ramp + drain:
            frac = 1.0 - (t - ramp) / drain
        else:
            frac = None
        if frac is not None:
            row["resync_backlog_gb"] = round(frac * 420, 1)
            row["cache_tier_usage_pct"] = round(row["cache_tier_usage_pct"] + frac * 22, 2)
            resync_side_effect = frac

    return row, resync_side_effect


def build_alert_log():
    alerts = []

    def add(cluster_id, ts, severity, source, message):
        alerts.append({
            "cluster_id": cluster_id, "ts": ts.isoformat(),
            "severity": severity, "source": source, "message": message,
        })

    cs, rs = ANOMALIES["congestion"], ANOMALIES["resync_storm"]
    exh, nl, hc = ANOMALIES["capacity_utilization"], ANOMALIES["network_latency"], ANOMALIES["host_component_limit"]
    add(cs["cluster"], START + timedelta(minutes=cs["start_min"] + 5),
        "warning", "vsan-health", "vSAN health: memory or SSD congestion reached threshold limit")
    add(rs["cluster"], START + timedelta(minutes=rs["start_min"]),
        "info", "vcenter", "vSAN: resync operations in progress following host exit from maintenance mode")
    add(rs["cluster"], START + timedelta(minutes=rs["start_min"] + rs["ramp_min"] + rs["drain_min"] - 5),
        "info", "vcenter", "vSAN: resync operations complete")
    add(exh["cluster"], START + timedelta(minutes=int(STEPS * INTERVAL_MIN * 0.72)),
        "warning", "vsan-health", "vSAN health: capacity utilization on vSAN datastore (yellow, >70%)")
    add(exh["cluster"], START + timedelta(minutes=int(STEPS * INTERVAL_MIN * 0.94)),
        "critical", "vsan-health", "vSAN health: capacity utilization on vSAN datastore (red, >90%)")
    add(HOSTS_BY_CLUSTER[CLUSTERS[2]["id"]][0]["cluster_id"], START + timedelta(minutes=nl["start_min"] + 10),
        "warning", "vsan-health", "vSAN health: network latency check - ping latency above 5ms threshold")
    add(HOSTS_BY_CLUSTER[CLUSTERS[0]["id"]][0]["cluster_id"],
        START + timedelta(minutes=int(STEPS * INTERVAL_MIN * 0.85)),
        "warning", "vsan-health", "vSAN health: host component count approaching per-host limit (yellow, 80-90%)")

    # benign noise, unrelated to any anomaly
    noise = [
        (CLUSTERS[0]["id"], 140, "info", "vcenter", "Snapshot consolidation completed"),
        (CLUSTERS[2]["id"], 300, "info", "vcenter", "NTP time sync warning cleared"),
        (CLUSTERS[1]["id"], 900, "info", "vcenter", "Host exited maintenance mode"),
        (CLUSTERS[3]["id"], 60, "info", "vcenter", "vSphere HA re-established cluster heartbeat"),
    ]
    for cluster_id, offset_min, sev, src, msg in noise:
        add(cluster_id, START + timedelta(minutes=offset_min), sev, src, msg)

    alerts.sort(key=lambda a: a["ts"])
    return alerts


def main():
    host_rows, ds_rows = [], []

    for step in range(STEPS):
        minute_offset = step * INTERVAL_MIN
        ts = START + timedelta(minutes=minute_offset)
        load = diurnal_load(ts)

        # compute datastore rows first (also yields resync side-effect for hosts)
        resync_effect_by_cluster = {}
        for ds in DATASTORES:
            row, resync_effect = datastore_baseline(ds, ts, load, minute_offset)
            ds_rows.append(row)
            resync_effect_by_cluster[ds["cluster_id"]] = resync_effect

        for host in HOSTS:
            effect = resync_effect_by_cluster.get(host["cluster_id"], 0.0)
            host_rows.append(host_metric_row(host, ts, load, minute_offset, effect))

    alerts = build_alert_log()

    # ---- write CSVs ----
    def write_csv(path, rows, fieldnames):
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)

    write_csv(os.path.join(OUT_DIR, "host_metrics.csv"), host_rows,
              ["host_id", "ts", "cpu_usage_pct", "cpu_ready_pct", "mem_usage_pct",
               "network_latency_ms", "component_count_pct"])
    write_csv(os.path.join(OUT_DIR, "datastore_metrics.csv"), ds_rows,
              ["datastore_id", "ts", "read_latency_ms", "write_latency_ms", "iops_read", "iops_write",
               "congestion_pct", "used_capacity_pct", "cache_tier_usage_pct", "resync_backlog_gb"])
    write_csv(os.path.join(OUT_DIR, "alert_log.csv"), alerts,
              ["cluster_id", "ts", "severity", "source", "message"])

    # ---- write seed_entities.sql ----
    def sql_str(v):
        return "'" + str(v).replace("'", "''") + "'"

    lines = ["-- Fabricated seed data. No real customer/site names or values.", ""]
    for c in CLUSTERS:
        lines.append(
            f"insert into clusters (id, name, site, vsan_type, node_count) values "
            f"({sql_str(c['id'])}, {sql_str(c['name'])}, {sql_str(c['site'])}, "
            f"{sql_str(c['vsan_type'])}, {c['node_count']});"
        )
    lines.append("")
    for h in HOSTS:
        lines.append(
            f"insert into hosts (id, cluster_id, name, cpu_cores, mem_total_gb) values "
            f"({sql_str(h['id'])}, {sql_str(h['cluster_id'])}, {sql_str(h['name'])}, "
            f"{h['cpu_cores']}, {h['mem_total_gb']});"
        )
    lines.append("")
    for d in DATASTORES:
        lines.append(
            f"insert into datastores (id, cluster_id, name, type, total_capacity_gb) values "
            f"({sql_str(d['id'])}, {sql_str(d['cluster_id'])}, {sql_str(d['name'])}, "
            f"{sql_str(d['type'])}, {d['total_capacity_gb']});"
        )
    with open(os.path.join(DB_DIR, "seed_entities.sql"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    # ---- write signatures.sql (Phase 01 table, grounded in real vSAN KB
    # articles rather than invented thresholds — see "source" on each) ----
    SIGNATURES = [
        {
            "name": "congestion",
            "description": "Congestion score climbs (SSD/cache-tier write buffer, log space, or memory "
                            "heap) while write IOPS drop and write latency rises — vSAN's own flow-control "
                            "throttling writes at the front door before it cascades downstream.",
            "detection_rule": {"signals": ["congestion_pct", "cache_tier_usage_pct", "iops_write", "write_latency_ms"],
                                "logic": "congestion_pct AND cache_tier_usage_pct trending up, iops_write trending down"},
            "default_severity": "warning",
            "source": "Broadcom KB 326479 'Understanding Congestion in vSAN'; KB 327050 'vSAN memory or SSD congestion reached threshold limit'",
        },
        {
            "name": "capacity_utilization",
            "description": "Used capacity crosses documented vSAN Health Service thresholds: Yellow at 70%, "
                            "Red at 90%. Past Red, vSAN has limited functionality — storage vMotion, VM "
                            "creation/power-on, and snapshot operations start failing.",
            "detection_rule": {"signals": ["used_capacity_pct"],
                                "logic": "used_capacity_pct >= 70 -> warning, >= 90 -> critical"},
            "default_severity": "critical",
            "source": "Broadcom KB 326889 'vSAN Health Service - Capacity utilization'",
        },
        {
            "name": "resync_storm_post_maintenance",
            "description": "Resync backlog spikes immediately after a host exits Maintenance Mode (delta-"
                            "sync of components that went stale under 'Ensure accessibility'). Usually "
                            "benign in small (3-4 node) clusters — the tell is whether the backlog is "
                            "steadily draining (expected) or flat/growing (investigate as a real fault).",
            "detection_rule": {"signals": ["resync_backlog_gb"],
                                "logic": "resync_backlog_gb spikes after maintenance-mode exit; classify by whether it is draining"},
            "default_severity": "warning",
            "source": "Broadcom KB 438821 'vSAN massive resync and degraded object health alerts after exiting Maintenance Mode'",
        },
        {
            "name": "network_latency",
            "description": "Inter-host ping latency exceeds vSAN's documented 5ms warning threshold — "
                            "vSAN performance depends on low, consistent latency between hosts, so this "
                            "points at a NIC, switch, or uplink problem before it shows up as I/O latency.",
            "detection_rule": {"signals": ["network_latency_ms"],
                                "logic": "network_latency_ms > 5 sustained"},
            "default_severity": "warning",
            "source": "Broadcom KB 315544 'vSAN Health Service - Network Health - Network Latency Check'",
        },
        {
            "name": "host_component_limit",
            "description": "A host's component count approaches the per-host ceiling (9,000 on OSA). "
                            "Green <80%, Yellow 80-90%, Red >90%. Past Red, new VM deployment and rebuild "
                            "operations fail outright — this is a hard capacity wall, not a soft one.",
            "detection_rule": {"signals": ["component_count_pct"],
                                "logic": "component_count_pct >= 80 -> warning, >= 90 -> critical"},
            "default_severity": "critical",
            "source": "Broadcom KB 315533 'vSAN Health Service - Limits - Host component'; KB 315507 'vSAN Component Limit per Cluster'",
        },
    ]
    sig_lines = ["-- Phase 01 bottleneck signatures, grounded in real Broadcom/VMware KB articles.", ""]
    for s in SIGNATURES:
        rule_json = json.dumps(s["detection_rule"]).replace("'", "''")
        desc = s["description"].replace("'", "''")
        src = s["source"].replace("'", "''")
        sig_lines.append(
            f"insert into bottleneck_signatures (id, name, description, detection_rule, default_severity, source_reference) "
            f"values (gen_random_uuid(), {sql_str(s['name'])}, '{desc}', '{rule_json}'::jsonb, "
            f"{sql_str(s['default_severity'])}, '{src}');"
        )
    with open(os.path.join(DB_DIR, "signatures.sql"), "w", encoding="utf-8") as f:
        f.write("\n".join(sig_lines) + "\n")

    print(f"host_metrics: {len(host_rows)} rows")
    print(f"datastore_metrics: {len(ds_rows)} rows")
    print(f"alert_log: {len(alerts)} rows")
    print(f"clusters={len(CLUSTERS)} hosts={len(HOSTS)} datastores={len(DATASTORES)}")


if __name__ == "__main__":
    main()
