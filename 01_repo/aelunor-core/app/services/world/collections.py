from __future__ import annotations

from typing import Any, Dict


def stable_sorted_mapping(values: Dict[str, Any], *, key_fn=None) -> Dict[str, Any]:
    if not isinstance(values, dict):
        return {}
    if key_fn is None:
        key_fn = lambda item: str(item[0])
    items = sorted(values.items(), key=key_fn)
    return {key: value for key, value in items}
