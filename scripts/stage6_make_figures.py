from __future__ import annotations

import csv
import json
import os
import pathlib


PROJECT = pathlib.Path("/workspace/realtime_vla_flash_project")
RESULTS = PROJECT / "results"
FIGURES = PROJECT / "figures"


try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ModuleNotFoundError:
    if os.environ.get("STAGE6_FIGURE_REEXEC") != "1":
        env_python = PROJECT / ".venv-libero/bin/python"
        if env_python.exists():
            os.environ["STAGE6_FIGURE_REEXEC"] = "1"
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


def latency_by_route_boxplot(rows: list[dict[str, str]]) -> None:
    path = FIGURES / "stage6_latency_by_route_boxplot.png"
    series = []
    labels = []
    for route in ["draft", "full"]:
        vals = [as_float(r.get("policy_time_gpu_sync_ms")) for r in rows if r.get("route_type") == route]
        vals = [v for v in vals if v is not None]
        if vals:
            series.append(vals)
            labels.append(route)
    if not series:
        save_empty(path, "Stage 6 GPU-synchronized Latency by Route")
        return
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.boxplot(series, labels=labels, showfliers=False)
    ax.set_ylabel("Milliseconds")
    ax.set_title("Stage 6 GPU-synchronized Latency by Route")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def latency_cdf(rows: list[dict[str, str]]) -> None:
    path = FIGURES / "stage6_latency_cdf.png"
    vals = [as_float(r.get("policy_time_gpu_sync_ms")) for r in rows]
    vals = sorted(v for v in vals if v is not None)
    if not vals:
        save_empty(path, "Stage 6 Latency CDF")
        return
    y = [(i + 1) / len(vals) for i in range(len(vals))]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(vals, y)
    ax.set_xlabel("GPU-synchronized policy time (ms)")
    ax.set_ylabel("CDF")
    ax.set_title("Stage 6 Latency CDF")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def accepted_prefix_hist(rows: list[dict[str, str]]) -> None:
    path = FIGURES / "stage6_accepted_prefix_hist.png"
    vals = [as_float(r.get("accepted_prefix_len")) for r in rows]
    vals = [v for v in vals if v is not None]
    if not vals:
        save_empty(path, "Stage 6 Accepted Prefix")
        return
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(vals, bins=range(0, int(max(vals)) + 3))
    ax.set_xlabel("Accepted prefix length")
    ax.set_ylabel("Inference calls")
    ax.set_title("Stage 6 Accepted Prefix Histogram")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def cold_start_vs_steady() -> None:
    path = FIGURES / "stage6_cold_start_vs_steady_state.png"
    cold = load_json(RESULTS / "stage6_cold_start_summary.json", {})
    latency = load_json(RESULTS / "stage6_latency_summary.json", {})
    warm = cold.get("warmup_first_inference", {}).get("policy_time_gpu_sync_ms")
    steady = latency.get("steady_state_excluding_first_inference_per_run", {}).get("policy_time_gpu_sync_ms", {}).get("p50")
    vals = [as_float(warm), as_float(steady)]
    if any(v is None for v in vals):
        save_empty(path, "Stage 6 Cold-start vs Steady-state")
        return
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(["warm-up first", "steady p50"], vals)
    ax.set_ylabel("Milliseconds")
    ax.set_title("Stage 6 Cold-start vs Steady-state")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def main() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    rows = read_csv(RESULTS / "stage6_infer_summary.csv")
    latency_by_route_boxplot(rows)
    latency_cdf(rows)
    accepted_prefix_hist(rows)
    cold_start_vs_steady()
    for path in [
        FIGURES / "stage6_latency_by_route_boxplot.png",
        FIGURES / "stage6_latency_cdf.png",
        FIGURES / "stage6_accepted_prefix_hist.png",
        FIGURES / "stage6_cold_start_vs_steady_state.png",
    ]:
        print(path)


if __name__ == "__main__":
    main()
