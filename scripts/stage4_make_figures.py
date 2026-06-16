import csv
import json
import os
import pathlib
import sys


PROJECT = pathlib.Path("/workspace/realtime_vla_flash_project")
RESULTS = PROJECT / "results"
FIGURES = PROJECT / "figures"


try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ModuleNotFoundError:
    if os.environ.get("STAGE4_FIGURE_REEXEC") != "1":
        env_python = PROJECT / ".venv-libero/bin/python"
        if env_python.exists():
            os.environ["STAGE4_FIGURE_REEXEC"] = "1"
            os.execv(str(env_python), [str(env_python), __file__])
    raise


def read_csv(path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def load_json(path, default):
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def as_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def save_empty(path, title):
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.text(0.5, 0.5, "No data available", ha="center", va="center")
    ax.set_title(title)
    ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def success_by_task(task_rows):
    path = FIGURES / "stage4_success_by_task.png"
    if not task_rows:
        save_empty(path, "Stage 4 Success by Task")
        return
    tasks = [str(row.get("task_id")) for row in task_rows]
    rates = [as_float(row.get("success_rate")) for row in task_rows]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(tasks, rates)
    ax.set_ylim(0, 1.05)
    ax.set_xlabel("Task ID")
    ax.set_ylabel("Success rate")
    ax.set_title("Stage 4 Success by Task")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def latency_boxplot(infer_rows):
    path = FIGURES / "stage4_latency_boxplot.png"
    if not infer_rows:
        save_empty(path, "Stage 4 Steady-state Latency")
        return
    steady = [row for row in infer_rows if not (str(row.get("episode_idx")) == "0" and str(row.get("infer_id")) == "0")]
    series = [
        [as_float(row.get("policy_time_ms"), None) for row in steady],
        [as_float(row.get("serve_time_ms"), None) for row in steady],
        [as_float(row.get("client_roundtrip_ms"), None) for row in steady],
    ]
    series = [[v for v in values if v is not None] for values in series]
    if not any(series):
        save_empty(path, "Stage 4 Steady-state Latency")
        return
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.boxplot(series, labels=["policy", "serve", "roundtrip"], showfliers=False)
    ax.set_ylabel("Milliseconds")
    ax.set_title("Stage 4 Steady-state Latency")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def accepted_prefix_hist(infer_rows):
    path = FIGURES / "stage4_accepted_prefix_hist.png"
    values = [as_float(row.get("accepted_prefix_len"), None) for row in infer_rows]
    values = [v for v in values if v is not None]
    if not values:
        save_empty(path, "Stage 4 Accepted Prefix")
        return
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(values, bins=range(0, int(max(values)) + 3))
    ax.set_xlabel("Accepted prefix length")
    ax.set_ylabel("Inference calls")
    ax.set_title("Stage 4 Accepted Prefix Histogram")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def route_ratio_by_task(route_summary):
    path = FIGURES / "stage4_route_ratio_by_task.png"
    by_task = route_summary.get("route_counts_by_task", {})
    if not by_task:
        save_empty(path, "Stage 4 Route Ratio by Task")
        return
    tasks = sorted(by_task.keys(), key=lambda x: int(x) if str(x).isdigit() else str(x))
    draft = []
    full = []
    for task in tasks:
        counts = by_task.get(task, {})
        total = float(sum(int(v) for v in counts.values())) or 1.0
        draft.append(float(counts.get("draft", 0)) / total)
        full.append(float(counts.get("full", 0)) / total)
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(tasks, draft, label="draft")
    ax.bar(tasks, full, bottom=draft, label="full")
    ax.set_ylim(0, 1.05)
    ax.set_xlabel("Task ID")
    ax.set_ylabel("Route ratio")
    ax.set_title("Stage 4 Route Ratio by Task")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def main():
    FIGURES.mkdir(parents=True, exist_ok=True)
    task_rows = read_csv(RESULTS / "stage4_task_summary.csv")
    infer_rows = read_csv(RESULTS / "stage4_infer_summary.csv")
    route_summary = load_json(RESULTS / "stage4_route_summary.json", {})
    success_by_task(task_rows)
    latency_boxplot(infer_rows)
    accepted_prefix_hist(infer_rows)
    route_ratio_by_task(route_summary)
    for path in [
        FIGURES / "stage4_success_by_task.png",
        FIGURES / "stage4_latency_boxplot.png",
        FIGURES / "stage4_accepted_prefix_hist.png",
        FIGURES / "stage4_route_ratio_by_task.png",
    ]:
        print(path)


if __name__ == "__main__":
    main()
