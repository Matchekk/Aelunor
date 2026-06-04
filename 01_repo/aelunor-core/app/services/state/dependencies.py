from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Mapping


@dataclass(frozen=True)
class StateEngineDependencies:
    campaign_repository: Any = None
    ollama_adapter: Any = None
    live_state_service: Any = None
    logger: Any = None

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any]) -> "StateEngineDependencies":
        return cls(
            campaign_repository=mapping.get("CAMPAIGN_REPOSITORY"),
            ollama_adapter=mapping.get("OLLAMA_ADAPTER"),
            live_state_service=mapping.get("live_state_service"),
            logger=mapping.get("LOGGER"),
        )

    def merged(self, other: "StateEngineDependencies") -> "StateEngineDependencies":
        return replace(
            self,
            campaign_repository=other.campaign_repository or self.campaign_repository,
            ollama_adapter=other.ollama_adapter or self.ollama_adapter,
            live_state_service=other.live_state_service or self.live_state_service,
            logger=other.logger or self.logger,
        )
