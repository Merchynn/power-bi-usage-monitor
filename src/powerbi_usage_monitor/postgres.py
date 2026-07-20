from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text

TABLES = (
    ("dim_workspace", "workspace_id"),
    ("dim_dataset", "dataset_id"),
    ("dim_report", "report_id"),
    ("dim_dashboard", "dashboard_id"),
    ("fact_access_event", "event_id"),
)


def validate_identifier(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise ValueError(f"Invalid SQL identifier: {value!r}")
    return value


def sqlite_type_to_postgres(declared_type: str) -> str:
    upper = (declared_type or "").upper()
    if "INT" in upper:
        return "BIGINT"
    if "REAL" in upper or "FLOA" in upper or "DOUB" in upper:
        return "DOUBLE PRECISION"
    return "TEXT"


def sync_sqlite_to_postgres(
    sqlite_path: str | Path,
    postgres_url: str,
    schema: str = "powerbi_monitor",
) -> dict[str, int]:
    source_path = Path(sqlite_path)
    if not source_path.exists():
        raise FileNotFoundError(source_path)

    schema = validate_identifier(schema)
    engine = create_engine(postgres_url, pool_pre_ping=True)
    counts: dict[str, int] = {}

    with sqlite3.connect(source_path) as sqlite_connection:
        sqlite_connection.row_factory = sqlite3.Row
        with engine.begin() as target:
            target.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))

            for table, primary_key in TABLES:
                table = validate_identifier(table)
                primary_key = validate_identifier(primary_key)
                metadata = sqlite_connection.execute(
                    f'PRAGMA table_info("{table}")'
                ).fetchall()
                if not metadata:
                    continue

                columns = [str(row[1]) for row in metadata]
                ddl_columns = []
                for row in metadata:
                    name = validate_identifier(str(row[1]))
                    data_type = sqlite_type_to_postgres(str(row[2]))
                    suffix = " PRIMARY KEY" if name == primary_key else ""
                    ddl_columns.append(f'"{name}" {data_type}{suffix}')
                target.execute(
                    text(
                        f'CREATE TABLE IF NOT EXISTS "{schema}"."{table}" '
                        f'({", ".join(ddl_columns)})'
                    )
                )

                quoted_columns = ", ".join(f'"{column}"' for column in columns)
                parameters = ", ".join(f':{column}' for column in columns)
                updates = ", ".join(
                    f'"{column}" = EXCLUDED."{column}"'
                    for column in columns
                    if column != primary_key
                )
                statement = text(
                    f'INSERT INTO "{schema}"."{table}" ({quoted_columns}) '
                    f'VALUES ({parameters}) '
                    f'ON CONFLICT ("{primary_key}") DO UPDATE SET {updates}'
                )
                rows = [dict(row) for row in sqlite_connection.execute(f'SELECT * FROM "{table}"')]
                if rows:
                    target.execute(statement, rows)
                counts[table] = len(rows)

            target.execute(
                text(
                    f'''CREATE OR REPLACE VIEW "{schema}".vw_adoption_daily AS
                    SELECT substr(event_time_utc, 1, 10) AS access_date,
                           workspace_id, item_type, item_id,
                           max(item_name) AS item_name,
                           count(*) AS accesses,
                           count(DISTINCT user_id) AS unique_users
                    FROM "{schema}".fact_access_event
                    GROUP BY substr(event_time_utc, 1, 10), workspace_id, item_type, item_id'''
                )
            )
    return counts
