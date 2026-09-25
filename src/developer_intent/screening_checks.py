"""Stage A correspondence validation and Git access checks."""

from __future__ import annotations

import re
import subprocess
import tempfile
import json
from datetime import datetime
from pathlib import Path

from .screening_github import pr_identity
from .screening_chatgpt import share_id

SHA = re.compile(r"[0-9a-fA-F]{40,64}\Z")


def correspondence(facts: dict, source: dict, case_id: str) -> dict:
    """Accept only an explicit, identity-bound review; an index pair is a lead."""
    review = facts.get("correspondence_review")
    unresolved = {"judgment": "unresolved", "source": "source_index_pair_only",
                  "reviewer": "", "timestamp": "", "version": "",
                  "evidence_ref": "", "reason": "independent_task_correspondence_not_established"}
    if review is None:
        return unresolved
    if not isinstance(review, dict):
        raise ValueError("Correspondence review must be an object")
    required = ("case_id", "pr_url", "conversation_url", "judgment", "source",
                "reviewer", "timestamp", "version", "evidence_ref", "rationale")
    if any(not isinstance(review.get(key), str) or not review[key].strip() for key in required):
        raise ValueError("Correspondence review lacks required provenance")
    try:
        reviewed_at = datetime.fromisoformat(review["timestamp"].replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Correspondence review timestamp is invalid") from exc
    if reviewed_at.tzinfo is None:
        raise ValueError("Correspondence review timestamp needs a timezone")
    if (review["case_id"] != case_id or review["pr_url"] != source["PR_Link"].strip()
            or share_id(review["conversation_url"]) != share_id(source["Conversation_Link"].strip())):
        raise ValueError("Correspondence review identity differs from source")
    if review["judgment"] not in {"yes", "no", "unresolved"}:
        raise ValueError("Unsupported correspondence judgment")
    if review["judgment"] == "yes" and review["source"] in {
            "source_index_pair_only", "text_similarity_only", "outcome_class",
            "final_diff", "integrated_implementation"}:
        raise ValueError("Unsupported positive correspondence basis")
    return {"judgment": review["judgment"], "source": review["source"],
            "reviewer": review["reviewer"], "timestamp": review["timestamp"],
            "version": review["version"], "evidence_ref": review["evidence_ref"],
            "reason": review["rationale"]}


def history_access(pr: dict | None, pr_url: str, *, run=subprocess.run) -> dict:
    """Fetch one known commit into a temporary bare Git store; read no tree or diff."""
    result = {"judgment": "unresolved", "mechanism": "git_fetch_commit_object",
              "repository": "", "object": "", "status": "not_attempted",
              "source": "PR base_sha", "reason": "PR identity or base SHA unavailable"}
    identity = pr_identity(pr_url)
    if identity is None or not isinstance(pr, dict):
        return result
    canonical = pr_identity(pr.get("html_url", ""))
    if canonical is None or canonical[2] != identity[2]:
        return result
    sha = pr.get("base_sha")
    result["repository"] = f"{canonical[0]}/{canonical[1]}"
    if not isinstance(sha, str) or not SHA.fullmatch(sha):
        return result
    result["object"] = sha
    remote = f"https://github.com/{canonical[0]}/{canonical[1]}.git"
    try:
        with tempfile.TemporaryDirectory(prefix="dir-stage-a-git-") as directory:
            run(["git", "init", "--bare", "-q", directory], check=True,
                capture_output=True, timeout=30)
            fetched = run(["git", "-C", directory, "-c", "credential.helper=",
                           "fetch", "--no-tags", "--depth=1", remote, sha],
                          check=False, capture_output=True, timeout=90)
            if fetched.returncode:
                error = fetched.stderr.decode("utf-8", errors="replace").lower()
                if ("repository not found" in error or "not a git repository" in error
                        or "authentication failed" in error or "permission denied" in error):
                    result.update(judgment="no", status="repository_inaccessible",
                                  reason="repository_access_denied_or_not_found")
                else:
                    result.update(status="fetch_failed", reason="commit_fetch_inconclusive")
                return result
            inspected = run(["git", "-C", directory, "cat-file", "-t", sha],
                            check=False, capture_output=True, timeout=30)
            if inspected.returncode == 0 and inspected.stdout.strip() == b"commit":
                result.update(judgment="yes", status="commit_object_retrieved", reason="")
            else:
                result.update(status="object_verification_failed", reason="fetched_object_not_verified_as_commit")
    except (OSError, subprocess.TimeoutExpired, subprocess.CalledProcessError):
        result.update(status="probe_error", reason="git_probe_inconclusive")
    return result


def load_review(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
