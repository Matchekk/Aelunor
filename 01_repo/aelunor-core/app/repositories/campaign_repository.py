import json
import os
import re
import tempfile
from typing import Any, Dict, List


JsonDict = Dict[str, Any]

# Campaign ids are server-generated (make_id) and only ever contain these chars.
# Validating here keeps an attacker-controlled path param from escaping the
# campaigns directory via traversal (e.g. "../../etc/passwd").
_SAFE_CAMPAIGN_ID = re.compile(r"^[A-Za-z0-9_-]+$")


class CampaignRepository:
    """JSON-backed campaign repository.

    Campaign JSON remains the persistent source of truth. Writes are staged in
    the campaign directory and then atomically replaced to avoid partial files.
    """

    def __init__(self, *, data_dir: str, campaigns_dir: str) -> None:
        self.data_dir = data_dir
        self.campaigns_dir = campaigns_dir

    def ensure_storage(self) -> None:
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.campaigns_dir, exist_ok=True)

    def campaign_path(self, campaign_id: str) -> str:
        if not isinstance(campaign_id, str) or not _SAFE_CAMPAIGN_ID.match(campaign_id):
            raise ValueError(f"Invalid campaign_id: {campaign_id!r}")
        return os.path.join(self.campaigns_dir, f"{campaign_id}.json")

    def list_campaign_ids(self) -> List[str]:
        self.ensure_storage()
        ids: List[str] = []
        for name in os.listdir(self.campaigns_dir):
            # Skip in-flight save staging files (".campaign-*.json") and any other
            # hidden files so a concurrent save cannot surface a phantom id.
            if name.endswith(".json") and not name.startswith("."):
                ids.append(name[:-5])
        return sorted(ids)

    def load_json(self, path: str) -> JsonDict:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_json(self, path: str, payload: JsonDict) -> None:
        self.ensure_storage()
        directory = os.path.dirname(path)
        fd, tmp_path = tempfile.mkstemp(prefix=".campaign-", suffix=".json", dir=directory)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
                f.write("\n")
            os.replace(tmp_path, path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except FileNotFoundError:
                pass
            raise
