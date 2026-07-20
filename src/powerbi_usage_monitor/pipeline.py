from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from .api import PowerBIClient
from .config import Settings
from .postgres import sync_sqlite_to_postgres
from .storage import connect, insert_access_events, upsert_inventory


def collect_day(settings: Settings, day: date, sync_postgres: bool = True) -> dict[str, Any]:
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    database_path = settings.output_dir / "powerbi_usage_monitor.db"
    raw_dir = settings.output_dir / "raw" / day.isoformat()
    raw_dir.mkdir(parents=True, exist_ok=True)

    client = PowerBIClient(settings.tenant_id, settings.client_id, settings.client_secret)
    inventory = client.inventory()
    events = client.activity_events(day, settings.timezone)

    (raw_dir / "inventory.json").write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (raw_dir / "activity_events.json").write_text(
        json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    with connect(database_path) as connection:
        upsert_inventory(connection, inventory)
        inserted = insert_access_events(connection, events)

    result: dict[str, Any] = {
        "day": day.isoformat(),
        "events_received": len(events),
        "events_inserted": inserted,
        "database": str(database_path),
    }
    if sync_postgres and settings.postgres_url:
        result["postgres"] = sync_sqlite_to_postgres(
            database_path, settings.postgres_url, settings.postgres_schema
        )
    return result


def collect_history(settings: Settings, history_days: int, sync_postgres: bool = True) -> list[dict[str, Any]]:
    if history_days < 1:
        raise ValueError("history_days must be at least 1")
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=history_days - 1)
    return [
        collect_day(settings, start + timedelta(days=offset), sync_postgres)
        for offset in range(history_days)
    ]


def run_demo(output_dir: str | Path = "output") -> dict[str, Any]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    database_path = output / "powerbi_usage_monitor.db"
    inventory = {
        "workspaces": [{"id": "workspace-demo", "name": "Analytics", "type": "Workspace", "state": "Active"}],
        "datasets": [{"id": "dataset-demo", "workspaceId": "workspace-demo", "name": "Sales Semantic Model", "isRefreshable": True}],
        "reports": [{"id": "report-demo", "workspaceId": "workspace-demo", "datasetId": "dataset-demo", "name": "Executive Sales", "webUrl": "https://example.invalid/report"}],
        "dashboards": [],
    }
    events = [
        {"Id": "event-001", "CreationTime": "2026-07-19T12:00:00Z", "Activity": "ViewReport", "UserId": "analyst@example.invalid", "WorkspaceId": "workspace-demo", "ReportId": "report-demo", "ReportName": "Executive Sales"},
        {"Id": "event-002", "CreationTime": "2026-07-19T14:30:00Z", "Activity": "ViewReport", "UserId": "manager@example.invalid", "WorkspaceId": "workspace-demo", "ReportId": "report-demo", "ReportName": "Executive Sales"},
    ]
    with connect(database_path) as connection:
        upsert_inventory(connection, inventory)
        inserted = insert_access_events(connection, events)
    return {"database": str(database_path), "events_inserted": inserted}
