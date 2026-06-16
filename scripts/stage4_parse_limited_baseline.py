import csv
import json
import os
import pathlib
import re
import statistics
from collections import Counter, defaultdict
from typing import Any


PROJECT = pathlib.Path("/workspace/realtime_vla_flash_project")
OFFICIAL_DIR = PROJECT / "repos/realtime-vla-flash"
VIDEO_ROOT = PROJECT / "videos/stage4_limited_baseline"
RESULTS = PROJECT / "results"
CONFIG = PROJECT / "configs/stage4_libero_goal_limited_baseline.json"


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
        value = str(value).strip().replace("%", "")
        if value in {"", "N/A", "[N/A]", "nan", "None"}:
            return None
        return float(value)
    except Exception:
        return None


def percentile(values: list[float], pct: float) -> float | None:
    values = sorted(float(v) for v in values if isinstance(v, (int, float)))
    if not values:
        return None
    if len(values) == 1:
        return float(values[0])
    idx = (len(values) - 1) * (pct / 100.0)
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


def walk_relevant_files() -> tuple[list[pathlib.Path], list[pathlib.Path], list[pathlib.Path], list[pathlib.Path]]:
    roots = [VIDEO_ROOT, RESULTS, OFFICIAL_DIR]
    skip_names = {
        ".git",
        ".venv",
        ".venv-libero",
        "__pycache__",
        "checkpoints",
        "converted",
        "third_party",
        "node_modules",
        "wandb",
    }
    episode_logs: list[pathlib.Path] = []
    trace_files: list[pathlib.Path] = []
    infer_files: list[pathlib.Path] = []
    videos: list[pathlib.Path] = []
    for root in roots:
        if not root.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [name for name in dirnames if name not in skip_names]
            base = pathlib.Path(dirpath)
            for filename in filenames:
                path = base / filename
                path_text = str(path)
                if "stage4_" not in path_text:
                    continue
                if path.name == "episode_log.json":
                    episode_logs.append(path)
                elif path.name == "trace.jsonl":
                    trace_files.append(path)
                elif path.name == "infer.jsonl":
                    infer_files.append(path)
                elif path.suffix.lower() == ".mp4":
                    videos.append(path)
    return sorted(set(episode_logs)), sorted(set(trace_files)), sorted(set(infer_files)), sorted(set(videos))


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
                    if isinstance(item, dict):
                        item["_source"] = str(path)
                        item["_run_name"] = run_name(path)
                        item["_is_warmup"] = is_warmup_path(path)
                        rows.append(item)
                except Exception:
                    pass
    except Exception:
        pass
    return rows


def is_warmup_path(path: pathlib.Path | str) -> bool:
    return "warmup" in str(path)


def run_name(path: pathlib.Path | str) -> str:
    parts = pathlib.Path(path).parts
    for part in parts:
        if part.startswith("stage4_warmup_") or part.startswith("stage4_libero_goal_"):
            return part
    return ""


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


