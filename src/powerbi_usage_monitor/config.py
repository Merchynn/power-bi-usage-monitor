from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    tenant_id: str
    client_id: str
    client_secret: str
    postgres_url: str | None
    postgres_schema: str = "powerbi_monitor"
    timezone: str = "America/Sao_Paulo"
    output_dir: Path = Path("output")

    @classmethod
    def from_env(cls, require_powerbi: bool = True) -> "Settings":
        load_dotenv()
        values = {
            "tenant_id": os.getenv("PBI_TENANT_ID", ""),
            "client_id": os.getenv("PBI_CLIENT_ID", ""),
            "client_secret": os.getenv("PBI_CLIENT_SECRET", ""),
        }
        if require_powerbi:
            missing = [name for name, value in values.items() if not value]
            if missing:
                raise RuntimeError(
                    "Power BI environment variables missing: " + ", ".join(missing)
                )
        return cls(
            **values,
            postgres_url=os.getenv("POSTGRES_URL") or None,
            postgres_schema=os.getenv("PBI_MONITOR_SCHEMA", "powerbi_monitor"),
            timezone=os.getenv("PBI_TIMEZONE", "America/Sao_Paulo"),
            output_dir=Path(os.getenv("PBI_OUTPUT_DIR", "output")),
        )
