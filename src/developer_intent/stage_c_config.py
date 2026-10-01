"""Central, secret-safe configuration for Protocol v5 Stage C."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .screening_config import _read_env


@dataclass(frozen=True)
class StageCModelConfig:
    api_key: str | None
    base_url: str | None
    model: str
    reasoning_mode: str
    reasoning_effort: str
    structured_outputs: bool = True
    tools_enabled: tuple[str, ...] = ()

    @property
    def structurally_valid(self) -> bool:
        return bool(self.model and self.reasoning_mode in {"standard", "pro"}
                    and self.reasoning_effort in {"none", "low", "medium", "high", "xhigh", "max"})

    @property
    def live_permitted(self) -> bool:
        return self.structurally_valid and bool(self.api_key)

    def safe_report(self) -> str:
        return "\n".join([
            "Provider: openai",
            "API family: responses",
            f"Configured model: {self.model or 'missing'}",
            f"Reasoning mode: {self.reasoning_mode or 'missing'}",
            f"Reasoning effort: {self.reasoning_effort or 'missing'}",
            "Structured Outputs: enabled",
            "Model tools: disabled",
            "Pass 1 prompt version: dir-stage-c-first-generation-v3",
            "Pass 2 prompt version: dir-stage-c-csv-extraction-v2",
            "Methodology version: dir-tfg-v2",
            "Extraction version: conversation-extraction-v4",
            f"OPENAI_API_KEY: {'present' if self.api_key else 'missing'}",
            f"Configuration structurally valid: {'yes' if self.structurally_valid else 'no'}",
            f"Credentials present: {'yes' if self.api_key else 'no'}",
            f"Live API invocation permitted: {'yes' if self.live_permitted else 'no'}",
        ])


def load_stage_c_config(root: Path, *, env_file: Path | None = None,
                        environ: dict[str, str] | None = None) -> StageCModelConfig:
    local = _read_env(env_file or root / ".env")
    env = dict(os.environ if environ is None else environ)
    values = {**local, **env}
    return StageCModelConfig(
        api_key=values.get("OPENAI_API_KEY") or None,
        base_url=values.get("OPENAI_API_BASE_URL") or None,
        model=values.get("DIR_STAGE_C_MODEL", "").strip(),
        reasoning_mode=values.get("DIR_STAGE_C_REASONING_MODE", "standard").strip(),
        reasoning_effort=values.get("DIR_STAGE_C_REASONING_EFFORT", "medium").strip(),
    )
