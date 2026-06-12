from typing import Any, Dict, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.services.llm import active_model, model_catalog


class LlmTestIn(BaseModel):
    ollamaBaseUrl: Optional[str] = None
    model: Optional[str] = None


class LlmModelIn(BaseModel):
    model: Optional[str] = None


def build_llm_router() -> APIRouter:
    router = APIRouter()

    @router.get("/api/llm/models")
    def list_models(ollama_base_url: Optional[str] = Query(default=None, alias="ollamaBaseUrl")) -> Dict[str, Any]:
        return model_catalog.list_ollama_models(base_url=ollama_base_url)

    @router.post("/api/llm/test")
    def test_model(inp: LlmTestIn) -> Dict[str, Any]:
        return model_catalog.test_ollama_model(base_url=inp.ollamaBaseUrl, model=inp.model)

    @router.get("/api/llm/model")
    def get_model() -> Dict[str, Any]:
        return active_model.get_active_model()

    @router.put("/api/llm/model")
    def set_model(inp: LlmModelIn) -> Dict[str, Any]:
        return active_model.set_active_model(inp.model or "")

    return router
