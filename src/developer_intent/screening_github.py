"""GitHub PR screening facts from the official API."""

from __future__ import annotations

import json
import re
from urllib.parse import urlparse

from .screening_http import HttpClient

PR_PATH = re.compile(r"^/([^/]+)/([^/]+)/pull/(\d+)/?$")
REDIRECT_PATH = re.compile(r"^/repositories/(\d+)/pulls/(\d+)/?$")


def pr_identity(url: str) -> tuple[str, str, int] | None:
    parsed = urlparse(url)
    match = PR_PATH.fullmatch(parsed.path)
    if parsed.scheme != "https" or parsed.netloc.lower() != "github.com" or not match:
        return None
    return match[1], match[2], int(match[3])


def _json_response(body: bytes) -> object:
    try:
        return json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Malformed JSON response") from exc


def _verified_repository_redirect(final_url: str, raw: dict, number: int) -> int | None:
    """Return the stable repository ID only for a matching GitHub API redirect."""
    parsed = urlparse(final_url)
    match = REDIRECT_PATH.fullmatch(parsed.path)
    base = raw.get("base")
    repository = base.get("repo") if isinstance(base, dict) else None
    canonical = pr_identity(raw.get("html_url", ""))
    if (parsed.scheme != "https" or parsed.netloc.lower() != "api.github.com"
            or not match or not isinstance(repository, dict) or canonical is None
            or int(match[2]) != number or canonical[2] != number
            or repository.get("id") != int(match[1])
            or str(repository.get("full_name", "")).casefold()
            != f"{canonical[0]}/{canonical[1]}".casefold()):
        return None
    return int(match[1])


def retrieve_pr(url: str, http: HttpClient, *, token: str | None = None,
                refresh: bool = False) -> dict:
    identity = pr_identity(url)
    result = {"url": url, "retrieval_status": "not_attempted", "notes": "",
              "pr": None, "files": None}
    if identity is None:
        result.update(retrieval_status="malformed_url", notes="Invalid GitHub PR URL")
        return result
    owner, repo, number = identity
    base = f"https://api.github.com/repos/{owner}/{repo}/pulls/{number}"
    response = http.get(base, token=token, refresh=refresh)
    if response.body is None:
        result.update(retrieval_status=response.status, notes=response.note)
        return result
    try:
        raw = _json_response(response.body)
        if not isinstance(raw, dict) or not isinstance(raw.get("number"), int):
            raise ValueError("Missing PR identity in API response")
        canonical = pr_identity(raw.get("html_url", ""))
        if canonical is None or raw["number"] != number or canonical[2] != number:
            raise ValueError("PR identity mismatch in API response")
        redirected = canonical != identity
        repository_id = _verified_repository_redirect(response.final_url, raw, number) if redirected else None
        if redirected and repository_id is None:
            raise ValueError("Unverified PR repository redirect")
        if any(not isinstance(raw.get(field), int) or raw[field] < 0 for field in
               ("additions", "deletions", "changed_files", "commits")):
            raise ValueError("Missing or invalid PR screening measurements")
        if any(not isinstance(raw.get(field), dict) for field in
               ("user", "base", "head")):
            raise ValueError("Malformed PR identity metadata")
        pr = {
            "html_url": raw["html_url"], "number": raw["number"],
            "source_url": url, "canonical_url": raw["html_url"],
            "redirect_verified": redirected, "repository_id": repository_id,
            "api_final_url": response.final_url,
            "state": raw.get("state"), "created_at": raw.get("created_at"),
            "closed_at": raw.get("closed_at"), "merged_at": raw.get("merged_at"),
            "additions": raw.get("additions"), "deletions": raw.get("deletions"),
            "changed_files": raw.get("changed_files"), "commits": raw.get("commits"),
            "author": raw["user"].get("login"),
            "base_branch": raw["base"].get("ref"),
            "head_branch": raw["head"].get("ref"),
            "base_sha": raw["base"].get("sha"),
            "head_sha": raw["head"].get("sha"),
        }
    except ValueError as exc:
        result.update(retrieval_status="malformed_response", notes=str(exc))
        return result
    files = []
    page = 1
    while True:
        response_files = http.get(f"{base}/files?per_page=100&page={page}",
                                  token=token, refresh=refresh)
        if response_files.body is None:
            result.update(retrieval_status=response_files.status,
                          notes=f"PR metadata retrieved; file list: {response_files.note}")
            result["pr"] = pr
            return result
        try:
            chunk = _json_response(response_files.body)
            if not isinstance(chunk, list) or any(not isinstance(f, dict) for f in chunk):
                raise ValueError("Malformed PR file list")
            files.extend({"filename": f.get("filename"), "additions": f.get("additions"),
                          "deletions": f.get("deletions")} for f in chunk)
        except ValueError as exc:
            result.update(retrieval_status="malformed_response", notes=str(exc), pr=pr)
            return result
        if len(chunk) < 100:
            break
        page += 1
    if pr["changed_files"] != len({f["filename"] for f in files}):
        result.update(retrieval_status="malformed_response",
                      notes="PR file list count disagrees with PR metadata", pr=pr)
        return result
    result.update(retrieval_status=response.status, pr=pr, files=files)
    return result
