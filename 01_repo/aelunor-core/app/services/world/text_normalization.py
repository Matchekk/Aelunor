from __future__ import annotations

import re


def normalized_eval_text(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-zA-ZäöüÄÖÜß0-9 ]+", " ", str(text or "").lower())).strip()
