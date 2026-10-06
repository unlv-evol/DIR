"""Provider acquisition and exact Git materialization for Post-C v4."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.parse import quote

from .screening_config import _read_env

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary=path.with_suffix(path.suffix+".tmp")
    temporary.write_text(json.dumps(value,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    temporary.replace(path)

def load_live_config(root: Path, *, environ: dict[str,str] | None=None) -> dict:
    values={**_read_env(root/".env"),**dict(os.environ if environ is None else environ)}
    timeout=float(values.get("DIR_POST_C_TIMEOUT","30")); retries=int(values.get("DIR_POST_C_TRANSPORT_RETRIES","2"))
    if timeout<=0 or retries<0 or retries>2: raise ValueError("Post-C timeout must be positive and retries 0..2")
    return {"github_token":values.get("GITHUB_TOKEN") or None,"timeout":timeout,"transport_retries":retries}

def provider_get(url: str, token: str | None, timeout: float) -> dict:
    headers={"Accept":"application/vnd.github+json","User-Agent":"DIR-post-stage-c/4"}
    if token: headers["Authorization"]=f"Bearer {token}"
    request=urllib.request.Request(url,headers=headers)
    try:
        with urllib.request.urlopen(request,timeout=timeout) as response:
            return {"status":"success","http_status":response.status,"body":response.read(),"retrieved_at":utc_now(),"final_url":response.geturl()}
    except urllib.error.HTTPError as exc:
        remaining=exc.headers.get("X-RateLimit-Remaining") if exc.headers else None
        status=("rate_limited" if exc.code==429 or (exc.code==403 and remaining=="0") else "authentication_blocked" if exc.code==401 else "repository_unavailable" if exc.code==404 else "server_error" if exc.code in {500,502,503,504} else "transport_failed")
        return {"status":status,"http_status":exc.code,"body":b"","retrieved_at":utc_now(),"final_url":url}
    except TimeoutError:
        return {"status":"timed_out","http_status":0,"body":b"","retrieved_at":utc_now(),"final_url":url}
    except (urllib.error.URLError,OSError):
        return {"status":"transport_failed","http_status":0,"body":b"","retrieved_at":utc_now(),"final_url":url}



def output_paths(case_id: str) -> dict[str, Path]:
    return {"acquisition": Path(f"cases/reconstruction/{case_id}/historical_state_acquisition_v4.json"),
            "boundary": Path(f"data/derived/historical_information/{case_id}/historical_information_boundary_v4.json")}


def _get_json(url: str, config: dict, get: Callable = provider_get) -> tuple[object | None, dict]:
    attempts = []
    for number in range(1, config["transport_retries"] + 2):
        result = get(url, config.get("github_token"), config["timeout"])
        attempts.append({"attempt": number, "url": url, "status": result["status"],
                         "http_status": result["http_status"], "retrieved_at": result["retrieved_at"]})
        if result["status"] == "success":
            return json.loads(result["body"]), {"source": url, "retrieved_at": result["retrieved_at"],
                                                "sha256": hashlib.sha256(result["body"]).hexdigest(), "attempts": attempts}
        if result["status"] not in {"rate_limited", "transport_failed", "timed_out", "server_error"}:
            break
        time.sleep(min(2 ** (number - 1), 4))
    return None, {"source": url, "retrieved_at": attempts[-1]["retrieved_at"], "attempts": attempts}


def _commit(item: dict, repository: str, pr_number: int | None, provenance: dict) -> dict:
    commit = item.get("commit", item)
    return {"sha": item["sha"], "parent_shas": [p["sha"] for p in item.get("parents", [])],
            "tree_sha": commit.get("tree", {}).get("sha", ""),
            "author_time": commit.get("author", {}).get("date"),
            "committer_time": commit.get("committer", {}).get("date"),
            "repository": repository, "pr_number": pr_number, "provenance": provenance}


def _paged_commits(url: str, repository: str, pr_number: int | None, config: dict,
                   get: Callable = provider_get, max_pages: int = 100) -> tuple[list[dict], list[dict], str]:
    commits, provenance = [], []
    for page in range(1, max_pages + 1):
        separator = "&" if "?" in url else "?"
        body, source = _get_json(f"{url}{separator}per_page=100&page={page}", config, get)
        provenance.append(source)
        if body is None: return commits, provenance, "acquisition_failed"
        if not isinstance(body, list): return commits, provenance, "acquisition_failed"
        commits.extend(_commit(item, repository, pr_number, source) for item in body)
        if len(body) < 100: return commits, provenance, "complete"
    return commits, provenance, "truncated"


def _base_candidate(url: str, repository: str, config: dict, get: Callable = provider_get) -> tuple[list[dict], list[dict], str]:
    body, source = _get_json(f"{url}&per_page=1&page=1", config, get)
    if not isinstance(body, list): return [], [source], "acquisition_failed"
    return ([_commit(body[0], repository, None, source)] if body else []), [source], "complete"


def materialize(repository: str, sha: str, *, timeout: float = 180, run=subprocess.run) -> dict:
    remote = f"https://github.com/{repository}.git"
    try:
        with tempfile.TemporaryDirectory(prefix="dir-post-c-v4-") as directory:
            run(["git", "init", "--bare", "-q", directory], check=True, capture_output=True, timeout=30)
            fetched = run(["git", "-C", directory, "-c", "credential.helper=", "fetch", "--no-tags", "--depth=1", remote, sha],
                          check=False, capture_output=True, timeout=timeout)
            if fetched.returncode: return {"status": "acquisition_failed", "complete_recursive_tree": False}
            obj = run(["git", "-C", directory, "cat-file", "-t", sha], check=False, capture_output=True, text=True, timeout=30)
            raw = run(["git", "-C", directory, "cat-file", "-p", sha], check=False, capture_output=True, text=True, timeout=30)
            tree1 = run(["git", "-C", directory, "ls-tree", "-r", "-t", "--full-tree", sha], check=False, capture_output=True, timeout=timeout)
            tree2 = run(["git", "-C", directory, "ls-tree", "-r", "-t", "--full-tree", sha], check=False, capture_output=True, timeout=timeout)
            headers = raw.stdout.split("\n\n", 1)[0].splitlines(); trees = [x.split()[1] for x in headers if x.startswith("tree ")]; parents = [x.split()[1] for x in headers if x.startswith("parent ")]
            complete = obj.stdout.strip() == "commit" and not raw.returncode and len(trees) == 1 and not tree1.returncode and tree1.stdout == tree2.stdout
            return {"status": "materialized" if complete else "tree_materialization_failed", "object_type": obj.stdout.strip(),
                    "commit_sha": sha, "tree_sha": trees[0] if trees else "", "parent_shas": parents,
                    "recursive_tree_entry_count": len(tree1.stdout.splitlines()),
                    "recursive_tree_listing_sha256": hashlib.sha256(tree1.stdout).hexdigest() if complete else "",
                    "deterministic_repeat": tree1.stdout == tree2.stdout, "complete_recursive_tree": complete,
                    "retrieved_at": utc_now(), "source": remote}
    except (OSError, subprocess.SubprocessError):
        return {"status": "acquisition_failed", "complete_recursive_tree": False}
