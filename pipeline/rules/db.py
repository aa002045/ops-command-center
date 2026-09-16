"""Shared Postgres connection for the anomaly-detection engine.

Same pattern as pipeline/ingest/db.py, duplicated on purpose rather than
imported across packages — keeps `rules` runnable on its own without
needing `ingest` installed alongside it.
"""
import os

import psycopg2

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:devpass@localhost:5432/occ"
)


def get_connection():
    return psycopg2.connect(DATABASE_URL)
