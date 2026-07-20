from __future__ import annotations

import time
from datetime import date, datetime, time as dt_time, timedelta, timezone
from typing import Any, Iterable
from zoneinfo import ZoneInfo

import msal
import requests

API_BASE = "https://api.powerbi.com/v1.0/myorg"
SCOPE = ["https://analysis.windows.net/powerbi/api/.default"]


class PowerBIAPIError(RuntimeError):
    pass


def local_day_window_utc(day: date, timezone_name: str) -> tuple[datetime, datetime]:
    tz = ZoneInfo(timezone_name)
    start_local = datetime.combine(day, dt_time.min, tzinfo=tz)
    end_local = start_local + timedelta(days=1) - timedelta(milliseconds=1)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)


def iso_z(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


class PowerBIClient:
    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        timeout: int = 60,
        retries: int = 4,
    ) -> None:
        authority = f"https://login.microsoftonline.com/{tenant_id}"
        app = msal.ConfidentialClientApplication(
            client_id=client_id,
            authority=authority,
            client_credential=client_secret,
        )
        token_result = app.acquire_token_for_client(scopes=SCOPE)
        token = token_result.get("access_token")
        if not token:
            raise PowerBIAPIError(
                token_result.get("error_description") or "Power BI authentication failed"
            )
        self.timeout = timeout
        self.retries = retries
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {token}"})

    def get_json(
        self,
        url: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        for attempt in range(self.retries + 1):
            response = self.session.get(url, params=params, timeout=self.timeout)
            if response.status_code == 429 or response.status_code >= 500:
                if attempt == self.retries:
                    break
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 2**attempt
                time.sleep(delay)
                continue
            if response.ok:
                return response.json()
            raise PowerBIAPIError(
                f"GET {response.url} failed with HTTP {response.status_code}: "
                f"{response.text[:500]}"
            )
        raise PowerBIAPIError(f"GET {url} failed after retries")

    def paged_values(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        url = path if path.startswith("http") else f"{API_BASE}/{path.lstrip('/')}"
        rows: list[dict[str, Any]] = []
        first = True
        while url:
            payload = self.get_json(url, params=params if first else None)
            rows.extend(payload.get("value", []))
            url = payload.get("@odata.nextLink") or payload.get("continuationUri")
            first = False
        return rows

    def activity_events(self, day: date, timezone_name: str) -> list[dict[str, Any]]:
        start, end = local_day_window_utc(day, timezone_name)
        params = {
            "startDateTime": f"'{iso_z(start)}'",
            "endDateTime": f"'{iso_z(end)}'",
        }
        url = f"{API_BASE}/admin/activityevents"
        events: list[dict[str, Any]] = []
        first = True
        while url:
            payload = self.get_json(url, params=params if first else None)
            events.extend(payload.get("activityEventEntities", []))
            url = payload.get("continuationUri")
            first = False
        return deduplicate(events, "Id")

    def inventory(self) -> dict[str, list[dict[str, Any]]]:
        return {
            "workspaces": self.paged_values("admin/groups?$top=5000"),
            "datasets": self.paged_values("admin/datasets?$top=5000"),
            "reports": self.paged_values("admin/reports?$top=5000"),
            "dashboards": self.paged_values("admin/dashboards?$top=5000"),
        }


def deduplicate(rows: Iterable[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        value = str(row.get(key) or row)
        if value not in seen:
            seen.add(value)
            result.append(row)
    return result
