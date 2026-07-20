from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # demo local funciona sem dependências opcionais
    def load_dotenv() -> bool:
        return False


@dataclass(frozen=True)
class Settings:
    tenant_id: str | None
    client_id: str | None
    client_secret: str | None
    timezone: str
    output_dir: Path
    postgres_url: str | None
    postgres_schema: str

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        return cls(
            tenant_id=os.getenv("PBI_TENANT_ID"),
            client_id=os.getenv("PBI_CLIENT_ID"),
            client_secret=os.getenv("PBI_CLIENT_SECRET"),
            timezone=os.getenv("PBI_TIMEZONE", "America/Sao_Paulo"),
            output_dir=Path(os.getenv("PBI_OUTPUT_DIR", "output")),
            postgres_url=os.getenv("POSTGRES_URL"),
            postgres_schema=os.getenv("PBI_MONITOR_SCHEMA", "powerbi_monitor"),
        )

    def require_powerbi_credentials(self) -> None:
        missing = [
            name
            for name, value in {
                "PBI_TENANT_ID": self.tenant_id,
                "PBI_CLIENT_ID": self.client_id,
                "PBI_CLIENT_SECRET": self.client_secret,
            }.items()
            if not value
        ]
        if missing:
            raise ValueError(
                "Variáveis obrigatórias ausentes: " + ", ".join(missing)
            )
