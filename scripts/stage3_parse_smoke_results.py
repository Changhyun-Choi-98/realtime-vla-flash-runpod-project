import csv
import json
import os
import pathlib
import re
import statistics
from collections import Counter
from typing import Any


PROJECT = pathlib.Path("/workspace/realtime_vla_flash_project")
OFFICIAL_DIR = PROJECT / "repos/realtime-vla-flash"
VIDEO_ROOT = PROJECT / "videos/stage3_closed_loop_smoke"
RESULTS = PROJECT / "results"
CONFIG = PROJECT / "configs/stage3_libero_goal_task0_smoke.json"


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
        if value in {"", "N/A", "[N/A]", "nan"}:
            return None
        return float(value)
    except Exception:
        return None


def percentile(values: list[float], pct: float) -> float | None:
    values = sorted(v for v in values if isinstance(v, (int, float)))
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


def write_csv(path: pathlib.Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fieldnames})


def iter_files() -> tuple[list[pathlib.Path], list[pathlib.Path], list[pathlib.Path], list[pathlib.Path]]:
    roots = [VIDEO_ROOT, RESULTS, OFFICIAL_DIR]
    skip_names = {".git", ".venv", ".venv-libero", "__pycache__", "node_modules", "checkpoints", "converted"}
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
                if path.name == "episode_log.json":
                    episode_logs.append(path)
                elif path.name == "trace.jsonl":
                    trace_files.append(path)
                elif path.name == "infer.jsonl":
                    infer_files.append(path)
                elif path.suffix.lower() == ".mp4":
                    videos.append(path)
    return (
        sorted(set(episode_logs)),
        sorted(set(trace_files)),
        sorted(set(infer_files)),
        sorted(set(videos)),
    )


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
                        rows.append(item)
                except Exception:
                    pass
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
            if isinstance(item, dict):
                row = dict(item)
                row["_source"] = str(path)
                records.append(row)
    return records


def parse_infer_files(paths: list[pathlib.Path]) -> list[dict[str, Any]]:
    rows = []
    for path in paths:
        for item in load_jsonl(path):
            item["_source"] = str(path)
            rows.append(item)
    return rows


