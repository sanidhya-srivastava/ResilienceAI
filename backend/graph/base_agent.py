"""BaseAgent — abstract base class for all five recovery agents."""
from __future__ import annotations

import os
import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from pydantic import BaseModel

from backend.db.database import Database
from backend.db.models import AgentAction
from backend.db.repository import ActionRepository
from backend.graph.state import RecoveryState
from backend.simulator.utils import utcnow

if TYPE_CHECKING:
    pass


class BaseAgent(ABC):
    """All agents inherit from this class and implement run()."""

    name: str  # must be set on each subclass

    def __init__(self, db: Database) -> None:
        self.db = db

    # ── Public interface ───────────────────────────────────────────────────────

    @abstractmethod
    def run(self, state: RecoveryState) -> dict:
        """Execute this agent's step and return a partial RecoveryState dict.

        LangGraph merges the returned dict into the shared state automatically.
        """
        ...

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _call_llm(self, prompt: str, schema: type[BaseModel]) -> BaseModel:
        """Call the LLM and parse its output into *schema*, or return a mock."""
        if _is_mock_mode():
            from backend.graph.mock_responses import MOCK_LLM_RESPONSES  # noqa: PLC0415
            raw = MOCK_LLM_RESPONSES.get(self.name, {})
            return schema.model_validate(raw)

        import ollama  # noqa: PLC0415

        model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
        host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        client = ollama.Client(host=host)

        for attempt in range(2):
            try:
                response = client.chat(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    format=schema.model_json_schema(),
                    options={"temperature": 0},
                )
                return schema.model_validate_json(response["message"]["content"])
            except Exception:
                if attempt == 1:
                    # Fallback: return mock on parse failure
                    from backend.graph.mock_responses import MOCK_LLM_RESPONSES  # noqa: PLC0415
                    return schema.model_validate(MOCK_LLM_RESPONSES.get(self.name, {}))

        raise RuntimeError(f"LLM call failed for agent '{self.name}'")  # unreachable

    def _log_action(
        self,
        state: RecoveryState,
        output: dict,
        success: bool,
        duration_ms: int,
        action_type: str = "execute",
    ) -> None:
        """Persist an agent action record to SQLite."""
        try:
            with self.db.connect() as conn:
                ActionRepository.create(
                    conn,
                    AgentAction(
                        incident_id=state["incident_id"],
                        agent_name=self.name,
                        action_type=action_type,
                        output_summary=str(output)[:500],
                        success=success,
                        duration_ms=duration_ms,
                        timestamp=utcnow(),
                    ),
                )
        except Exception:
            # Never let DB errors crash the agent pipeline
            pass

    @staticmethod
    def _elapsed_ms(start: float) -> int:
        return int((time.time() - start) * 1000)


def _is_mock_mode() -> bool:
    return os.getenv("MOCK_MODE", "true").lower() == "true"
