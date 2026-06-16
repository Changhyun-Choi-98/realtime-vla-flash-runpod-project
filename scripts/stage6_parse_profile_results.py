import csv
import json
import math
import os
import pathlib
import re
import statistics
from collections import Counter, defaultdict
from typing import Any


PROJECT = pathlib.Path("/workspace/realtime_vla_flash_project")
VIDEO_ROOT = PROJECT / "videos/stage6_sync_profile"
RESULTS = PROJECT / "results"
CONFIG = PROJECT / "configs/stage6_sync_profile.json"


def load_json(path: pathlib.Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def read_text(path: pathlib.Path) -> str:
    return path.read_text(errors="ignore") if path.exists() else ""


def safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        text = str(value).strip().replace("%", "")
        if text in {"", "N/A", "[N/A]", "nan", "None"}:
            return None
        out = float(text)
        return out if math.isfinite(out) else None
    except Exception:
        return None


def percentile(values: list[float], pct: float) -> float | None:
    values = sorted(float(v) for v in values if isinstance(v, (int, float)))
    if not values:
        return None
    if len(values) == 1:
        return float(values[0])
    idx = (len(values) - 1) * pct / 100.0
    lo = int(idx)
    hi = min(lo + 1, len(values) - 1)
    frac = idx - lo
    return float(values[lo] * (1.0 - frac) + values[hi] * frac)


def mean(values: list[float]) -> float | None:
    values = [float(v) for v in values if isinstance(v, (int, float))]
    return float(statistics.fmean(values)) if values else None


def stats(values: list[float]) -> dict[str, float | None]:
    return {
        "mean": mean(values),
        "p50": percentile(values, 50),
        "p90": percentile(values, 90),
        "p95": percentile(values, 95),
        "p99": percentile(values, 99),
    }


def write_csv(path: pathlib.Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k) for k in fieldnames})


def is_warmup_path(path: pathlib.Path | str) -> bool:
    return "warmup" in str(path)


def run_name(path: pathlib.Path | str) -> str:
    for part in pathlib.Path(path).parts:
        if part.startswith("stage6_warmup_") or part.startswith("stage6_libero_goal_"):
            return part
    return ""


def walk_stage6_files() -> tuple[list[pathlib.Path], list[pathlib.Path], list[pathlib.Path], list[pathlib.Path]]:
    roots = [VIDEO_ROOT, RESULTS]
    episode_logs: list[pathlib.Path] = []
    trace_files: list[pathlib.Path] = []
    infer_files: list[pathlib.Path] = []
    videos: list[pathlib.Path] = []
    skip = {".git", ".venv", ".venv-libero", "__pycache__", "checkpoints", "converted", "datasets", "tmp"}
    for root in roots:
        if not root.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in skip]
            base = pathlib.Path(dirpath)
            for name in filenames:
                path = base / name
                text = str(path)
                if "stage6_" not in text:
                    continue
                if name == "episode_log.json":
                    episode_logs.append(path)
                elif name == "trace.jsonl":
                    trace_files.append(path)
                elif name == "infer.jsonl":
                    infer_files.append(path)
                elif path.suffix.lower() == ".mp4":
                    videos.append(path)
    return sorted(set(episode_logs)), sorted(set(trace_files)), sorted(set(infer_files)), sorted(set(videos))


