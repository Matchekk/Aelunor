"""Cloud LLM adapter backed by the Anthropic Claude API.

This is the optional cloud fallback for the local-first Ollama setup. It exposes
the same duck-typed interface the rest of the app already uses for the Ollama
adapter (``chat`` / ``request_seed`` / ``status_payload``) so it can be dropped
in wherever an ``OllamaAdapter`` is expected.

The Anthropic API key is read automatically from the machine environment by the
official SDK (``ANTHROPIC_API_KEY`` / ``ANTHROPIC_AUTH_TOKEN``) — nothing is
hardcoded here. ``anthropic`` is imported lazily so the module (and the whole
app) imports cleanly even when the package or a key is absent; the import only
happens when a Claude call is actually made.
"""
import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class AnthropicSettings:
    model: str
    max_tokens: int
    timeout_sec: int


def anthropic_key_present() -> bool:
    """True when a usable Anthropic credential is available in the environment."""
    return bool(
        (os.getenv("ANTHROPIC_API_KEY") or "").strip()
        or (os.getenv("ANTHROPIC_AUTH_TOKEN") or "").strip()
    )


class AnthropicAdapter:
    """Calls Claude via the official Anthropic SDK, mirroring OllamaAdapter."""

    def __init__(self, settings: AnthropicSettings) -> None:
        self.settings = settings
        self._client = None

    def _get_client(self) -> Any:
        if self._client is None:
            import anthropic  # lazy: keeps the package optional until first use

            # No api_key passed: the SDK resolves ANTHROPIC_API_KEY /
            # ANTHROPIC_AUTH_TOKEN from the environment automatically.
            self._client = anthropic.Anthropic()
        return self._client

    def request_seed(self) -> Optional[int]:
        # The Anthropic API has no deterministic seed parameter.
        return None

    def status_payload(self) -> Dict[str, Any]:
        return {
            "provider": "anthropic",
            "configured_model": self.settings.model,
            "request_timeout_sec": self.settings.timeout_sec,
            "max_tokens": self.settings.max_tokens,
            "api_key_present": anthropic_key_present(),
            "anthropic_ok": anthropic_key_present(),
        }

    @staticmethod
    def _extract_text(response: Any) -> str:
        parts: List[str] = []
        for block in getattr(response, "content", []) or []:
            if getattr(block, "type", None) == "text":
                parts.append(getattr(block, "text", "") or "")
        return "".join(parts).strip()

    def chat(
        self,
        system: str,
        user: str,
        *,
        format_schema: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        temperature: Optional[float] = None,  # accepted for interface parity, ignored
        repeat_penalty: Optional[float] = None,  # ignored — no Claude equivalent
        num_ctx: Optional[int] = None,  # ignored — Claude manages context itself
    ) -> str:
        request_timeout = max(30, int(timeout or self.settings.timeout_sec))
        client = self._get_client().with_options(timeout=float(request_timeout))
        base_kwargs: Dict[str, Any] = {
            "model": self.settings.model,
            "max_tokens": self.settings.max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }

        if format_schema is not None:
            try:
                response = client.messages.create(
                    **base_kwargs,
                    output_config={"format": {"type": "json_schema", "schema": format_schema}},
                )
                return self._extract_text(response)
            except Exception:
                # Schema not accepted (e.g. missing additionalProperties:false, or
                # unsupported constraints). Fall back to a plain JSON instruction so
                # the local-LLM JSON contract still holds.
                json_user = (
                    user
                    + "\n\nAntworte ausschließlich mit einem einzelnen gültigen JSON-Objekt "
                    + "gemäß diesem Schema. Keine Markdown-Fences, keine Erklärung.\n\nSCHEMA:\n"
                    + json.dumps(format_schema, ensure_ascii=False)
                )
                response = client.messages.create(
                    model=self.settings.model,
                    max_tokens=self.settings.max_tokens,
                    system=system,
                    messages=[{"role": "user", "content": json_user}],
                )
                return self._extract_text(response)

        response = client.messages.create(**base_kwargs)
        return self._extract_text(response)


class FallbackLLMAdapter:
    """Tries a primary adapter (local Ollama) and falls back to a cloud adapter.

    Matches the local-first intent: the local LLM stays the primary path, and the
    Anthropic cloud adapter only handles requests when the local backend is
    unreachable (e.g. no Ollama running on this machine).
    """

    def __init__(
        self,
        primary: Any,
        fallback: Any,
        *,
        primary_name: str = "ollama",
        fallback_name: str = "anthropic",
        logger: Any = None,
    ) -> None:
        self.primary = primary
        self.fallback = fallback
        self.primary_name = primary_name
        self.fallback_name = fallback_name
        self._logger = logger

    def request_seed(self) -> Optional[int]:
        return self.primary.request_seed()

    def status_payload(self) -> Dict[str, Any]:
        def _safe(adapter: Any) -> Dict[str, Any]:
            try:
                return adapter.status_payload()
            except Exception as exc:  # pragma: no cover - defensive
                return {"error": str(exc)}

        return {
            "provider": "auto",
            "primary": {"name": self.primary_name, **_safe(self.primary)},
            "fallback": {"name": self.fallback_name, **_safe(self.fallback)},
        }

    def chat(self, system: str, user: str, **kwargs: Any) -> str:
        try:
            return self.primary.chat(system, user, **kwargs)
        except Exception as exc:
            if self._logger is not None:
                try:
                    self._logger.warning(
                        "llm_primary_unavailable",
                        extra={"primary": self.primary_name, "fallback": self.fallback_name, "error": str(exc)[:240]},
                    )
                except Exception:  # pragma: no cover - logging must never break the turn
                    pass
            return self.fallback.chat(system, user, **kwargs)
