import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

SLOT_PREFIX = "slot_"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def deep_copy(value: Any) -> Any:
    return json.loads(json.dumps(value))


def hash_secret(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def make_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"
