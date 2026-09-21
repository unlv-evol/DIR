"""Run Protocol v5 Stage A screening into new versioned outputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from developer_intent.screening import read_source, screen_rows, screening_summary, write_manifest  # noqa: E402
from developer_intent.screening_archive import archive_fallback  # noqa: E402
from developer_intent.screening_chatgpt import retrieve_share  # noqa: E402
from developer_intent.screening_config import load_config  # noqa: E402
from developer_intent.screening_github import retrieve_pr  # noqa: E402
from developer_intent.screening_http import HttpClient  # noqa: E402


def protect_legacy_paths(output: Path, eligible_output: Path, summary_path: Path,
                         evidence_dir: Path, cache_dir: Path, source: Path) -> None:
    """Never let a v5 run rewrite v3 results or its evidence cache."""
    old_manifest_names = {"screened_cases.csv", "pilot_cases.csv", "selection_summary.md"}
    manifests = (ROOT / "cases/manifests").resolve()
    old_intermediate = (ROOT / "data/intermediate/screening").resolve()
    old_cache = old_intermediate / "cache"
    for path in (output, eligible_output, summary_path):
        resolved = path.resolve()
        if (resolved == source.resolve()
                or (resolved.parent == manifests and resolved.name in old_manifest_names)
                or resolved == old_intermediate
                or old_intermediate in resolved.parents):
            raise ValueError(f"Protocol v5 cannot overwrite legacy/source output: {resolved}")
    for path in (evidence_dir, cache_dir):
        resolved = path.resolve()
        if resolved == old_cache or old_cache in resolved.parents:
            raise ValueError(f"Protocol v5 cannot write into legacy cache: {resolved}")


def protect_existing_outputs(output: Path, eligible_output: Path, summary_path: Path) -> None:
    """Fail before retrieval rather than replacing an earlier v5 research result."""
    paths = (output.resolve(), eligible_output.resolve(), summary_path.resolve())
    if len(set(paths)) != len(paths):
        raise ValueError("Stage A output paths must be distinct")
    existing = [str(path) for path in paths if path.exists()]
    if existing:
        raise FileExistsError("Stage A output exists; archive it before rerunning: " + ", ".join(existing))


def retrieve_candidates(candidates: list[dict], evidence_dir: Path,
                        http: HttpClient, token: str | None, refresh: bool) -> None:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    for index, row in enumerate(candidates, 1):
        sid = row["Case ID"].strip()
        path = evidence_dir / f"{sid}.json"
        facts = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        pr = retrieve_pr(row["PR_Link"], http, token=token, refresh=refresh)
        if pr["retrieval_status"].startswith("retrieved_") and pr["pr"] is not None and pr["files"] is not None:
            facts["pr"] = pr["pr"]
            facts["files"] = pr["files"]
            facts["pr_retrieval_status"] = pr["retrieval_status"]
        else:
            facts.setdefault("pr_retrieval_status", pr["retrieval_status"])
            facts["pr_latest_attempt_status"] = pr["retrieval_status"]
            facts["pr_latest_attempt_note"] = pr["notes"]
        chat = retrieve_share(row["Conversation_Link"], http, refresh=refresh)
        if chat["parsing_status"] == "parsed":
            facts["conversation"] = {
                key: chat[key] for key in ("url", "canonical_url", "share_id", "title",
                                           "start", "precision", "temporal_status", "complete", "turns",
                                           "records", "tool_trace", "other_records", "raw_conversation")
            }
            facts["conversation"].update(source_type="public_share")
            facts["conversation_parsing_status"] = "parsed"
            facts["conversation_retrieval_status"] = chat["retrieval_status"]
            facts.pop("conversation_archive_status", None)
            facts.pop("conversation_archive_members", None)
            facts.pop("conversation_archive_leads", None)
        else:
            facts.setdefault("conversation_retrieval_status", chat["retrieval_status"])
            facts.setdefault("conversation_parsing_status", chat["parsing_status"])
            facts["conversation_latest_attempt_status"] = chat["retrieval_status"]
            facts["conversation_latest_attempt_note"] = chat["notes"]
        path.write_text(json.dumps(facts, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"[{index}/{len(candidates)}] {sid}: PR={pr['retrieval_status']}; "
              f"conversation={chat['retrieval_status']}/{chat['parsing_status']}")


def apply_archive_fallback(candidates: list[dict], evidence_dir: Path,
                           archive: Path) -> Counter:
    failed = []
    for row in candidates:
        path = evidence_dir / f"{row['Case ID'].strip()}.json"
        if not path.exists():
            continue
        facts = json.loads(path.read_text(encoding="utf-8"))
        if facts.get("conversation_parsing_status") not in (None, "", "not_attempted", "parsed", "parsed_archive"):
            failed.append(row)
    if not failed:
        return Counter()
    matches = archive_fallback(archive, failed)
    counts = Counter()
    for row in failed:
        sid = row["Case ID"].strip()
        path = evidence_dir / f"{sid}.json"
        facts = json.loads(path.read_text(encoding="utf-8"))
        result = matches[sid]
        counts[result["status"]] += 1
        facts["conversation_archive_status"] = result["status"]
        if result["status"] == "recovered":
            facts["conversation"] = result["conversation"]
            facts["conversation_parsing_status"] = "parsed_archive"
            facts["conversation_retrieval_status"] = "retrieved_archive"
            facts["conversation_archive_members"] = result["matching_members"]
            facts.pop("conversation_archive_leads", None)
        elif result["status"] == "summary_only_unresolved":
            facts["conversation_archive_leads"] = result["leads"]
        elif result["status"] == "conflicting_snapshots":
            facts["conversation_archive_members"] = result["matching_members"]
        path.write_text(json.dumps(facts, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "data/raw/final_analysis_dataset_from_patchprompt_study.csv")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--eligible-output", type=Path,
                        default=ROOT / "cases/manifests/eligible_PA_PN_cases.csv")
    parser.add_argument("--summary", type=Path, default=ROOT / "cases/manifests/stage_a_summary.md")
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument("--evidence-dir", type=Path)
    parser.add_argument("--archive", type=Path, default=ROOT / "data/raw/allPullRequestSharings.zip",
                        help="PatchTrack sharing archive used after failed public-share parsing")
    parser.add_argument("--no-archive-fallback", action="store_true")
    parser.add_argument("--timeout", type=float)
    parser.add_argument("--retries", type=int)
    parser.add_argument("--limit", type=int, help="Process only first N PA/PN candidates")
    parser.add_argument("--live", action="store_true", help="Retrieve GitHub and public ChatGPT sources")
    parser.add_argument("--refresh", action="store_true", help="Re-fetch successful cached HTTP responses")
    parser.add_argument("--check-config", action="store_true", help="Print safe configuration; no network")
    args = parser.parse_args()
    if args.limit is not None and args.limit <= 0:
        parser.error("--limit must be positive")
    config = load_config(ROOT, cache_dir=args.cache_dir, output=args.output,
                         timeout=args.timeout, retries=args.retries)
    if args.check_config:
        print(config.safe_report())
        return
    output = config.output.resolve()
    eligible_output = args.eligible_output.resolve()
    summary_path = args.summary.resolve()
    source = read_source(args.source)
    candidates = [row for row in source if row["Outcome_Class"] in {"PA", "PN"}]
    if args.limit:
        candidates = candidates[:args.limit]
    if args.limit and args.output is None:
        output = ROOT / f"data/intermediate/screening_v5/smoke_{args.limit}.csv"
        if args.eligible_output == ROOT / "cases/manifests/eligible_PA_PN_cases.csv":
            eligible_output = ROOT / f"data/intermediate/screening_v5/smoke_{args.limit}_eligible.csv"
        if args.summary == ROOT / "cases/manifests/stage_a_summary.md":
            summary_path = ROOT / f"data/intermediate/screening_v5/smoke_{args.limit}_summary.md"
    evidence_dir = args.evidence_dir or config.cache_dir / "evidence"
    try:
        protect_legacy_paths(output, eligible_output, summary_path, evidence_dir,
                             config.cache_dir, args.source)
        protect_existing_outputs(output, eligible_output, summary_path)
    except (ValueError, FileExistsError) as exc:
        parser.error(str(exc))
    if args.live:
        http = HttpClient(config.cache_dir / "http", config.timeout, config.retries)
        retrieve_candidates(candidates, evidence_dir, http, config.github_token, args.refresh)
    if not args.no_archive_fallback:
        archive_counts = apply_archive_fallback(candidates, evidence_dir, args.archive)
        if archive_counts:
            print(f"Archive fallback: {dict(sorted(archive_counts.items()))}")
    screened = screen_rows(candidates, evidence_dir)
    summary = screening_summary(source, screened)
    summary += (f"\nSource CSV SHA-256: "
                f"`{hashlib.sha256(args.source.read_bytes()).hexdigest()}`\n")
    summary += f"Run scope: {'first ' + str(args.limit) if args.limit else 'all'} PA/PN candidates.\n"
    for field in ("pr_retrieval_status", "conversation_retrieval_status", "conversation_parsing_status",
                  "conversation_archive_status"):
        summary += f"{field}: {dict(sorted(Counter(row[field] for row in screened).items()))}\n"
    write_manifest(screened, output)
    write_manifest([row for row in screened if row["eligible"] == "true"], eligible_output)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(summary, encoding="utf-8")
    print(f"Source records: {len(source)}; PA/PN candidates in run: {len(screened)}; "
          f"confirmed eligible: {sum(row['eligible'] == 'true' for row in screened)}; "
          f"pending: {sum(row['eligibility_status'] == 'pending_resolution' for row in screened)}")


if __name__ == "__main__":
    main()
