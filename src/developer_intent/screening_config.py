"""Small configuration loader for the screening CLI; no extra dependency."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _read_env(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


@dataclass(frozen=True)
class Config:
    github_token: str | None
    timeout: float
    retries: int
    cache_dir: Path
    output: Path

    def safe_report(self) -> str:
        return (f"GitHub token: {'configured' if self.github_token else 'not configured'}\n"
                f"GitHub API base URL: https://api.github.com\n"
                f"HTTP timeout: {self.timeout:g}s\nHTTP retries: {self.retries}\n"
                f"Screening cache: {self.cache_dir}\nScreening output: {self.output}")


def load_config(root: Path, *, cache_dir: Path | None = None,
                output: Path | None = None, timeout: float | None = None,
                retries: int | None = None, env_file: Path | None = None,
                environ: dict[str, str] | None = None) -> Config:
    local = _read_env(env_file or root / ".env")
    env = dict(os.environ if environ is None else environ)
    values = {**local, **env}
    seconds = float(timeout if timeout is not None else values.get("DIR_HTTP_TIMEOUT", "30"))
    attempts = int(retries if retries is not None else values.get("DIR_HTTP_RETRIES", "3"))
    if seconds <= 0 or attempts < 0:
        raise ValueError("HTTP timeout must be positive and retries nonnegative")
    return Config(
        github_token=values.get("GITHUB_TOKEN") or None,
        timeout=seconds,
        retries=attempts,
        cache_dir=cache_dir or root / values.get("DIR_SCREENING_CACHE_DIR", "data/intermediate/screening/cache"),
        output=output or root / values.get("DIR_SCREENING_OUTPUT", "cases/manifests/screened_cases.csv"),
    )
