from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def stable_id(prefix: str, payload: dict[str, Any]) -> str:
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return f"{prefix}_{hashlib.sha256(text.encode('utf-8')).hexdigest()}"


def connect(path: str | Path) -> sqlite3.Connection:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(target)
    connection.row_factory = sqlite3.Row
    create_schema(connection)
    return connection


def create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS dim_workspace (
            workspace_id TEXT PRIMARY KEY,
            workspace_name TEXT,
            workspace_type TEXT,
            state TEXT,
            loaded_at_utc TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS dim_dataset (
            dataset_id TEXT PRIMARY KEY,
            workspace_id TEXT,
            dataset_name TEXT,
            is_refreshable INTEGER,
            loaded_at_utc TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS dim_report (
            report_id TEXT PRIMARY KEY,
            workspace_id TEXT,
            dataset_id TEXT,
            report_name TEXT,
            web_url TEXT,
            loaded_at_utc TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS dim_dashboard (
            dashboard_id TEXT PRIMARY KEY,
            workspace_id TEXT,
            dashboard_name TEXT,
            web_url TEXT,
            loaded_at_utc TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS fact_access_event (
            event_id TEXT PRIMARY KEY,
            event_time_utc TEXT,
            activity TEXT,
            user_id TEXT,
            workspace_id TEXT,
            item_type TEXT,
            item_id TEXT,
            item_name TEXT,
            client_ip TEXT,
            raw_json TEXT,
            loaded_at_utc TEXT NOT NULL
        );

        CREATE VIEW IF NOT EXISTS vw_inventory AS
        SELECT 'Report' AS item_type, report_id AS item_id, report_name AS item_name,
               workspace_id, dataset_id
        FROM dim_report
        UNION ALL
        SELECT 'Dashboard', dashboard_id, dashboard_name, workspace_id, NULL
        FROM dim_dashboard;

        CREATE VIEW IF NOT EXISTS vw_adoption_daily AS
        SELECT substr(event_time_utc, 1, 10) AS access_date,
               workspace_id, item_type, item_id, max(item_name) AS item_name,
               count(*) AS accesses, count(DISTINCT user_id) AS unique_users
        FROM fact_access_event
        GROUP BY substr(event_time_utc, 1, 10), workspace_id, item_type, item_id;
        """
    )
    connection.commit()


def _loaded_at() -> str:
    return datetime.now(timezone.utc).isoformat()


def upsert_inventory(
    connection: sqlite3.Connection,
    inventory: dict[str, list[dict[str, Any]]],
) -> None:
    loaded_at = _loaded_at()
    for row in inventory.get("workspaces", []):
        workspace_id = row.get("id")
        if not workspace_id:
            continue
        connection.execute(
            """
            INSERT INTO dim_workspace VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(workspace_id) DO UPDATE SET
                workspace_name=excluded.workspace_name,
                workspace_type=excluded.workspace_type,
                state=excluded.state,
                loaded_at_utc=excluded.loaded_at_utc
            """,
            (
                workspace_id,
                row.get("name"),
                row.get("type"),
                row.get("state"),
                loaded_at,
            ),
        )

    mappings = (
        ("datasets", "dim_dataset", "dataset_id", "id", "name"),
        ("reports", "dim_report", "report_id", "id", "name"),
        ("dashboards", "dim_dashboard", "dashboard_id", "id", "displayName"),
    )
    for source, table, pk, id_field, name_field in mappings:
        for row in inventory.get(source, []):
            item_id = row.get(id_field)
            if not item_id:
                continue
            if table == "dim_dataset":
                connection.execute(
                    """
                    INSERT INTO dim_dataset VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(dataset_id) DO UPDATE SET
                        workspace_id=excluded.workspace_id,
                        dataset_name=excluded.dataset_name,
                        is_refreshable=excluded.is_refreshable,
                        loaded_at_utc=excluded.loaded_at_utc
                    """,
                    (
                        item_id,
                        row.get("workspaceId"),
                        row.get(name_field),
                        int(bool(row.get("isRefreshable"))),
                        loaded_at,
                    ),
                )
            elif table == "dim_report":
                connection.execute(
                    """
                    INSERT INTO dim_report VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(report_id) DO UPDATE SET
                        workspace_id=excluded.workspace_id,
                        dataset_id=excluded.dataset_id,
                        report_name=excluded.report_name,
                        web_url=excluded.web_url,
                        loaded_at_utc=excluded.loaded_at_utc
                    """,
                    (
                        item_id,
                        row.get("workspaceId"),
                        row.get("datasetId"),
                        row.get(name_field),
                        row.get("webUrl"),
                        loaded_at,
                    ),
                )
            else:
                connection.execute(
                    """
                    INSERT INTO dim_dashboard VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(dashboard_id) DO UPDATE SET
                        workspace_id=excluded.workspace_id,
                        dashboard_name=excluded.dashboard_name,
                        web_url=excluded.web_url,
                        loaded_at_utc=excluded.loaded_at_utc
                    """,
                    (
                        item_id,
                        row.get("workspaceId"),
                        row.get(name_field) or row.get("name"),
                        row.get("webUrl"),
                        loaded_at,
                    ),
                )
    connection.commit()


def insert_access_events(
    connection: sqlite3.Connection,
    events: list[dict[str, Any]],
) -> int:
    loaded_at = _loaded_at()
    inserted = 0
    for event in events:
        activity = event.get("Activity") or "Unknown"
        item_type = "Dashboard" if "Dashboard" in activity else "Report"
        item_id = event.get("DashboardId") or event.get("ReportId")
        event_id = event.get("Id") or stable_id("evt", event)
        cursor = connection.execute(
            """
            INSERT OR IGNORE INTO fact_access_event VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                event.get("CreationTime"),
                activity,
                event.get("UserId"),
                event.get("WorkspaceId"),
                item_type,
                item_id,
                event.get("DashboardName") or event.get("ReportName"),
                event.get("ClientIP"),
                json.dumps(event, ensure_ascii=False),
                loaded_at,
            ),
        )
        inserted += cursor.rowcount
    connection.commit()
    return inserted