def parse_vram(path: pathlib.Path) -> dict[str, Any]:
    used: list[float] = []
    util: list[float] = []
    power: list[float] = []
    total_values: list[float] = []
    if path.exists():
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                u = safe_float(row.get("memory.used"))
                t = safe_float(row.get("memory.total"))
                gu = safe_float(row.get("utilization.gpu"))
                pw = safe_float(row.get("power.draw"))
                if u is not None:
                    used.append(u)
                if t is not None:
                    total_values.append(t)
                if gu is not None:
                    util.append(gu)
                if pw is not None:
                    power.append(pw)
    payload = {
        "sample_count": len(used),
        "peak_memory_used_mib": max(used) if used else None,
        "mean_memory_used_mib": mean(used),
        "memory_total_mib": max(total_values) if total_values else None,
        "peak_gpu_utilization": max(util) if util else None,
        "peak_power_draw": max(power) if power else None,
    }
    (RESULTS / "stage4_vram_summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def classify_failure(reason: str | None, success: bool) -> str:
    if success:
        return "no failure"
    text = str(reason or "").lower()
    if not text:
        return "policy behavior/no success"
    if "connect" in text or "websocket" in text:
        return "client/server connection failure"
    if "shape" in text or "action" in text or "control" in text:
        return "action shape/control failure"
    if "egl" in text or "mujoco" in text or "robosuite" in text or "render" in text:
        return "simulator runtime failure"
    if "gripper" in text or "contact" in text:
        return "gripper/contact failure"
    return "policy behavior/no success"


def first_infer_by_run(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    firsts = {}
    for row in sorted(records, key=lambda r: (str(r.get("_run_name", "")), int(r.get("episode_idx", 0)), int(r.get("infer_id", 0)))):
        name = str(row.get("_run_name", ""))
        if name and name not in firsts:
            firsts[name] = row
    return firsts


def classify_decision(
    orchestration: dict[str, Any],
    measured_episodes: list[dict[str, Any]],
    measured_infers: list[dict[str, Any]],
    trace_files: list[pathlib.Path],
    server_log: str,
    client_logs: str,
) -> tuple[str, str]:
    text = f"{server_log}\n{client_logs}"
    if not orchestration.get("server_ready"):
        return "BLOCKED_SERVER_NOT_READY", "Server did not become ready."
    if re.search(r"cuda.*out of memory|CUDA out of memory|\bOOM\b", text, re.I):
        return "BLOCKED_GPU_OOM", "CUDA OOM appeared in logs."
    if re.search(r"(error|exception|traceback).{0,160}(shape|control|action dimension|wrong.*action)", text, re.I | re.S):
        return "BLOCKED_ACTION_SHAPE_OR_CONTROL", "Action shape/control error appeared in logs."
    completed = len(measured_episodes)
    if completed < 15:
        return "BLOCKED_CLIENT_OR_ENV_RUNTIME", "Fewer than 15 measured episodes completed."
    if measured_episodes and (not measured_infers or not trace_files):
        return "BLOCKED_LOGGING_MISSING", "Episode logs exist but infer or trace logs are missing."
    if completed >= 25:
        success_count = sum(1 for row in measured_episodes if bool(row.get("success")))
        success_rate = float(success_count) / float(completed)
        if success_rate >= 0.5:
            return "PROCEED_TO_STAGE5_ROBUSTNESS_AND_STAGE6_PROFILING", "At least 25 measured episodes completed, logs are parseable, and success rate is >= 0.5."
        return "PARTIAL_PASS_LOW_SUCCESS_OR_TASK_FAILURES", "Measured episodes completed, but aggregate success rate is below 0.5."
    return "PARTIAL_PASS_LOW_SUCCESS_OR_TASK_FAILURES", "Partial measured baseline completed."


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    config = load_json(CONFIG, default={})
    orchestration = load_json(RESULTS / "stage4_smoke_orchestration.json", default={})
    episode_log_files, trace_files, infer_files, videos = walk_relevant_files()
    episodes_all = parse_episode_logs(episode_log_files)
    infers_all = []
    for path in infer_files:
        infers_all.extend(load_jsonl(path))
    traces_all = []
    for path in trace_files:
        traces_all.extend(load_jsonl(path))

    measured_episodes = [row for row in episodes_all if not row.get("_is_warmup")]
    warmup_episodes = [row for row in episodes_all if row.get("_is_warmup")]
    measured_infers = [row for row in infers_all if not row.get("_is_warmup")]
    warmup_infers = [row for row in infers_all if row.get("_is_warmup")]
    measured_trace_files = [path for path in trace_files if not is_warmup_path(path)]
    measured_infer_files = [path for path in infer_files if not is_warmup_path(path)]
    measured_videos = [path for path in videos if not is_warmup_path(path)]

    episode_rows = []
    for idx, row in enumerate(measured_episodes):
        success = bool(row.get("success"))
        episode_rows.append(
            {
                "episode_global": idx,
                "task_suite_name": row.get("task_suite_name"),
                "task_id": row.get("task_id"),
                "episode_idx": row.get("episode_idx"),
                "completed": True,
                "success": success,
                "steps": row.get("env_steps_taken"),
                "infer_calls": row.get("infer_calls"),
                "failure_reason": row.get("failure_reason"),
                "failure_mode": classify_failure(row.get("failure_reason"), success),
                "video_path": row.get("video_path"),
                "run_name": row.get("_run_name"),
                "source": row.get("_source"),
            }
        )
    write_csv(
        RESULTS / "stage4_episode_summary.csv",
        episode_rows,
        [
            "episode_global",
            "task_suite_name",
            "task_id",
            "episode_idx",
            "completed",
            "success",
            "steps",
            "infer_calls",
            "failure_reason",
            "failure_mode",
            "video_path",
            "run_name",
            "source",
        ],
    )

    tasks = list(config.get("tasks", [0, 1, 2]))
    requested_per_task = int(config.get("num_trials_per_task", 10))
    task_rows = []
    for task_id in tasks:
        rows = [row for row in measured_episodes if int(row.get("task_id", -1)) == int(task_id)]
        success_count = sum(1 for row in rows if bool(row.get("success")))
        completed = len(rows)
        failure_modes = Counter(classify_failure(row.get("failure_reason"), bool(row.get("success"))) for row in rows)
        main_failure = "no failure"
        if completed != requested_per_task:
            main_failure = "client/server connection failure" if not rows else "logging/observability failure"
        elif success_count < completed:
            failure_only = Counter(
                classify_failure(row.get("failure_reason"), bool(row.get("success")))
                for row in rows
                if not bool(row.get("success"))
            )
            main_failure = failure_only.most_common(1)[0][0] if failure_only else "policy behavior/no success"
        task_rows.append(
            {
                "task_id": task_id,
                "episodes_requested": requested_per_task,
                "episodes_completed": completed,
                "success_count": success_count,
                "success_rate": (float(success_count) / float(completed)) if completed else 0.0,
                "main_failure_mode": main_failure,
            }
        )
    write_csv(
        RESULTS / "stage4_task_summary.csv",
        task_rows,
        ["task_id", "episodes_requested", "episodes_completed", "success_count", "success_rate", "main_failure_mode"],
    )

    infer_rows = []
    for row in measured_infers:
        infer_rows.append(
            {
                "run_name": row.get("_run_name"),
                "task_id": row.get("task_id"),
                "episode_idx": row.get("episode_idx"),
                "infer_id": row.get("infer_id"),
                "route_type": row.get("route_type"),
                "accepted_prefix_len": row.get("accepted_prefix_len"),
                "chunk_exec_len": row.get("chunk_exec_len"),
                "policy_time_ms": row.get("policy_time_ms"),
                "serve_time_ms": row.get("serve_time_ms"),
                "client_roundtrip_ms": row.get("client_roundtrip_ms"),
                "sample_actions_ms": row.get("sample_actions_ms"),
            }
        )
    write_csv(
        RESULTS / "stage4_infer_summary.csv",
        infer_rows,
        [
            "run_name",
            "task_id",
            "episode_idx",
            "infer_id",
            "route_type",
            "accepted_prefix_len",
            "chunk_exec_len",
            "policy_time_ms",
            "serve_time_ms",
            "client_roundtrip_ms",
            "sample_actions_ms",
        ],
    )

    route_counts = Counter(str(row.get("route_type", "unknown")) for row in measured_infers)
    by_task_routes: dict[str, Counter] = defaultdict(Counter)
    for row in measured_infers:
        by_task_routes[str(row.get("task_id"))][str(row.get("route_type", "unknown"))] += 1
    total_routes = sum(route_counts.values())
    accepted_values = [safe_float(row.get("accepted_prefix_len")) for row in measured_infers]
    accepted_values = [v for v in accepted_values if v is not None]
    chunk_values = [safe_float(row.get("chunk_exec_len")) for row in measured_infers]
    chunk_values = [v for v in chunk_values if v is not None]
    route_summary = {
        "infer_log_files": [str(path) for path in measured_infer_files],
        "trace_files": [str(path) for path in measured_trace_files],
        "route_counts": dict(route_counts),
        "route_counts_by_task": {task: dict(counts) for task, counts in sorted(by_task_routes.items())},
        "draft_ratio": (float(route_counts.get("draft", 0)) / float(total_routes)) if total_routes else None,
        "full_ratio": (float(route_counts.get("full", 0)) / float(total_routes)) if total_routes else None,
        "accepted_prefix_len": stats(accepted_values),
        "chunk_exec_len": stats(chunk_values),
        "missing_fields": [],
    }
    for name, values in [("accepted_prefix_len", accepted_values), ("chunk_exec_len", chunk_values)]:
        if not values:
            route_summary["missing_fields"].append(name)
    (RESULTS / "stage4_route_summary.json").write_text(json.dumps(route_summary, indent=2), encoding="utf-8")

    firsts = first_infer_by_run(infers_all)
    measured_firsts = [row for name, row in firsts.items() if "stage4_libero_goal_task" in name]
    steady_infers = [
        row
        for row in measured_infers
        if not (int(row.get("episode_idx", -1)) == 0 and int(row.get("infer_id", -1)) == 0)
    ]
    warmup_first = next(iter([row for name, row in firsts.items() if "warmup" in name]), None)

    def values(rows: list[dict[str, Any]], field: str) -> list[float]:
        vals = [safe_float(row.get(field)) for row in rows]
        return [v for v in vals if v is not None]

    latency_summary = {
        "first_inference_cold_start_ms": {
            "warmup_policy_time_ms": None if warmup_first is None else safe_float(warmup_first.get("policy_time_ms")),
            "warmup_serve_time_ms": None if warmup_first is None else safe_float(warmup_first.get("serve_time_ms")),
            "warmup_client_roundtrip_ms": None if warmup_first is None else safe_float(warmup_first.get("client_roundtrip_ms")),
            "measured_run_first_policy_time_ms": values(measured_firsts, "policy_time_ms"),
            "measured_run_first_client_roundtrip_ms": values(measured_firsts, "client_roundtrip_ms"),
        },
        "steady_state_policy_time_ms": stats(values(steady_infers, "policy_time_ms")),
        "steady_state_serve_time_ms": stats(values(steady_infers, "serve_time_ms")),
        "steady_state_client_roundtrip_ms": stats(values(steady_infers, "client_roundtrip_ms")),
        "all_measured_policy_time_ms": stats(values(measured_infers, "policy_time_ms")),
        "all_measured_serve_time_ms": stats(values(measured_infers, "serve_time_ms")),
        "all_measured_client_roundtrip_ms": stats(values(measured_infers, "client_roundtrip_ms")),
        "steady_state_sample_count": len(steady_infers),
        "measured_infer_count": len(measured_infers),
        "caveat": "Stage 4 timing is preliminary and is not paper-level latency reproduction because GPU-synchronized profiling is not implemented here.",
    }
    (RESULTS / "stage4_latency_summary.json").write_text(json.dumps(latency_summary, indent=2), encoding="utf-8")

    vram_summary = parse_vram(PROJECT / "logs/stage4_gpu_monitor.csv")

    failures = []
    for row in episode_rows:
        if str(row.get("failure_mode")) != "no failure":
            failures.append(row)
    failure_summary = {
        "failure_count": len(failures),
        "failure_modes": dict(Counter(str(row.get("failure_mode")) for row in failures)),
        "failures": failures,
        "warmup_episode_count": len(warmup_episodes),
    }
    (RESULTS / "stage4_failure_summary.json").write_text(json.dumps(failure_summary, indent=2), encoding="utf-8")

    success_count = sum(1 for row in measured_episodes if bool(row.get("success")))
    completed = len(measured_episodes)
    requested = int(config.get("measured_episode_count", 30))
    comparison = {
        "is_full_paper_reproduction": False,
        "is_full_libero_benchmark": False,
        "suite": config.get("suite"),
        "tasks": tasks,
        "measured_episode_count": completed,
        "requested_measured_episode_count": requested,
        "paper_comparison_allowed": False,
        "caveats": [
            "Limited LIBERO Goal subset only.",
            "Does not cover all LIBERO suites or tasks.",
            "Does not reproduce real-world conveyor results.",
            "Latency is preliminary without GPU-synchronized profiling.",
            "Hardware and container may differ from the paper setup.",
        ],
    }
    (RESULTS / "stage4_comparison_to_paper_caveat.json").write_text(json.dumps(comparison, indent=2), encoding="utf-8")

    all_client_logs = "\n".join(read_text(PROJECT / f"logs/stage4_client_task{task}_n10.txt") for task in tasks)
    decision, decision_reason = classify_decision(
        orchestration,
        measured_episodes,
        measured_infers,
        measured_trace_files,
        read_text(PROJECT / "logs/stage4_server.txt"),
        all_client_logs,
    )

    final_decision = {
        "decision": decision,
        "decision_reason": decision_reason,
        "orchestration": orchestration,
        "episodes_requested_measured": requested,
        "episodes_completed_measured": completed,
        "success_count": success_count,
        "success_rate": (float(success_count) / float(completed)) if completed else 0.0,
        "success_rate_by_task": {str(row["task_id"]): row["success_rate"] for row in task_rows},
        "video_count_measured": len(measured_videos),
        "warmup_excluded_from_metrics": True,
        "route_summary_path": str(RESULTS / "stage4_route_summary.json"),
        "latency_summary_path": str(RESULTS / "stage4_latency_summary.json"),
        "vram_summary_path": str(RESULTS / "stage4_vram_summary.json"),
        "paper_reproduction_claimed": False,
        "full_benchmark_attempted": False,
    }
    (RESULTS / "stage4_decision.json").write_text(json.dumps(final_decision, indent=2), encoding="utf-8")
    print(json.dumps(final_decision, indent=2))


if __name__ == "__main__":
    main()