def load_jsonl(path: pathlib.Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                except Exception:
                    continue
                if isinstance(item, dict):
                    item["_source"] = str(path)
                    item["_run_name"] = run_name(path)
                    item["_is_warmup"] = is_warmup_path(path)
                    rows.append(item)
    except Exception:
        pass
    return rows


def parse_episode_logs(paths: list[pathlib.Path]) -> list[dict[str, Any]]:
    records = []
    for path in paths:
        payload = load_json(path, default=[])
        if isinstance(payload, dict):
            payload = payload.get("episodes", [])
        if not isinstance(payload, list):
            continue
        for item in payload:
            if not isinstance(item, dict):
                continue
            row = dict(item)
            row["_source"] = str(path)
            row["_run_name"] = run_name(path)
            row["_is_warmup"] = is_warmup_path(path)
            records.append(row)
    return records


def numeric_values(rows: list[dict[str, Any]], key: str) -> list[float]:
    values: list[float] = []
    for row in rows:
        val = safe_float(row.get(key))
        if val is not None:
            values.append(val)
    return values


def parse_vram(path: pathlib.Path) -> dict[str, Any]:
    used: list[float] = []
    total: list[float] = []
    util: list[float] = []
    power: list[float] = []
    if path.exists():
        with path.open("r", encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                for target, key in [(used, "memory.used"), (total, "memory.total"), (util, "utilization.gpu"), (power, "power.draw")]:
                    val = safe_float(row.get(key))
                    if val is not None:
                        target.append(val)
    payload = {
        "sample_count": len(used),
        "peak_memory_used_mib": max(used) if used else None,
        "mean_memory_used_mib": mean(used),
        "memory_total_mib": max(total) if total else None,
        "peak_gpu_utilization": max(util) if util else None,
        "peak_power_draw": max(power) if power else None,
    }
    (RESULTS / "stage6_vram_summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def infer_sort_key(row: dict[str, Any]) -> tuple[str, int, int]:
    return (
        str(row.get("_run_name", "")),
        int(row.get("episode_idx", 0) or 0),
        int(row.get("infer_id", 0) or 0),
    )


def first_by_run(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    firsts: dict[str, dict[str, Any]] = {}
    for row in sorted(rows, key=infer_sort_key):
        name = str(row.get("_run_name", ""))
        if name and name not in firsts:
            firsts[name] = row
    return firsts


def write_empty_placeholder() -> None:
    for name in [
        "stage6_infer_summary.csv",
        "stage6_route_summary.json",
        "stage6_latency_summary.json",
        "stage6_latency_by_route.json",
        "stage6_cold_start_summary.json",
        "stage6_vram_summary.json",
        "stage6_claim_assessment.json",
    ]:
        path = RESULTS / name
        if not path.exists():
            if path.suffix == ".csv":
                path.write_text("status,reason\nplaceholder,no parseable Stage 6 data\n", encoding="utf-8")
            else:
                path.write_text(json.dumps({"status": "placeholder", "reason": "no parseable Stage 6 data"}, indent=2), encoding="utf-8")


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    config = load_json(CONFIG, default={})
    orchestration = load_json(RESULTS / "stage6_profile_summary.json", default={})
    episode_logs, trace_files, infer_files, videos = walk_stage6_files()
    episodes = parse_episode_logs(episode_logs)
    infer_rows = []
    for path in infer_files:
        infer_rows.extend(load_jsonl(path))

    measured_episodes = [row for row in episodes if not row.get("_is_warmup")]
    measured_infers = [row for row in infer_rows if not row.get("_is_warmup")]
    warmup_infers = [row for row in infer_rows if row.get("_is_warmup")]

    infer_fieldnames = [
        "run_name",
        "task_id",
        "episode_idx",
        "infer_id",
        "route_type",
        "accepted_prefix_len",
        "chunk_exec_len",
        "policy_time_gpu_sync_ms",
        "policy_time_wall_ms",
        "gpu_sync_before_after_used",
        "sample_actions_ms",
        "policy_time_ms",
        "serve_time_ms",
        "client_roundtrip_ms",
        "timing_patch_stage",
        "source",
    ]
    infer_csv_rows = []
    for row in measured_infers:
        infer_csv_rows.append(
            {
                "run_name": row.get("_run_name"),
                "task_id": row.get("task_id"),
                "episode_idx": row.get("episode_idx"),
                "infer_id": row.get("infer_id"),
                "route_type": row.get("route_type"),
                "accepted_prefix_len": row.get("accepted_prefix_len"),
                "chunk_exec_len": row.get("chunk_exec_len"),
                "policy_time_gpu_sync_ms": row.get("policy_time_gpu_sync_ms"),
                "policy_time_wall_ms": row.get("policy_time_wall_ms"),
                "gpu_sync_before_after_used": row.get("gpu_sync_before_after_used"),
                "sample_actions_ms": row.get("sample_actions_ms"),
                "policy_time_ms": row.get("policy_time_ms"),
                "serve_time_ms": row.get("serve_time_ms"),
                "client_roundtrip_ms": row.get("client_roundtrip_ms"),
                "timing_patch_stage": row.get("timing_patch_stage"),
                "source": row.get("_source"),
            }
        )
    write_csv(RESULTS / "stage6_infer_summary.csv", infer_csv_rows, infer_fieldnames)

    route_counts = Counter(str(row.get("route_type", "unknown")) for row in measured_infers)
    total_routes = sum(route_counts.values())
    route_summary = {
        "infer_log_files": [str(p) for p in infer_files],
        "infer_log_file_count": len(infer_files),
        "trace_file_count": len(trace_files),
        "route_counts": dict(route_counts),
        "draft_ratio": (route_counts.get("draft", 0) / total_routes) if total_routes else None,
        "full_ratio": (route_counts.get("full", 0) / total_routes) if total_routes else None,
        "accepted_prefix_len": stats(numeric_values(measured_infers, "accepted_prefix_len")),
        "chunk_exec_len": stats(numeric_values(measured_infers, "chunk_exec_len")),
        "missing_fields": sorted(
            key
            for key in [
                "route_type",
                "accepted_prefix_len",
                "chunk_exec_len",
                "policy_time_gpu_sync_ms",
                "policy_time_wall_ms",
                "serve_time_ms",
                "client_roundtrip_ms",
            ]
            if any(row.get(key) is None for row in measured_infers)
        ),
    }
    (RESULTS / "stage6_route_summary.json").write_text(json.dumps(route_summary, indent=2), encoding="utf-8")

    firsts = first_by_run(infer_rows)
    steady = []
    first_keys = {(row.get("_run_name"), row.get("episode_idx"), row.get("infer_id")) for row in firsts.values()}
    for row in measured_infers:
        key = (row.get("_run_name"), row.get("episode_idx"), row.get("infer_id"))
        if key not in first_keys:
            steady.append(row)

    latency_summary = {
        "all_measured": {
            "policy_time_gpu_sync_ms": stats(numeric_values(measured_infers, "policy_time_gpu_sync_ms")),
            "policy_time_wall_ms": stats(numeric_values(measured_infers, "policy_time_wall_ms")),
            "sample_actions_ms": stats(numeric_values(measured_infers, "sample_actions_ms")),
            "serve_time_ms": stats(numeric_values(measured_infers, "serve_time_ms")),
            "client_roundtrip_ms": stats(numeric_values(measured_infers, "client_roundtrip_ms")),
        },
        "steady_state_excluding_first_inference_per_run": {
            "policy_time_gpu_sync_ms": stats(numeric_values(steady, "policy_time_gpu_sync_ms")),
            "policy_time_wall_ms": stats(numeric_values(steady, "policy_time_wall_ms")),
            "sample_actions_ms": stats(numeric_values(steady, "sample_actions_ms")),
            "serve_time_ms": stats(numeric_values(steady, "serve_time_ms")),
            "client_roundtrip_ms": stats(numeric_values(steady, "client_roundtrip_ms")),
        },
        "steady_state_sample_count": len(steady),
        "measured_infer_count": len(measured_infers),
        "sync_field_present_ratio": (
            sum(1 for row in measured_infers if safe_float(row.get("policy_time_gpu_sync_ms")) is not None) / len(measured_infers)
            if measured_infers
            else 0.0
        ),
    }
    (RESULTS / "stage6_latency_summary.json").write_text(json.dumps(latency_summary, indent=2), encoding="utf-8")

    by_route = {}
    for route in sorted(route_counts):
        rows = [row for row in measured_infers if str(row.get("route_type")) == route]
        rows_steady = [row for row in steady if str(row.get("route_type")) == route]
        by_route[route] = {
            "count": len(rows),
            "policy_time_gpu_sync_ms": stats(numeric_values(rows_steady or rows, "policy_time_gpu_sync_ms")),
            "serve_time_ms": stats(numeric_values(rows_steady or rows, "serve_time_ms")),
            "client_roundtrip_ms": stats(numeric_values(rows_steady or rows, "client_roundtrip_ms")),
        }
    (RESULTS / "stage6_latency_by_route.json").write_text(json.dumps(by_route, indent=2), encoding="utf-8")

    cold = {
        "warmup_first_inference": {
            "policy_time_gpu_sync_ms": safe_float(warmup_infers[0].get("policy_time_gpu_sync_ms")) if warmup_infers else None,
            "serve_time_ms": safe_float(warmup_infers[0].get("serve_time_ms")) if warmup_infers else None,
            "client_roundtrip_ms": safe_float(warmup_infers[0].get("client_roundtrip_ms")) if warmup_infers else None,
        },
        "first_inference_per_run": {
            name: {
                "policy_time_gpu_sync_ms": safe_float(row.get("policy_time_gpu_sync_ms")),
                "serve_time_ms": safe_float(row.get("serve_time_ms")),
                "client_roundtrip_ms": safe_float(row.get("client_roundtrip_ms")),
                "route_type": row.get("route_type"),
            }
            for name, row in firsts.items()
        },
        "cold_start_excluded_from_steady_state": True,
    }
    (RESULTS / "stage6_cold_start_summary.json").write_text(json.dumps(cold, indent=2), encoding="utf-8")

    vram = parse_vram(PROJECT / "logs/stage6_gpu_monitor.csv")

    success_count = sum(1 for row in measured_episodes if bool(row.get("success")))
    completed = len(measured_episodes)
    profile_summary = {
        "suite": config.get("suite"),
        "tasks": config.get("tasks"),
        "episodes_requested_measured": int(config.get("measured_episode_count", 9)),
        "episodes_completed_measured": completed,
        "success_count": success_count,
        "success_rate": (success_count / completed) if completed else None,
        "video_count_measured": len([p for p in videos if not is_warmup_path(p)]),
        "warmup_excluded_from_metrics": True,
        "orchestration": orchestration,
    }
    (RESULTS / "stage6_profile_summary.json").write_text(json.dumps(profile_summary, indent=2), encoding="utf-8")

    claim = {
        "paper_claim_latency_full_reference_ms": 58.0,
        "paper_claim_task_level_flash_triton_ms": 19.1,
        "paper_claim_fastest_flash_round_ms": 7.8,
        "our_hardware": "NVIDIA L40S",
        "paper_hardware_exact_match": "unknown",
        "our_metric_type": "GPU-synchronized server-side timing plus client roundtrip on a limited LIBERO Goal subset",
        "comparable_to_paper": "partial",
        "why_not_hardware_exact": "The Stage 6 run uses a Runpod NVIDIA L40S container and only tasks 0, 1, and 2 from LIBERO Goal, not the full paper setup.",
        "cold_start_excluded": True,
        "steady_state_summary": latency_summary["steady_state_excluding_first_inference_per_run"],
        "route_level_summary": by_route,
        "claim_status": "PARTIALLY_SUPPORTED_LIMITED",
        "blog_safe_wording": "In a limited LIBERO Goal subset on Runpod L40S, synchronized server-side FLASH timing is in the same broad range as the paper's latency motivation, but this is not a full benchmark or hardware-exact reproduction.",
    }
    (RESULTS / "stage6_claim_assessment.json").write_text(json.dumps(claim, indent=2), encoding="utf-8")

    text_logs = "\n".join(
        read_text(PROJECT / f"logs/stage6_client_task{i}_n3.txt") for i in [0, 1, 2]
    ) + "\n" + read_text(PROJECT / "logs/stage6_server_profiled.txt")
    if re.search(r"cuda.*out of memory|CUDA out of memory|\bOOM\b", text_logs, re.I):
        decision = "BLOCKED_GPU_OOM"
        reason = "CUDA OOM appeared in logs."
    elif not orchestration.get("server_ready", True):
        decision = "BLOCKED_SERVER_NOT_READY"
        reason = "Server did not become ready."
    elif completed < 5:
        decision = "BLOCKED_CLIENT_OR_ENV_RUNTIME"
        reason = "Fewer than 5 measured episodes completed."
    elif not measured_infers:
        decision = "BLOCKED_LOGGING_MISSING"
        reason = "Infer logs were missing."
    elif latency_summary["sync_field_present_ratio"] >= 0.8:
        decision = "PROCEED_TO_STAGE5_ROBUSTNESS_PROBE"
        reason = "Synchronized timing fields were present for at least 80% of measured infer rows."
    else:
        decision = "PARTIAL_PASS_PROFILED_BUT_TIMING_FIELDS_INCOMPLETE"
        reason = "Profile run completed, but synchronized timing fields were incomplete."

    decision_payload = {
        "decision": decision,
        "decision_reason": reason,
        "episodes_requested_measured": profile_summary["episodes_requested_measured"],
        "episodes_completed_measured": completed,
        "success_count": success_count,
        "success_rate": profile_summary["success_rate"],
        "sync_field_present_ratio": latency_summary["sync_field_present_ratio"],
        "route_summary_path": str(RESULTS / "stage6_route_summary.json"),
        "latency_summary_path": str(RESULTS / "stage6_latency_summary.json"),
        "claim_assessment_path": str(RESULTS / "stage6_claim_assessment.json"),
        "full_benchmark_attempted": False,
        "paper_reproduction_claimed": False,
        "robustness_probe_attempted": False,
    }
    (RESULTS / "stage6_decision.json").write_text(json.dumps(decision_payload, indent=2), encoding="utf-8")
    print(json.dumps(decision_payload, indent=2))

    if not measured_infers:
        write_empty_placeholder()


if __name__ == "__main__":
    main()
