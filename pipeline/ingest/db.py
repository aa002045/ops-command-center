"""Shared Postgres connection for the ingestion pipeline."""
import os

import psycopg2

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:devpass@localhost:5432/occ"
)


def get_connection():
    return psycopg2.connect(DATABASE_URL)
