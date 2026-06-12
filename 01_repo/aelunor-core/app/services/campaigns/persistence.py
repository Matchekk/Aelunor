import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from fastapi import HTTPException

from app.config.errors import (
    ERROR_CODE_NORMALIZE,
    ERROR_CODE_PERSISTENCE,
    ERROR_CODE_SSE_BROADCAST,
)
from app.core.turn_profiling import profiling_enabled
from app.repositories.campaign_repository import CampaignRepository

profiling_logger = logging.getLogger("aelunor.turn_profile")


CampaignState = Dict[str, Any]


def resolve_campaign_repository(
    *,
    configured: Any,
    data_dir: str,
    campaigns_dir: str,
) -> CampaignRepository:
    if (
        isinstance(configured, CampaignRepository)
        and configured.data_dir == data_dir
        and configured.campaigns_dir == campaigns_dir
    ):
        return configured
    return CampaignRepository(data_dir=data_dir, campaigns_dir=campaigns_dir)


def save_json(repository: CampaignRepository, path: str, payload: CampaignState) -> None:
    repository.save_json(path, payload)


def load_json(repository: CampaignRepository, path: str) -> CampaignState:
    return repository.load_json(path)


def campaign_path(repository: CampaignRepository, campaign_id: str) -> str:
    return repository.campaign_path(campaign_id)


def list_campaign_ids(repository: CampaignRepository) -> List[str]:
    return repository.list_campaign_ids()


@dataclass(frozen=True)
class CampaignLoadPorts:
    repository: CampaignRepository
    normalize_campaign: Callable[[CampaignState], CampaignState]


def load_campaign(campaign_id: str, *, ports: CampaignLoadPorts) -> CampaignState:
    path = campaign_path(ports.repository, campaign_id)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Kampagne nicht gefunden.")
    return ports.normalize_campaign(load_json(ports.repository, path))


@dataclass(frozen=True)
class CampaignSavePorts:
    repository: CampaignRepository
    normalize_campaign: Callable[[CampaignState], CampaignState]
    utc_now: Callable[[], str]
    emit_turn_phase_event: Callable[..., None]
    turn_flow_error: Callable[..., Exception]
    live_state_service: Any
    logger: Any = None


def save_campaign(
    campaign: CampaignState,
    *,
    reason: str = "campaign_updated",
    trace_ctx: Optional[Dict[str, Any]] = None,
    ports: CampaignSavePorts,
) -> None:
    try:
        ports.emit_turn_phase_event(trace_ctx, phase="normalize", success=True, extra={"reason": reason})
        campaign = ports.normalize_campaign(campaign)
        ports.emit_turn_phase_event(trace_ctx, phase="normalize", success=True, extra={"reason": reason, "result": "ok"})
    except Exception as exc:
        ports.emit_turn_phase_event(
            trace_ctx,
            phase="normalize",
            success=False,
            error_code=ERROR_CODE_NORMALIZE,
            error_class=exc.__class__.__name__,
            message=str(exc)[:240],
            extra={"reason": reason},
        )
        if trace_ctx is not None:
            raise ports.turn_flow_error(
                error_code=ERROR_CODE_NORMALIZE,
                phase="normalize",
                trace_ctx=trace_ctx,
                exc=exc,
            )
        raise

    campaign["campaign_meta"]["updated_at"] = ports.utc_now()
    campaign_id = campaign["campaign_meta"]["campaign_id"]

    try:
        ports.emit_turn_phase_event(trace_ctx, phase="persist_save", success=True, extra={"reason": reason})
        if profiling_enabled():
            save_started = time.perf_counter()
            save_json(ports.repository, campaign_path(ports.repository, campaign_id), campaign)
            profiling_logger.info(
                json.dumps(
                    {
                        "kind": "save_profile",
                        "campaign_id": campaign_id,
                        "reason": reason,
                        "s": round(time.perf_counter() - save_started, 3),
                    },
                    ensure_ascii=False,
                )
            )
        else:
            save_json(ports.repository, campaign_path(ports.repository, campaign_id), campaign)
        ports.emit_turn_phase_event(trace_ctx, phase="persist_save", success=True, extra={"reason": reason, "result": "ok"})
    except Exception as exc:
        ports.emit_turn_phase_event(
            trace_ctx,
            phase="persist_save",
            success=False,
            error_code=ERROR_CODE_PERSISTENCE,
            error_class=exc.__class__.__name__,
            message=str(exc)[:240],
            extra={"reason": reason},
        )
        if trace_ctx is not None:
            raise ports.turn_flow_error(
                error_code=ERROR_CODE_PERSISTENCE,
                phase="persist_save",
                trace_ctx=trace_ctx,
                exc=exc,
            )
        raise

    try:
        ports.emit_turn_phase_event(trace_ctx, phase="sse_broadcast", success=True, extra={"reason": reason})
        ports.live_state_service.broadcast_campaign_sync(campaign_id, reason=reason)
        ports.emit_turn_phase_event(trace_ctx, phase="sse_broadcast", success=True, extra={"reason": reason, "result": "ok"})
    except Exception as exc:
        ports.emit_turn_phase_event(
            trace_ctx,
            phase="sse_broadcast",
            success=False,
            error_code=ERROR_CODE_SSE_BROADCAST,
            error_class=exc.__class__.__name__,
            message=str(exc)[:240],
            extra={"reason": reason},
        )
        if ports.logger is not None:
            ports.logger.warning(
                "campaign_saved_but_sse_broadcast_failed",
                extra={
                    "campaign_id": campaign_id,
                    "reason": reason,
                    "error_class": exc.__class__.__name__,
                    "error": str(exc)[:240],
                },
            )
