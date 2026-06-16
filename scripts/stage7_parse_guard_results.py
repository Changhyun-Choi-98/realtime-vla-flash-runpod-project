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
VIDEO_ROOT = PROJECT / "videos/stage7_wrist_health_guard"
RESULTS = PROJECT / "results"
CONDITIONS = ["guard_wrist_zero_every4", "guard_wrist_zero_all"]
TASKS = [0, 1, 2]


def load_json(path: pathlib.Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


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


def boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


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
            writer.writerow({key: row.get(key) for key in fieldnames})


def condition_from_path(path: pathlib.Path | str) -> str:
    text = str(path)
    if "stage7_sanity_clean_guard" in text:
        return "sanity_clean_guard"
    if "stage7_guard_every4" in text:
        return "guard_wrist_zero_every4"
    if "stage7_guard_allzero" in text:
        return "guard_wrist_zero_all"
    return "unknown"


def stage5_condition(stage7_condition: str) -> str:
    return {
        "guard_wrist_zero_every4": "wrist_zero_every4",
        "guard_wrist_zero_all": "wrist_zero_all",
    }.get(stage7_condition, "")


def run_name(path: pathlib.Path | str) -> str:
    for part in pathlib.Path(path).parts:
        if part.startswith("stage7_"):
            return part
    return ""


def walk_files() -> tuple[list[pathlib.Path], list[pathlib.Path], list[pathlib.Path], list[pathlib.Path]]:
    roots = [VIDEO_ROOT]
    skip = {".git", ".venv", ".venv-libero", "__pycache__", "checkpoints", "converted", "datasets", "tmp"}
    episode_logs: list[pathlib.Path] = []
    trace_files: list[pathlib.Path] = []
    infer_files: list[pathlib.Path] = []
    videos: list[pathlib.Path] = []
    for root in roots:
        if not root.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in skip]
            base = pathlib.Path(dirpath)
            for name in filenames:
                path = base / name
                if path.name == "episode_log.json":
                    episode_logs.append(path)
                elif path.name == "trace.jsonl":
                    trace_files.append(path)
                elif path.name == "infer.jsonl":
                    infer_files.append(path)
                elif path.suffix.lower() == ".mp4":
                    videos.append(path)
    return sorted(episode_logs), sorted(trace_files), sorted(infer_files), sorted(videos)


def load_jsonl(path: pathlib.Path) -> list[dict[str, Any]]:
    rows = []
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
                    item["_condition"] = condition_from_path(path)
                    rows.append(item)
    except Exception:
        pass
    return rows


def parse_episode_logs(paths: list[pathlib.Path]) -> list[dict[str, Any]]:
    rows = []
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
            row["_condition"] = condition_from_path(path)
            rows.append(row)
    return rows


