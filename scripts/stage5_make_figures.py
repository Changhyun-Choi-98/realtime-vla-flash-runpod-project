from __future__ import annotations

import csv
import json
import os
import pathlib


PROJECT = pathlib.Path("/workspace/realtime_vla_flash_project")
RESULTS = PROJECT / "results"
FIGURES = PROJECT / "figures"
CONDITIONS = ["wrist_zero_every4", "wrist_zero_all"]


try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ModuleNotFoundError:
    if os.environ.get("STAGE5_FIGURE_REEXEC") != "1":
        env_python = PROJECT / ".venv-libero/bin/python"
        if env_python.exists():
            os.environ["STAGE5_FIGURE_REEXEC"] = "1"
            os.execv(str(env_python), [str(env_python), __file__])
    raise


def read_csv(path: pathlib.Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def load_json(path: pathlib.Path, default):
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def as_float(value, default=None):
    try:
        if value in {None, ""}:
            return default
        return float(value)
    except Exception:
        return default


def save_empty(path: pathlib.Path, title: str) -> None:
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.text(0.5, 0.5, "No data available", ha="center", va="center")
    ax.set_title(title)
    ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def success_by_condition_task(rows):
    path = FIGURES / "stage5_success_by_condition_task.png"
    if not rows:
        save_empty(path, "Stage 5 Success by Condition and Task")
        return
    labels = [f"{r['condition']}\\nT{r['task_id']}" for r in rows]
    rates = [as_float(r.get("success_rate"), 0.0) for r in rows]
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.bar(range(len(labels)), rates)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Success rate")
    ax.set_title("Stage 5 Success by Condition and Task")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def success_drop(rows):
    path = FIGURES / "stage5_success_drop_vs_baseline.png"
    if not rows:
        save_empty(path, "Stage 5 Success Drop vs Stage 4")
        return
    labels = [f"{r['condition']}\\nT{r['task_id']}" for r in rows]
    drops = [as_float(r.get("success_drop_vs_stage4"), 0.0) for r in rows]
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.bar(range(len(labels)), drops)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.set_ylabel("Success-rate drop")
    ax.set_title("Stage 5 Success Drop vs Stage 4")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def accepted_prefix(infer_rows):
    path = FIGURES / "stage5_accepted_prefix_by_condition.png"
    series = []
    labels = []
    for condition in CONDITIONS:
        vals = [as_float(r.get("accepted_prefix_len")) for r in infer_rows if r.get("condition") == condition]
        vals = [v for v in vals if v is not None]
        if vals:
            series.append(vals)
            labels.append(condition)
    if not series:
        save_empty(path, "Stage 5 Accepted Prefix by Condition")
        return
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.boxplot(series, labels=labels, showfliers=False)
    ax.set_ylabel("Accepted prefix length")
    ax.set_title("Stage 5 Accepted Prefix by Condition")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def route_ratio(route_summary):
    path = FIGURES / "stage5_route_ratio_by_condition.png"
    conds = [c for c in CONDITIONS if c in route_summary.get("conditions", {})]
    if not conds:
        save_empty(path, "Stage 5 Route Ratio by Condition")
        return
    draft = [route_summary["conditions"][c].get("draft_ratio") or 0.0 for c in conds]
    full = [route_summary["conditions"][c].get("full_ratio") or 0.0 for c in conds]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(conds, draft, label="draft")
    ax.bar(conds, full, bottom=draft, label="full")
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Route ratio")
    ax.set_title("Stage 5 Route Ratio by Condition")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def latency(infer_rows):
    path = FIGURES / "stage5_latency_by_condition.png"
    series = []
    labels = []
    for condition in CONDITIONS:
        vals = [as_float(r.get("policy_time_gpu_sync_ms")) for r in infer_rows if r.get("condition") == condition]
        vals = [v for v in vals if v is not None]
        if vals:
            series.append(vals)
            labels.append(condition)
    if not series:
        save_empty(path, "Stage 5 Latency by Condition")
        return
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.boxplot(series, labels=labels, showfliers=False)
    ax.set_ylabel("policy_time_gpu_sync_ms")
    ax.set_title("Stage 5 Latency by Condition")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def main() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    task_rows = read_csv(RESULTS / "stage5_condition_task_summary.csv")
    infer_rows = read_csv(RESULTS / "stage5_infer_summary.csv")
    routes = load_json(RESULTS / "stage5_route_summary.json", {})
    success_by_condition_task(task_rows)
    success_drop(task_rows)
    accepted_prefix(infer_rows)
    route_ratio(routes)
    latency(infer_rows)
    for path in [
        FIGURES / "stage5_success_by_condition_task.png",
        FIGURES / "stage5_success_drop_vs_baseline.png",
        FIGURES / "stage5_accepted_prefix_by_condition.png",
        FIGURES / "stage5_route_ratio_by_condition.png",
        FIGURES / "stage5_latency_by_condition.png",
    ]:
        print(path)


if __name__ == "__main__":
    main()
