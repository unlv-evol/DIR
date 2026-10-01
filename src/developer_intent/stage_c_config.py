"""Central, secret-safe configuration for Protocol v5 Stage C."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .screening_config import _read_env


@dataclass(frozen=True)
class StageCVersionContract:
    input_version: str
    package_version: str
    input_filename: str
    pass_1_prompt_version: str
    extraction_version: str
    output_version: str
    candidate_prefix: str


STAGE_C_VERSION_CONTRACTS = {
    "v1": StageCVersionContract(
        "v1", "conversation-only-v1", "stage_c_model_view.json",
        "dir-stage-c-first-generation-v3", "conversation-extraction-v4", "v4",
        "ARTIFACT_"),
    "v2": StageCVersionContract(
        "v2", "conversation-only-v2", "stage_c_model_view_v2.json",
        "dir-stage-c-first-generation-v4", "conversation-extraction-v5", "v5",
        "GTC_"),
}


def stage_c_version_contract(input_version: str) -> StageCVersionContract:
    try:
        return STAGE_C_VERSION_CONTRACTS[input_version]
    except KeyError as exc:
        raise ValueError(f"Unsupported Stage C input version: {input_version}") from exc


@dataclass(frozen=True)
class StageCModelConfig:
    api_key: str | None
    base_url: str | None
    model: str
    reasoning_mode: str
    reasoning_effort: str
    max_retries: int = 2
    structured_outputs: bool = True
    tools_enabled: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if (isinstance(self.max_retries, bool) or not isinstance(self.max_retries, int)
                or not 0 <= self.max_retries <= 5):
            raise ValueError("DIR_STAGE_C_MAX_RETRIES must be an integer from 0 through 5")

    @property
    def structurally_valid(self) -> bool:
        return bool(self.model and self.reasoning_mode in {"standard", "pro"}
                    and self.reasoning_effort in {"none", "low", "medium", "high", "xhigh", "max"})

    @property
    def live_permitted(self) -> bool:
        return self.structurally_valid and bool(self.api_key)

    def safe_report(self, input_version: str = "v1") -> str:
        contract = stage_c_version_contract(input_version)
        return "\n".join([
            "Provider: openai",
            "API family: responses",
            f"Input version: {contract.input_version}",
            f"Input package: {contract.package_version}",
            f"Input file: {contract.input_filename}",
            f"Configured model: {self.model or 'missing'}",
            f"Reasoning mode: {self.reasoning_mode or 'missing'}",
            f"Reasoning effort: {self.reasoning_effort or 'missing'}",
            f"OpenAI SDK max retries: {self.max_retries}",
            "Structured Outputs: enabled",
            "Model tools: disabled",
            f"Pass 1 prompt version: {contract.pass_1_prompt_version}",
            "Pass 2 prompt version: dir-stage-c-csv-extraction-v2",
            "Methodology version: dir-tfg-v2",
            f"Extraction version: {contract.extraction_version}",
            f"Output contract: {contract.output_version}",
            f"Candidate namespace: {contract.candidate_prefix}*",
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
    raw_max_retries = values.get("DIR_STAGE_C_MAX_RETRIES", "2").strip()
    try:
        max_retries = int(raw_max_retries)
    except ValueError as exc:
        raise ValueError("DIR_STAGE_C_MAX_RETRIES must be an integer from 0 through 5") from exc
    return StageCModelConfig(
        api_key=values.get("OPENAI_API_KEY") or None,
        base_url=values.get("OPENAI_API_BASE_URL") or None,
        model=values.get("DIR_STAGE_C_MODEL", "").strip(),
        reasoning_mode=values.get("DIR_STAGE_C_REASONING_MODE", "standard").strip(),
        reasoning_effort=values.get("DIR_STAGE_C_REASONING_EFFORT", "medium").strip(),
        max_retries=max_retries,
    )
