from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


APP_NAME = "Aelunor"
APP_VERSION = "0.1.0"
APP_ENV_VAR = "AELUNOR_APP_MODE"
APP_MODE_DESKTOP = "desktop"


@dataclass(frozen=True)
class RuntimeConfig:
    app_name: str
    version: str
    mode: str
    is_desktop: bool
    user_data_dir: Path
    data_dir: Path
    logs_dir: Path
    resource_root: Path


def _default_user_data_dir() -> Path:
    appdata = os.getenv("APPDATA")
    if appdata:
        return Path(appdata) / APP_NAME
    return Path.home() / f".{APP_NAME.lower()}"


def _resource_root() -> Path:
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        return Path(bundle_root)
    return Path(__file__).resolve().parents[1]


def resolve_runtime_config() -> RuntimeConfig:
    mode = os.getenv(APP_ENV_VAR, "dev").strip().lower() or "dev"
    user_data_dir = Path(os.getenv("AELUNOR_USER_DATA_DIR", str(_default_user_data_dir()))).expanduser()
    data_dir = Path(os.getenv("DATA_DIR", str(user_data_dir / "data"))).expanduser()
    logs_dir = Path(os.getenv("AELUNOR_LOG_DIR", str(user_data_dir / "logs"))).expanduser()
    return RuntimeConfig(
        app_name=APP_NAME,
        version=os.getenv("AELUNOR_VERSION", APP_VERSION),
        mode=mode,
        is_desktop=mode == APP_MODE_DESKTOP,
        user_data_dir=user_data_dir,
        data_dir=data_dir,
        logs_dir=logs_dir,
        resource_root=_resource_root(),
    )


def bundled_path(*parts: str) -> Path:
    return resolve_runtime_config().resource_root.joinpath(*parts)

