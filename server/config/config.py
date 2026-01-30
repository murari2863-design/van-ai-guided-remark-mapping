from __future__ import annotations

import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

from server.utils.logger import log_msg

env_default = Path(__file__).parent / ".." / ".env"
if not os.path.exists(env_default):
    log_msg(f"Warning: env file at {env_default} doesn't exist!")
else:
    load_dotenv(env_default, encoding="utf-8")


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.getenv(name)
    return v if v not in (None, "") else default


def _env_guaranteed(name: str, default: str) -> str:
    v = os.getenv(name)
    return v if v not in (None, "") else default


def _env_safe(name: str) -> str:
    v = os.getenv(name)
    if v in (None, ""):
        raise RuntimeError(f"Environment variable {name} is required but not set.")
    return v


@dataclass
class Settings:
    environment: str
    port: int


def load_settings() -> Settings:
    return Settings(
        environment=_env_guaranteed("ENVIRONMENT", "production"),
        port=int(_env_guaranteed("PORT", "8000")),
    )
