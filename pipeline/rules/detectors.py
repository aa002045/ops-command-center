"""Phase 05 signature detectors — one function per Phase 01 KB-grounded
bottleneck signature (see db/signatures.sql for the exact citations).

Each function takes a rolling window of recent samples for ONE entity
(a datastore or a host), oldest first, and returns:

    (matched: bool, confidence: float 0..1, evidence: dict)

`evidence` is what a Phase 07 alert panel would show a viewer — the actual
numbers that tripped the signature, not just a yes/no. Thresholds below
were calibrated against the real injected anomalies in the sample dataset
(pipeline/out/*.csv) — see pipeline/rules/README.md for the exact before/
during/after values used to pick each number.

Two datastore-metric samples and two host-metric samples per dict, always
in this shape:
  datastore sample: {"ts", "congestion_pct", "cache_tier_usage_pct",
                      "iops_write", "used_capacity_pct", "resync_backlog_gb"}
  host sample:       {"ts", "network_latency_ms", "component_count_pct"}
"""
from .trend import slope

MIN_SAMPLES = 4


def detect_congestion(samples):
    """KB 326479 'Understanding Congestion in vSAN'; KB 327050 'vSAN memory
    or SSD congestion reached threshold limit'.

    Congestion score and cache-tier usage climbing together, elevated above
    baseline — not just a single high reading, which could be noise.
    """
    if len(samples) < MIN_SAMPLES:
        return False, 0.0, {}

    congestion = [s["congestion_pct"] for s in samples]
    cache = [s["cache_tier_usage_pct"] for s in samples]
    iops_write = [s["iops_write"] for s in samples]

    congestion_rising = slope(congestion) > 0.3
    cache_rising = slope(cache) > 0.3
    elevated = congestion[-1] > 20 and cache[-1] > 60

    if congestion_rising and cache_rising and elevated:
        confidence = round(min(1.0, 0.45 + (congestion[-1] - 20) / 70 + (cache[-1] - 60) / 100), 2)
        return True, confidence, {
            "congestion_pct": congestion[-1],
            "cache_tier_usage_pct": cache[-1],
            "iops_write": iops_write[-1],
            "congestion_trend_per_sample": round(slope(congestion), 2),
        }
    return False, 0.0, {}


def detect_capacity_utilization(samples):
    """KB 326889 'vSAN Health Service - Capacity utilization' — Yellow at
    70%, Red at 90%. A static threshold on the current reading, exactly as
    the KB defines it — no trend requirement needed.
    """
    if not samples:
        return False, 0.0, {}

    latest = samples[-1]["used_capacity_pct"]
    if latest >= 90:
        return True, round(min(1.0, 0.75 + (latest - 90) / 40), 2), {
            "used_capacity_pct": latest, "threshold": "critical (>=90%)",
        }
    if latest >= 70:
        return True, round(0.4 + (latest - 70) / 40, 2), {
            "used_capacity_pct": latest, "threshold": "warning (>=70%)",
        }
    return False, 0.0, {}


def detect_resync_storm(samples):
    """KB 438821 'vSAN massive resync and degraded object health alerts
    after exiting Maintenance Mode' — backlog spikes after a host exits
    Maintenance Mode. Usually benign; the tell is whether it's draining
    (falling) or stuck/growing (worth a closer look), so severity — not
    just whether it fires — depends on the trend direction.
    """
    if len(samples) < MIN_SAMPLES:
        return False, 0.0, {}

    backlog = [s["resync_backlog_gb"] for s in samples]
    latest = backlog[-1]
    if latest < 30:
        return False, 0.0, {}

    draining = slope(backlog) < 0
    confidence = round(min(1.0, 0.3 + latest / 500), 2)
    return True, confidence, {
        "resync_backlog_gb": latest,
        "draining": draining,
        "note": "steadily draining — expected post-maintenance behavior" if draining
                else "not draining — worth investigating as a possible real fault",
    }


def detect_network_latency(samples):
    """KB 315544 'vSAN Health Service - Network Health - Network Latency
    Check' — Yellow warning above 5ms ping between vSAN hosts. Requires the
    last two samples both over the line, not just one, so a single noisy
    reading doesn't fire an alert.
    """
    if len(samples) < 2:
        return False, 0.0, {}

    latest, prior = samples[-1]["network_latency_ms"], samples[-2]["network_latency_ms"]
    if latest > 5 and prior > 5:
        confidence = round(min(1.0, 0.5 + (latest - 5) / 15), 2)
        return True, confidence, {"network_latency_ms": latest, "threshold_ms": 5}
    return False, 0.0, {}


def detect_host_component_limit(samples):
    """KB 315533 'vSAN Health Service - Limits - Host component'; KB 315507
    'vSAN Component Limit per Cluster' — Green <80%, Yellow 80-90%, Red
    >90% of the 9,000-component-per-host ceiling (OSA). Static threshold on
    the current reading, same shape as capacity utilization.
    """
    if not samples:
        return False, 0.0, {}

    latest = samples[-1]["component_count_pct"]
    if latest >= 90:
        return True, round(min(1.0, 0.75 + (latest - 90) / 40), 2), {
            "component_count_pct": latest, "threshold": "critical (>=90%)",
        }
    if latest >= 80:
        return True, round(0.4 + (latest - 80) / 40, 2), {
            "component_count_pct": latest, "threshold": "warning (>=80%)",
        }
    return False, 0.0, {}


# Registry keyed on bottleneck_signatures.name — this is what maps a
# detector function to the row in Postgres that carries its KB citation
# and description, so the engine never hardcodes a signature's UUID.
DATASTORE_DETECTORS = {
    "congestion": detect_congestion,
    "capacity_utilization": detect_capacity_utilization,
    "resync_storm_post_maintenance": detect_resync_storm,
}
HOST_DETECTORS = {
    "network_latency": detect_network_latency,
    "host_component_limit": detect_host_component_limit,
}
