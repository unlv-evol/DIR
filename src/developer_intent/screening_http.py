"""HTTP retrieval with explicit failure statuses and success-only caching."""

from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class FetchResult:
    status: str
    body: bytes | None = None
    final_url: str = ""
    http_status: int | None = None
    note: str = ""
    from_cache: bool = False
    retrieved_at: str = ""
    content_type: str = ""


class HttpClient:
    def __init__(self, cache_dir: Path, timeout: float = 30, retries: int = 3,
                 sleep: Callable[[float], None] = time.sleep,
                 opener: Callable | None = None):
        self.cache_dir = cache_dir
        self.timeout = timeout
        self.retries = retries
        self.sleep = sleep
        self.opener = opener or urllib.request.urlopen

    def get(self, url: str, *, token: str | None = None, refresh: bool = False,
            accept: str = "application/json") -> FetchResult:
        # Cache authorization modes separately without including the secret.
        key = hashlib.sha256(f"{url}|{'auth' if token else 'public'}".encode("utf-8")).hexdigest()
        body_path = self.cache_dir / f"{key}.body"
        meta_path = self.cache_dir / f"{key}.json"
        if not refresh and body_path.exists() and meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            return FetchResult(meta["status"], body_path.read_bytes(), meta["final_url"],
                               meta["http_status"], from_cache=True,
                               retrieved_at=meta.get("retrieved_at", ""),
                               content_type=meta.get("content_type", ""))
        headers = {"Accept": accept, "User-Agent": "DIR-pilot-screening/1"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        request = urllib.request.Request(url, headers=headers)
        for attempt in range(self.retries + 1):
            try:
                with self.opener(request, timeout=self.timeout) as response:
                    body = response.read()
                    status = "retrieved_authenticated" if token else "retrieved_public"
                    final_url = response.geturl()
                    code = response.status
                    response_headers = getattr(response, "headers", None)
                    content_type = (response_headers.get("Content-Type", "")
                                    if response_headers is not None else "")
                    if not 200 <= code < 300:
                        return FetchResult("http_failure", final_url=final_url,
                                           http_status=code, note=f"HTTP {code}")
                    self.cache_dir.mkdir(parents=True, exist_ok=True)
                    retrieved_at = datetime.now(timezone.utc).isoformat()
                    body_path.write_bytes(body)
                    meta_path.write_text(json.dumps({"status": status, "final_url": final_url,
                                                     "http_status": code,
                                                     "retrieved_at": retrieved_at,
                                                     "content_type": content_type}), encoding="utf-8")
                    return FetchResult(status, body, final_url, code,
                                       retrieved_at=retrieved_at, content_type=content_type)
            except urllib.error.HTTPError as exc:
                code = exc.code
                remaining = exc.headers.get("X-RateLimit-Remaining") if exc.headers else None
                if code == 429 or (code == 403 and remaining == "0"):
                    status = "rate_limited"
                elif code == 401:
                    status = "authentication_required"
                elif code == 403:
                    status = "forbidden"
                elif code == 404:
                    status = "not_found"
                elif code in {500, 502, 503, 504}:
                    status = "server_error"
                else:
                    status = "http_failure"
                if status in {"rate_limited", "server_error"} and attempt < self.retries:
                    self.sleep(min(2 ** attempt, 8))
                    continue
                return FetchResult(status, final_url=url, http_status=code,
                                   note=f"HTTP {code}")
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                if attempt < self.retries:
                    self.sleep(min(2 ** attempt, 8))
                    continue
                return FetchResult("network_failure", final_url=url,
                                   note=type(exc).__name__)
        raise AssertionError("unreachable")