def read_csv(path: pathlib.Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def numeric(rows: list[dict[str, Any]], key: str) -> list[float]:
    out = []
    for row in rows:
        value = safe_float(row.get(key))
        if value is not None:
            out.append(value)
    return out


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
    (RESULTS / "stage7_vram_summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def classify_failure(row: dict[str, Any]) -> str:
    if boolish(row.get("success")):
        return "no failure"
    reason = str(row.get("failure_reason") or "").lower()
    if "connect" in reason or "websocket" in reason:
        return "server/client connection failure"
    if re.search(r"shape|control|action", reason):
        return "action shape/control failure"
    if re.search(r"egl|mujoco|robosuite|render|sim", reason):
        return "simulator runtime failure"
    if "cache" in reason:
        return "stale-cache-induced failure"
    return "perturbation-induced perception failure"


def stage5_task_rates() -> dict[tuple[str, int], dict[str, Any]]:
    rows = read_csv(RESULTS / "stage5_condition_task_summary.csv")
    out: dict[tuple[str, int], dict[str, Any]] = {}
    for row in rows:
        cond = row.get("condition", "")
        task = int(row.get("task_id", -1))
        out[(cond, task)] = {
            "success_rate": safe_float(row.get("success_rate")) or 0.0,
            "success_count": int(float(row.get("success_count", 0) or 0)),
            "episodes_completed": int(float(row.get("episodes_completed", 0) or 0)),
        }
    return out


def stage4_task_rates() -> dict[int, float]:
    rows = read_csv(RESULTS / "stage4_task_summary.csv")
    out: dict[int, float] = {}
    for row in rows:
        task = int(row.get("task_id", row.get("task", -1)) or -1)
        rate = safe_float(row.get("success_rate"))
        if task >= 0 and rate is not None:
            out[task] = rate
    return out


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    episode_files, trace_files, infer_files, videos = walk_files()
    episodes = parse_episode_logs(episode_files)
    infer_rows = []
    trace_rows = []
    for path in infer_files:
        infer_rows.extend(load_jsonl(path))
    for path in trace_files:
        trace_rows.extend(load_jsonl(path))

    measured_episodes = [r for r in episodes if r.get("_condition") in CONDITIONS]
    measured_infer = [r for r in infer_rows if r.get("_condition") in CONDITIONS]

    episode_summary = []
    for row in measured_episodes:
        failure_mode = classify_failure(row)
        episode_summary.append(
            {
                "condition": row.get("_condition"),
                "task_id": row.get("task_id"),
                "episode_idx": row.get("episode_idx"),
                "completed": True,
                "success": boolish(row.get("success")),
                "steps": row.get("steps"),
                "infer_calls": row.get("infer_calls"),
                "failure_reason": row.get("failure_reason"),
                "failure_mode": failure_mode,
                "video_path": row.get("video_path"),
                "source": row.get("_source"),
            }
        )

    ep_fields = [
        "condition",
        "task_id",
        "episode_idx",
        "completed",
        "success",
        "steps",
        "infer_calls",
        "failure_reason",
        "failure_mode",
        "video_path",
        "source",
    ]
    write_csv(RESULTS / "stage7_episode_summary.csv", episode_summary, ep_fields)

    stage5_rates = stage5_task_rates()
    stage4_rates = stage4_task_rates()
    task_summary = []
    for cond in CONDITIONS:
        prev_cond = stage5_condition(cond)
        for task in TASKS:
            rows = [r for r in episode_summary if r["condition"] == cond and int(r["task_id"]) == task]
            completed = len(rows)
            success = sum(1 for r in rows if boolish(r["success"]))
            rate = success / completed if completed else 0.0
            prev = stage5_rates.get((prev_cond, task), {"success_rate": 0.0, "success_count": 0, "episodes_completed": 0})
            task_summary.append(
                {
                    "condition": cond,
                    "task_id": task,
                    "episodes_requested": 5 if cond == "guard_wrist_zero_every4" else 3,
                    "episodes_completed": completed,
                    "success_count": success,
                    "success_rate": rate,
                    "stage5_no_guard_condition": prev_cond,
                    "stage5_no_guard_success": prev["success_count"],
                    "stage5_no_guard_completed": prev["episodes_completed"],
                    "stage5_no_guard_success_rate": prev["success_rate"],
                    "recovery_vs_stage5": rate - float(prev["success_rate"]),
                    "stage4_clean_success_rate": stage4_rates.get(task),
                    "success_gap_to_stage4_clean": None if task not in stage4_rates else float(stage4_rates[task]) - rate,
                    "main_failure_mode": Counter(r["failure_mode"] for r in rows if not boolish(r["success"])).most_common(1)[0][0]
                    if any(not boolish(r["success"]) for r in rows)
                    else "no failure",
                }
            )
    write_csv(
        RESULTS / "stage7_condition_task_summary.csv",
        task_summary,
        [
            "condition",
            "task_id",
            "episodes_requested",
            "episodes_completed",
            "success_count",
            "success_rate",
            "stage5_no_guard_condition",
            "stage5_no_guard_success",
            "stage5_no_guard_completed",
            "stage5_no_guard_success_rate",
            "recovery_vs_stage5",
            "stage4_clean_success_rate",
            "success_gap_to_stage4_clean",
            "main_failure_mode",
        ],
    )

    infer_out = []
    infer_fields = [
        "condition",
        "run_name",
        "task_id",
        "episode_idx",
        "infer_id",
        "route_type",
        "accepted_prefix_len",
        "chunk_exec_len",
        "policy_time_gpu_sync_ms",
        "policy_time_wall_ms",
        "policy_time_ms",
        "serve_time_ms",
        "client_roundtrip_ms",
        "sample_actions_ms",
        "stage5_perturb_enabled",
        "stage5_perturb_condition",
        "stage5_perturb_applied",
        "stage7_guard_enabled",
        "stage7_guard_mode",
        "stage7_wrist_health_mean",
        "stage7_wrist_health_std",
        "stage7_wrist_health_range",
        "stage7_wrist_healthy",
        "stage7_cache_available",
        "stage7_cache_age_queries",
        "stage7_cache_hit",
        "stage7_cache_miss",
        "stage7_image_replaced",
        "stage7_cache_updated",
        "stage7_guard_query_index",
        "stage7_guard_note",
        "source",
    ]
    for row in measured_infer:
        infer_out.append(
            {
                "condition": row.get("_condition"),
                "run_name": row.get("_run_name"),
                "task_id": row.get("task_id"),
                "episode_idx": row.get("episode_idx"),
                "infer_id": row.get("infer_id"),
                "route_type": row.get("route_type"),
                "accepted_prefix_len": row.get("accepted_prefix_len"),
                "chunk_exec_len": row.get("chunk_exec_len"),
                "policy_time_gpu_sync_ms": row.get("policy_time_gpu_sync_ms"),
                "policy_time_wall_ms": row.get("policy_time_wall_ms"),
                "policy_time_ms": row.get("policy_time_ms"),
                "serve_time_ms": row.get("serve_time_ms"),
                "client_roundtrip_ms": row.get("client_roundtrip_ms"),
                "sample_actions_ms": row.get("sample_actions_ms"),
                "stage5_perturb_enabled": row.get("stage5_perturb_enabled"),
                "stage5_perturb_condition": row.get("stage5_perturb_condition"),
                "stage5_perturb_applied": row.get("stage5_perturb_applied"),
                "stage7_guard_enabled": row.get("stage7_guard_enabled"),
                "stage7_guard_mode": row.get("stage7_guard_mode"),
                "stage7_wrist_health_mean": row.get("stage7_wrist_health_mean"),
                "stage7_wrist_health_std": row.get("stage7_wrist_health_std"),
                "stage7_wrist_health_range": row.get("stage7_wrist_health_range"),
                "stage7_wrist_healthy": row.get("stage7_wrist_healthy"),
                "stage7_cache_available": row.get("stage7_cache_available"),
                "stage7_cache_age_queries": row.get("stage7_cache_age_queries"),
                "stage7_cache_hit": row.get("stage7_cache_hit"),
                "stage7_cache_miss": row.get("stage7_cache_miss"),
                "stage7_image_replaced": row.get("stage7_image_replaced"),
                "stage7_cache_updated": row.get("stage7_cache_updated"),
                "stage7_guard_query_index": row.get("stage7_guard_query_index"),
                "stage7_guard_note": row.get("stage7_guard_note"),
                "source": row.get("_source"),
            }
        )
    write_csv(RESULTS / "stage7_infer_summary.csv", infer_out, infer_fields)

    missing_fields = []
    for field in [
        "stage7_guard_enabled",
        "stage7_wrist_healthy",
        "stage7_cache_hit",
        "stage7_cache_miss",
        "stage7_cache_updated",
        "stage7_image_replaced",
    ]:
        if any(row.get(field) is None for row in measured_infer):
            missing_fields.append(field)

    route_summary = {"conditions": {}, "missing_fields": missing_fields, "infer_log_files": [str(p) for p in infer_files], "trace_file_count": len(trace_files)}
    latency_summary = {}
    guard_summary = {"conditions": {}}
    for cond in CONDITIONS:
        rows = [r for r in measured_infer if r.get("_condition") == cond]
        route_counts = Counter(str(r.get("route_type", "unknown")) for r in rows)
        total_routes = sum(route_counts.values())
        guard_count = len(rows)
        cache_hits = sum(1 for r in rows if boolish(r.get("stage7_cache_hit")))
        cache_misses = sum(1 for r in rows if boolish(r.get("stage7_cache_miss")))
        cache_updates = sum(1 for r in rows if boolish(r.get("stage7_cache_updated")))
        replacements = sum(1 for r in rows if boolish(r.get("stage7_image_replaced")))
        healthy = sum(1 for r in rows if boolish(r.get("stage7_wrist_healthy")))
        unhealthy = guard_count - healthy
        ages = [v for v in numeric(rows, "stage7_cache_age_queries") if v >= 0]
        route_summary["conditions"][cond] = {
            "route_counts": dict(route_counts),
            "draft_ratio": route_counts.get("draft", 0) / total_routes if total_routes else None,
            "full_ratio": route_counts.get("full", 0) / total_routes if total_routes else None,
            "accepted_prefix_len": stats(numeric(rows, "accepted_prefix_len")),
            "chunk_exec_len": stats(numeric(rows, "chunk_exec_len")),
            "infer_count": len(rows),
        }
        latency_summary[cond] = {
            "policy_time_gpu_sync_ms": stats(numeric(rows, "policy_time_gpu_sync_ms")),
            "policy_time_ms": stats(numeric(rows, "policy_time_ms")),
            "serve_time_ms": stats(numeric(rows, "serve_time_ms")),
            "client_roundtrip_ms": stats(numeric(rows, "client_roundtrip_ms")),
            "sample_actions_ms": stats(numeric(rows, "sample_actions_ms")),
        }
        guard_summary["conditions"][cond] = {
            "guard_infer_count": guard_count,
            "guard_cache_hit_count": cache_hits,
            "guard_cache_miss_count": cache_misses,
            "guard_cache_update_count": cache_updates,
            "guard_replacement_count": replacements,
            "guard_cache_hit_rate": cache_hits / guard_count if guard_count else None,
            "guard_cache_miss_rate": cache_misses / guard_count if guard_count else None,
            "guard_replacement_rate": replacements / guard_count if guard_count else None,
            "wrist_healthy_rate": healthy / guard_count if guard_count else None,
            "wrist_unhealthy_rate": unhealthy / guard_count if guard_count else None,
            "mean_cache_age_queries": mean(ages),
        }

    (RESULTS / "stage7_route_summary.json").write_text(json.dumps(route_summary, indent=2), encoding="utf-8")
    (RESULTS / "stage7_latency_summary.json").write_text(json.dumps(latency_summary, indent=2), encoding="utf-8")
    (RESULTS / "stage7_guard_summary.json").write_text(json.dumps(guard_summary, indent=2), encoding="utf-8")
    vram = parse_vram(PROJECT / "logs/stage7_gpu_monitor.csv")

    failure_rows = [r for r in episode_summary if not boolish(r["success"])]
    by_cond_task: dict[str, dict[str, int]] = defaultdict(dict)
    grouped = defaultdict(Counter)
    for row in failure_rows:
        grouped[f"{row['condition']}_task{row['task_id']}"][row["failure_mode"]] += 1
    for key, counter in grouped.items():
        by_cond_task[key] = dict(counter)
    failure_summary = {"failure_count": len(failure_rows), "failure_types_by_condition_task": dict(by_cond_task), "failures": failure_rows}
    (RESULTS / "stage7_failure_summary.json").write_text(json.dumps(failure_summary, indent=2), encoding="utf-8")

    condition_aggregate = {}
    for cond in CONDITIONS:
        rows = [r for r in episode_summary if r["condition"] == cond]
        completed = len(rows)
        success = sum(1 for r in rows if boolish(r["success"]))
        prev_rows = [r for r in task_summary if r["condition"] == cond]
        prev_completed = sum(int(r["stage5_no_guard_completed"]) for r in prev_rows)
        prev_success = sum(int(r["stage5_no_guard_success"]) for r in prev_rows)
        prev_rate = prev_success / prev_completed if prev_completed else 0.0
        rate = success / completed if completed else 0.0
        condition_aggregate[cond] = {
            "episodes_requested": 15 if cond == "guard_wrist_zero_every4" else 9,
            "episodes_completed": completed,
            "success_count": success,
            "success_rate": rate,
            "stage5_no_guard_success_count": prev_success,
            "stage5_no_guard_completed": prev_completed,
            "stage5_no_guard_success_rate": prev_rate,
            "success_recovery_vs_stage5": rate - prev_rate,
            "success_gap_to_stage4_clean": 0.9 - rate,
        }

    comparison = {
        "stage4_clean_aggregate_success_rate": 0.9,
        "condition_aggregate": condition_aggregate,
        "condition_task_rows": task_summary,
        "route_summary_by_condition": route_summary["conditions"],
        "guard_summary_by_condition": guard_summary["conditions"],
        "interpretation": "Compare guard results to Stage 5 no-guard dropout; this is a minimal extension probe only.",
    }
    (RESULTS / "stage7_comparison_to_stage5.json").write_text(json.dumps(comparison, indent=2), encoding="utf-8")

    log_texts = []
    for path in (PROJECT / "logs").glob("stage7_*.txt"):
        if path.name in {"stage7_parse_results.txt"}:
            continue
        text = path.read_text(errors="ignore")
        cleaned_lines = []
        for line in text.splitlines():
            low = line.lower()
            if "info:root:actions shape=" in low:
                continue
            if "exception ignored in:" in low:
                continue
            if "eglcontext.__del__" in low or "mjrendercontext.__del__" in low:
                continue
            cleaned_lines.append(line)
        log_texts.append("\n".join(cleaned_lines))
    all_logs = "\n".join(log_texts)
    orch = load_json(RESULTS / "stage7_orchestration.json", {})
    if load_json(RESULTS / "stage7_patch_status.json", {}).get("decision") == "BLOCKED_GUARD_PATCH_TARGET_UNKNOWN":
        decision = "BLOCKED_GUARD_PATCH_TARGET_UNKNOWN"
    elif not orch.get("server_ready", True):
        decision = "BLOCKED_SERVER_NOT_READY"
    elif re.search(r"CUDA out of memory|out of memory", all_logs, re.I):
        decision = "BLOCKED_GPU_OOM"
    elif re.search(
        r"(Traceback|ERROR|Exception)[\s\S]{0,800}(action shape|shape mismatch|control error|invalid action|action dimension)",
        all_logs,
        re.I,
    ):
        decision = "BLOCKED_ACTION_SHAPE_OR_CONTROL"
    elif len(measured_episodes) < 12:
        decision = "BLOCKED_CLIENT_OR_ENV_RUNTIME"
    elif measured_episodes and (not infer_files or not trace_files):
        decision = "BLOCKED_LOGGING_MISSING"
    elif len(measured_episodes) >= 20 and not missing_fields:
        decision = "PROCEED_TO_STAGE8_FINAL_BLOG"
    else:
        decision = "PARTIAL_PASS_EXTENSION_ANALYZABLE"

    payload = {
        "decision": decision,
        "decision_reason": "Stage 7 guard run completed and logs were parseable." if decision.startswith("PROCEED") else "See blocker classification.",
        "measured_conditions": CONDITIONS,
        "episodes_requested_measured": 24,
        "episodes_completed_measured": len(measured_episodes),
        "condition_aggregate": condition_aggregate,
        "guard_summary": guard_summary,
        "missing_fields": missing_fields,
        "video_count": len([v for v in videos if "stage7_sanity_clean_guard" not in str(v)]),
        "full_benchmark_attempted": False,
        "paper_reproduction_claimed": False,
        "extension_claim_scope": "limited to LIBERO Goal tasks 0-2 under synthetic wrist-image dropout",
    }
    (RESULTS / "stage7_decision.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
