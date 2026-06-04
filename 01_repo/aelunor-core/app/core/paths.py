import os

from app.repositories.campaign_repository import CampaignRepository
from app.runtime_config import bundled_path, resolve_runtime_config

RUNTIME_CONFIG = resolve_runtime_config()
BASE_DIR = str(bundled_path("app"))
STATIC_DIR = os.path.join(BASE_DIR, "static")
UI_V1_DIST_DIR = str(bundled_path("ui", "dist"))
UI_V1_ASSETS_DIR = os.path.join(UI_V1_DIST_DIR, "assets")
DATA_DIR = str(RUNTIME_CONFIG.data_dir)
LEGACY_STATE_PATH = os.path.join(DATA_DIR, "state.json")
CAMPAIGNS_DIR = os.path.join(DATA_DIR, "campaigns")


def ensure_storage_dirs(*, data_dir: str, campaigns_dir: str) -> None:
    CampaignRepository(data_dir=data_dir, campaigns_dir=campaigns_dir).ensure_storage()


def ensure_data_dirs() -> None:
    ensure_storage_dirs(data_dir=DATA_DIR, campaigns_dir=CAMPAIGNS_DIR)
