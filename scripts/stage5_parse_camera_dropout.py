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
VIDEO_ROOT = PROJECT / "videos/stage5_camera_dropout"
RESULTS = PROJECT / "results"
CONFIG = PROJECT / "configs/stage5_camera_dropout_probe.json"
CONDITIONS = ["wrist_zero_every4", "wrist_zero_all"]
TASKS = [0, 1, 2]


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
            writer.writerow({key: row.get(key) for key in fieldnames})


def condition_from_path(path: pathlib.Path | str) -> str:
    text = str(path)
    if "stage5_sanity_clean" in text:
        return "sanity_clean"
    for condition in CONDITIONS:
        if condition in text:
            return condition
    return "unknown"


def run_name(path: pathlib.Path | str) -> str:
    for part in pathlib.Path(path).parts:
        if part.startswith("stage5_"):
            return part
    return ""


def walk_files() -> tuple[list[pathlib.Path], list[pathlib.Path], list[pathlib.Path], list[pathlib.Path]]:
    roots = [VIDEO_ROOT, RESULTS]
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
                if "stage5_" not in str(path):
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
    (RESULTS / "stage5_vram_summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def classify_failure(row: dict[str, Any]) -> str:
    if bool(row.get("success")):
        return "no failure"
    reason = str(row.get("failure_reason") or "").lower()
    if "connect" in reason or "websocket" in reason:
        return "server/client connection failure"
    if re.search(r"shape|control|action", reason):
        return "action shape/control failure"
    if re.search(r"egl|mujoco|robosuite|render|sim", reason):
        return "simulator runtime failure"
    if "gripper" in reason or "contact" in reason:
        return "gripper/contact failure"
    if row.get("_condition") in CONDITIONS:
        return "perturbation-induced perception failure"
    return "policy behavior/no success at horizon"


def baseline_data() -> dict[str, Any]:
    task_rows = read_csv(RESULTS / "stage4_task_summary.csv")
    episode_rows = read_csv(RESULTS / "stage4_episode_summary.csv")
    task_rates = {}
    for row in task_rows:
        task = str(row.get("task_id"))
        task_rates[task] = safe_float(row.get("success_rate"))
    first5 = {}
    for task in TASKS:
        subset = [
            row
            for row in episode_rows
            if str(row.get("task_id")) == str(task)
            and safe_float(row.get("episode_idx")) is not None
            and int(float(row.get("episode_idx"))) < 5
        ]
        if subset:
            success = sum(1 for row in subset if str(row.get("success")).lower() in {"true", "1", "yes"})
            first5[str(task)] = {
                "episodes": len(subset),
                "success": success,
                "success_rate": success / len(subset) if subset else None,
            }
    total_success = sum(int(float(row.get("success_count", 0) or 0)) for row in task_rows)
    total_completed = sum(int(float(row.get("episodes_completed", 0) or 0)) for row in task_rows)
    return {
        "stage4_task_success_rate": task_rates,
        "stage4_first5_by_task": first5,
        "stage4_aggregate_success_rate": total_success / total_completed if total_completed else None,
        "stage4_success_count": total_success,
        "stage4_completed": total_completed,
    }


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    config = load_json(CONFIG, default={})
    orchestration = load_json(RESULTS / "stage5_orchestration.json", default={})
    episode_logs, trace_files, infer_files, videos = walk_files()
    episodes = parse_episode_logs(episode_logs)
    infers = []
    for path in infer_files:
        infers.extend(load_jsonl(path))

    measured_episodes = [row for row in episodes if row.get("_condition") in CONDITIONS]
    measured_infers = [row for row in infers if row.get("_condition") in CONDITIONS]
    baseline = baseline_data()

    episode_rows = []
    for idx, row in enumerate(measured_episodes):
        condition = row.get("_condition")
        task = int(row.get("task_id", -1))
        success = bool(row.get("success"))
        failure_mode = classify_failure(row)
        episode_rows.append(
            {
                "condition": condition,
                "task_id": task,
                "episode_idx": row.get("episode_idx"),
                "completed": True,
                "success": success,
                "steps": row.get("env_steps_taken"),
                "infer_calls": row.get("infer_calls"),
                "failure_reason": row.get("failure_reason"),
                "failure_mode": failure_mode,
                "video_path": row.get("video_path"),
                "source": row.get("_source"),
            }
        )
    write_csv(
        RESULTS / "stage5_episode_summary.csv",
        episode_rows,
        [
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
        ],
    )

    condition_task_rows = []
    for condition in CONDITIONS:
        for task in TASKS:
            subset = [row for row in episode_rows if row["condition"] == condition and int(row["task_id"]) == task]
            completed = len(subset)
            success_count = sum(1 for row in subset if bool(row["success"]))
            rate = success_count / completed if completed else None
            base_task = baseline["stage4_task_success_rate"].get(str(task))
            base_first5 = baseline["stage4_first5_by_task"].get(str(task), {}).get("success_rate")
            condition_task_rows.append(
                {
                    "condition": condition,
                    "task_id": task,
                    "episodes_requested": 5,
                    "episodes_completed": completed,
                    "success_count": success_count,
                    "success_rate": rate,
                    "stage4_task_success_rate": base_task,
                    "stage4_first5_success_rate": base_first5,
                    "success_drop_vs_stage4": None if base_task is None or rate is None else base_task - rate,
                    "success_drop_vs_stage4_first5": None if base_first5 is None or rate is None else base_first5 - rate,
                    "main_failure_mode": Counter(row["failure_mode"] for row in subset if row["failure_mode"] != "no failure").most_common(1)[0][0]
                    if any(row["failure_mode"] != "no failure" for row in subset)
                    else "no failure",
                }
            )
    write_csv(
        RESULTS / "stage5_condition_task_summary.csv",
        condition_task_rows,
        [
            "condition",
            "task_id",
            "episodes_requested",
            "episodes_completed",
            "success_count",
            "success_rate",
            "stage4_task_success_rate",
            "stage4_first5_success_rate",
            "success_drop_vs_stage4",
            "success_drop_vs_stage4_first5",
            "main_failure_mode",
        ],
    )

    infer_rows = []
    for row in measured_infers:
        infer_rows.append(
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
                "stage5_perturb_target_key": row.get("stage5_perturb_target_key"),
                "stage5_perturb_applied": row.get("stage5_perturb_applied"),
                "stage5_perturb_query_index": row.get("stage5_perturb_query_index"),
                "stage5_perturb_mode": row.get("stage5_perturb_mode"),
                "stage5_perturb_period": row.get("stage5_perturb_period"),
                "source": row.get("_source"),
            }
        )
    write_csv(
        RESULTS / "stage5_infer_summary.csv",
        infer_rows,
        [
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
            "stage5_perturb_target_key",
            "stage5_perturb_applied",
            "stage5_perturb_query_index",
            "stage5_perturb_mode",
            "stage5_perturb_period",
            "source",
        ],
    )

    route_summary = {}
    latency_summary = {}
    missing_fields = set()
    for condition in CONDITIONS:
        rows = [row for row in measured_infers if row.get("_condition") == condition]
        counts = Counter(str(row.get("route_type", "unknown")) for row in rows)
        total = sum(counts.values())
        route_summary[condition] = {
            "route_counts": dict(counts),
            "draft_ratio": counts.get("draft", 0) / total if total else None,
            "full_ratio": counts.get("full", 0) / total if total else None,
            "accepted_prefix_len": stats(numeric(rows, "accepted_prefix_len")),
            "chunk_exec_len": stats(numeric(rows, "chunk_exec_len")),
            "perturb_applied_count": sum(1 for row in rows if bool(row.get("stage5_perturb_applied"))),
            "infer_count": len(rows),
        }
        latency_summary[condition] = {
            "policy_time_gpu_sync_ms": stats(numeric(rows, "policy_time_gpu_sync_ms")),
            "policy_time_ms": stats(numeric(rows, "policy_time_ms")),
            "serve_time_ms": stats(numeric(rows, "serve_time_ms")),
            "client_roundtrip_ms": stats(numeric(rows, "client_roundtrip_ms")),
            "sample_actions_ms": stats(numeric(rows, "sample_actions_ms")),
        }
        for key in [
            "route_type",
            "accepted_prefix_len",
            "chunk_exec_len",
            "stage5_perturb_applied",
            "client_roundtrip_ms",
        ]:
            if any(row.get(key) is None for row in rows):
                missing_fields.add(key)
        if any(row.get("policy_time_gpu_sync_ms") is None for row in rows):
            missing_fields.add("policy_time_gpu_sync_ms")
    route_payload = {
        "conditions": route_summary,
        "missing_fields": sorted(missing_fields),
        "infer_log_files": [str(p) for p in infer_files],
        "trace_file_count": len(trace_files),
    }
    (RESULTS / "stage5_route_summary.json").write_text(json.dumps(route_payload, indent=2), encoding="utf-8")
    (RESULTS / "stage5_latency_summary.json").write_text(json.dumps(latency_summary, indent=2), encoding="utf-8")

    vram = parse_vram(PROJECT / "logs/stage5_gpu_monitor.csv")

    failures = [row for row in episode_rows if row["failure_mode"] != "no failure"]
    failure_payload = {
        "failure_count": len(failures),
        "failure_types_by_condition_task": {
            f"{condition}_task{task}": dict(
                Counter(row["failure_mode"] for row in failures if row["condition"] == condition and int(row["task_id"]) == task)
            )
            for condition in CONDITIONS
            for task in TASKS
        },
        "failures": failures,
    }
    (RESULTS / "stage5_failure_summary.json").write_text(json.dumps(failure_payload, indent=2), encoding="utf-8")

    condition_aggregate = {}
    for condition in CONDITIONS:
        rows = [row for row in episode_rows if row["condition"] == condition]
        success_count = sum(1 for row in rows if bool(row["success"]))
        completed = len(rows)
        rate = success_count / completed if completed else None
        condition_aggregate[condition] = {
            "episodes_requested": 15,
            "episodes_completed": completed,
            "success_count": success_count,
            "success_rate": rate,
            "success_drop_vs_stage4_clean": None
            if rate is None or baseline["stage4_aggregate_success_rate"] is None
            else baseline["stage4_aggregate_success_rate"] - rate,
        }
    baseline_payload = {
        "stage4_clean_baseline": baseline,
        "condition_aggregate": condition_aggregate,
        "condition_task_rows": condition_task_rows,
        "route_summary_by_condition": route_summary,
        "interpretation": "Compare condition aggregate and task rows against Stage 4 clean baseline; this is a limited perturbation probe only.",
    }
    (RESULTS / "stage5_baseline_comparison.json").write_text(json.dumps(baseline_payload, indent=2), encoding="utf-8")

    server_log = read_text(PROJECT / "logs/stage5_server.txt")
    client_logs = "\n".join(read_text(PROJECT / f"logs/stage5_{condition}_task{task}_n5.txt") for condition in CONDITIONS for task in TASKS)
    completed = len(measured_episodes)
    decision = "PARTIAL_PASS_ROBUSTNESS_ANALYZABLE_LOW_SUCCESS"
    reason = "Partial robustness data was parseable."
    if load_json(RESULTS / "stage5_decision.json", {}).get("decision") == "BLOCKED_OBSERVATION_PATCH_TARGET_UNKNOWN":
        decision = "BLOCKED_OBSERVATION_PATCH_TARGET_UNKNOWN"
        reason = "Observation patch target was unknown."
    elif not orchestration.get("server_ready", True):
        decision = "BLOCKED_SERVER_NOT_READY"
        reason = "Server did not become ready."
    elif re.search(r"cuda.*out of memory|CUDA out of memory|\bOOM\b", server_log + "\n" + client_logs, re.I):
        decision = "BLOCKED_GPU_OOM"
        reason = "CUDA OOM appeared in logs."
    elif re.search(r"(error|exception|traceback).{0,160}(shape|control|action dimension|wrong.*action)", server_log + "\n" + client_logs, re.I | re.S):
        decision = "BLOCKED_ACTION_SHAPE_OR_CONTROL"
        reason = "Action shape/control error appeared in logs."
    elif completed < 15:
        decision = "BLOCKED_CLIENT_OR_ENV_RUNTIME"
        reason = "Fewer than 15 measured robustness episodes completed."
    elif measured_episodes and (not measured_infers or len(trace_files) == 0):
        decision = "BLOCKED_LOGGING_MISSING"
        reason = "Episode logs exist but infer/trace logs are missing."
    elif completed >= 25:
        decision = "PROCEED_TO_STAGE7_MINIMAL_EXTENSION"
        weak = all(abs((condition_aggregate[c]["success_drop_vs_stage4_clean"] or 0.0)) < 1e-9 for c in CONDITIONS)
        reason = "Robustness perturbation had weak measured effect." if weak else "Robustness perturbation changed measured outcomes versus Stage 4."

    decision_payload = {
        "decision": decision,
        "decision_reason": reason,
        "measured_conditions": CONDITIONS,
        "episodes_requested_measured": 30,
        "episodes_completed_measured": completed,
        "condition_aggregate": condition_aggregate,
        "missing_fields": sorted(missing_fields),
        "video_count": len([p for p in videos if condition_from_path(p) in CONDITIONS]),
        "full_benchmark_attempted": False,
        "paper_reproduction_claimed": False,
        "robustness_claim_scope": config.get("robustness_claim_scope"),
    }
    (RESULTS / "stage5_decision.json").write_text(json.dumps(decision_payload, indent=2), encoding="utf-8")
    print(json.dumps(decision_payload, indent=2))


if __name__ == "__main__":
    main()