def parse_trace_files(paths: list[pathlib.Path]) -> list[dict[str, Any]]:
    rows = []
    for path in paths:
        for item in load_jsonl(path):
            item["_source"] = str(path)
            rows.append(item)
    return rows


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
    (RESULTS / "stage3_vram_summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def classify_decision(
    initial_decision: dict[str, Any],
    episode_records: list[dict[str, Any]],
    infer_files: list[pathlib.Path],
    trace_files: list[pathlib.Path],
    server_log: str,
    client_log: str,
) -> tuple[str, str]:
    text = f"{server_log}\n{client_log}"
    if re.search(r"cuda.*out of memory|CUDA out of memory|\\bOOM\\b", text, re.I):
        return "BLOCKED_GPU_OOM", "CUDA OOM appeared in server or client logs."
    if not initial_decision.get("server_ready"):
        return "BLOCKED_SERVER_NOT_READY_DURING_CLIENT", "Server did not reach readiness before the client."
    if initial_decision.get("client_exit_status") not in (0, None):
        if re.search(r"connect|connection|refused|websocket", client_log, re.I):
            return "BLOCKED_CLIENT_CONNECTION", "Client failed with a connection/websocket error."
        if re.search(r"shape|control|action", client_log, re.I):
            return "BLOCKED_ACTION_SHAPE_OR_CONTROL", "Client failed with an action shape/control-like error."
        if re.search(r"mujoco|robosuite|egl|osmesa|simulation|OffScreenRenderEnv", client_log, re.I):
            return "BLOCKED_ENV_RUNTIME", "Client failed with a simulator/runtime-like error."
    if episode_records:
        if not infer_files or not trace_files:
            return "BLOCKED_LOGGING_MISSING", "Episode records exist but trace/infer logs are missing."
        success_count = sum(1 for row in episode_records if bool(row.get("success")))
        if success_count >= 1:
            return "PROCEED_TO_STAGE4_LIMITED_BASELINE", "At least one episode completed successfully and logs are parseable."
        return "PARTIAL_PASS_INTEGRATION_WORKS_BUT_NO_SUCCESS", "Episode rollout completed and logs are parseable, but no episode succeeded."
    if initial_decision.get("client_exit_status") not in (0, None):
        return "BLOCKED_ENV_RUNTIME", "Client exited nonzero before a complete episode record was written."
    return "BLOCKED_LOGGING_MISSING", "Client exited without parseable episode records."


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    config = load_json(CONFIG, default={})
    initial_decision = load_json(RESULTS / "stage3_decision.json", default={})
    episode_log_files, trace_files, infer_files, videos = iter_files()
    episode_records = parse_episode_logs(episode_log_files)
    infer_records = parse_infer_files(infer_files)
    trace_records = parse_trace_files(trace_files)

    route_counts = Counter(str(row.get("route_type", "unknown")) for row in infer_records)
    flash_full_counts = {
        "draft": int(route_counts.get("draft", 0)),
        "full": int(route_counts.get("full", 0)),
    }
    accepted = [safe_float(row.get("accepted_prefix_len")) for row in infer_records]
    accepted_values = [v for v in accepted if v is not None]
    policy_times = [safe_float(row.get("policy_time_ms")) for row in infer_records]
    serve_times = [safe_float(row.get("serve_time_ms")) for row in infer_records]
    roundtrip = [safe_float(row.get("client_roundtrip_ms")) for row in infer_records]
    policy_values = [v for v in policy_times if v is not None]
    serve_values = [v for v in serve_times if v is not None]
    roundtrip_values = [v for v in roundtrip if v is not None]

    missing_fields = []
    if not accepted_values:
        missing_fields.append("accepted_prefix_len")
    if not policy_values:
        missing_fields.append("policy_time_ms")
    if not serve_values:
        missing_fields.append("serve_time_ms")
    if not roundtrip_values:
        missing_fields.append("client_roundtrip_ms")

    episode_rows = []
    for idx, row in enumerate(episode_records):
        episode_rows.append(
            {
                "episode": row.get("episode_idx", idx),
                "task_suite_name": row.get("task_suite_name"),
                "task_id": row.get("task_id"),
                "completed": True,
                "success": bool(row.get("success")),
                "steps": row.get("env_steps_taken"),
                "infer_calls": row.get("infer_calls"),
                "failure_reason": row.get("failure_reason"),
                "video_path": row.get("video_path"),
                "source": row.get("_source"),
            }
        )

    write_csv(
        RESULTS / "stage3_episode_summary.csv",
        episode_rows,
        [
            "episode",
            "task_suite_name",
            "task_id",
            "completed",
            "success",
            "steps",
            "infer_calls",
            "failure_reason",
            "video_path",
            "source",
        ],
    )

    infer_summary_rows = []
    for row in infer_records:
        infer_summary_rows.append(
            {
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
        RESULTS / "stage3_infer_summary.csv",
        infer_summary_rows,
        [
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

    route_summary = {
        "infer_log_files": [str(path) for path in infer_files],
        "trace_files": [str(path) for path in trace_files],
        "route_counts": dict(route_counts),
        "flash_full_counts": flash_full_counts,
        "accepted_prefix_len_mean": mean(accepted_values),
        "accepted_prefix_len_p50": percentile(accepted_values, 50),
        "accepted_prefix_len_p95": percentile(accepted_values, 95),
        "missing_fields": missing_fields,
    }
    (RESULTS / "stage3_route_summary.json").write_text(json.dumps(route_summary, indent=2), encoding="utf-8")

    latency_summary = {
        "server_policy_time_ms_p50": percentile(policy_values, 50),
        "server_policy_time_ms_p95": percentile(policy_values, 95),
        "serve_time_ms_p50": percentile(serve_values, 50),
        "serve_time_ms_p95": percentile(serve_values, 95),
        "client_roundtrip_ms_p50": percentile(roundtrip_values, 50),
        "client_roundtrip_ms_p95": percentile(roundtrip_values, 95),
        "sample_count": len(infer_records),
        "missing_fields": missing_fields,
        "caveat": "Stage 3 smoke timing is preliminary and not paper-level latency reproduction.",
    }
    (RESULTS / "stage3_latency_summary.json").write_text(json.dumps(latency_summary, indent=2), encoding="utf-8")

    vram_summary = parse_vram(PROJECT / "logs/stage3_gpu_monitor.csv")
    server_log = read_text(PROJECT / "logs/stage3_server.txt")
    client_log = read_text(PROJECT / "logs/stage3_client_task0_n2.txt")
    decision, decision_reason = classify_decision(initial_decision, episode_records, infer_files, trace_files, server_log, client_log)

    success_count = sum(1 for row in episode_records if bool(row.get("success")))
    episodes_completed = len(episode_records)
    episodes_requested = int(config.get("num_trials_per_task_first", 2))
    smoke_summary = {
        "suite": config.get("suite", "libero_goal"),
        "task_id": config.get("task_id", 0),
        "episodes_requested": episodes_requested,
        "episodes_completed": episodes_completed,
        "success_count": success_count,
        "success_rate": (float(success_count) / float(episodes_completed)) if episodes_completed else 0.0,
        "client_exit_status": initial_decision.get("client_exit_status"),
        "server_ready": bool(initial_decision.get("server_ready")),
        "server_alive_before_cleanup": bool(initial_decision.get("server_alive_before_cleanup")),
        "video_count": len(videos),
        "episode_log_files": [str(path) for path in episode_log_files],
        "trace_files": [str(path) for path in trace_files],
        "infer_files": [str(path) for path in infer_files],
        "failure_reason_if_any": decision_reason if decision.startswith("BLOCKED") else None,
        "decision": decision,
    }
    (RESULTS / "stage3_smoke_summary.json").write_text(json.dumps(smoke_summary, indent=2), encoding="utf-8")

    final_decision = dict(initial_decision)
    final_decision.update(
        {
            "decision": decision,
            "decision_reason": decision_reason,
            "episodes_requested": episodes_requested,
            "episodes_completed": episodes_completed,
            "success_count": success_count,
            "success_rate": smoke_summary["success_rate"],
            "video_count": len(videos),
            "episode_log_files": [str(path) for path in episode_log_files],
            "trace_files": [str(path) for path in trace_files],
            "infer_files": [str(path) for path in infer_files],
            "route_summary_path": str(RESULTS / "stage3_route_summary.json"),
            "latency_summary_path": str(RESULTS / "stage3_latency_summary.json"),
            "vram_summary_path": str(RESULTS / "stage3_vram_summary.json"),
        }
    )
    (RESULTS / "stage3_decision.json").write_text(json.dumps(final_decision, indent=2), encoding="utf-8")
    print(json.dumps(smoke_summary, indent=2))


if __name__ == "__main__":
    main()
