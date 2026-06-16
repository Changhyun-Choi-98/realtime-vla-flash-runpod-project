from __future__ import annotations

import csv
import json
import pathlib
import subprocess
import sys


PROJECT = pathlib.Path("/workspace/realtime_vla_flash_project")
RESULTS = PROJECT / "results"
FIGURES = PROJECT / "figures"


def ensure_matplotlib():
    try:
        import matplotlib.pyplot as plt  # type: ignore

        return plt
    except Exception:
        py = PROJECT / ".venv-libero/bin/python"
        if py.exists() and pathlib.Path(sys.executable) != py:
            subprocess.check_call([str(py), __file__])
            raise SystemExit(0)
        raise


def read_csv(path: pathlib.Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def f(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def load_json(path: pathlib.Path):
    return json.loads(path.read_text()) if path.exists() else {}


def save(fig, name: str) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    path = FIGURES / name
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    print(path)


def main() -> None:
    plt = ensure_matplotlib()
    task_rows = read_csv(RESULTS / "stage7_condition_task_summary.csv")
    infer_rows = read_csv(RESULTS / "stage7_infer_summary.csv")
    guard = load_json(RESULTS / "stage7_guard_summary.json").get("conditions", {})
    route = load_json(RESULTS / "stage7_route_summary.json").get("conditions", {})
    latency = load_json(RESULTS / "stage7_latency_summary.json")

    labels = [f"{r['condition']} t{r['task_id']}" for r in task_rows]
    rates = [f(r.get("success_rate")) for r in task_rows]
    prev = [f(r.get("stage5_no_guard_success_rate")) for r in task_rows]
    x = list(range(len(labels)))
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.bar([i - 0.18 for i in x], prev, width=0.36, label="Stage 5 no guard")
    ax.bar([i + 0.18 for i in x], rates, width=0.36, label="Stage 7 guard")
    ax.set_ylabel("success rate")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=35, ha="right")
    ax.set_ylim(0, 1.05)
    ax.legend()
    save(fig, "stage7_success_recovery_vs_stage5.png")
    plt.close(fig)

    conds = list(guard)
    hit_rates = [guard[c].get("guard_cache_hit_rate") or 0 for c in conds]
    replacement_rates = [guard[c].get("guard_replacement_rate") or 0 for c in conds]
    fig, ax = plt.subplots(figsize=(7, 4))
    x = list(range(len(conds)))
    ax.bar([i - 0.18 for i in x], hit_rates, width=0.36, label="cache hit")
    ax.bar([i + 0.18 for i in x], replacement_rates, width=0.36, label="replacement")
    ax.set_ylabel("rate per inference")
    ax.set_xticks(x)
    ax.set_xticklabels(conds, rotation=20, ha="right")
    ax.legend()
    save(fig, "stage7_guard_cache_hit_rate.png")
    plt.close(fig)

    stage5_route = load_json(RESULTS / "stage5_route_summary.json").get("conditions", {})
    fig, ax = plt.subplots(figsize=(7, 4))
    labels = []
    means = []
    for c in ["wrist_zero_every4", "guard_wrist_zero_every4", "wrist_zero_all", "guard_wrist_zero_all"]:
        source = stage5_route if c.startswith("wrist_") else route
        labels.append(c)
        means.append((source.get(c, {}).get("accepted_prefix_len", {}) or {}).get("mean") or 0)
    ax.bar(labels, means)
    ax.set_ylabel("accepted prefix mean")
    ax.tick_params(axis="x", rotation=25)
    save(fig, "stage7_accepted_prefix_guard_vs_no_guard.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4))
    labels = []
    full = []
    draft = []
    for c in ["guard_wrist_zero_every4", "guard_wrist_zero_all"]:
        labels.append(c)
        full.append((route.get(c, {}) or {}).get("full_ratio") or 0)
        draft.append((route.get(c, {}) or {}).get("draft_ratio") or 0)
    x = list(range(len(labels)))
    ax.bar([i - 0.18 for i in x], draft, width=0.36, label="draft")
    ax.bar([i + 0.18 for i in x], full, width=0.36, label="full")
    ax.set_ylabel("route ratio")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20, ha="right")
    ax.legend()
    save(fig, "stage7_route_ratio_guard_vs_no_guard.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4))
    labels = list(latency)
    p50 = [(latency[c].get("policy_time_gpu_sync_ms", {}) or {}).get("p50") or 0 for c in labels]
    p95 = [(latency[c].get("policy_time_gpu_sync_ms", {}) or {}).get("p95") or 0 for c in labels]
    x = list(range(len(labels)))
    ax.bar([i - 0.18 for i in x], p50, width=0.36, label="p50")
    ax.bar([i + 0.18 for i in x], p95, width=0.36, label="p95")
    ax.set_ylabel("policy_time_gpu_sync_ms")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20, ha="right")
    ax.legend()
    save(fig, "stage7_latency_guard_vs_no_guard.png")
    plt.close(fig)


if __name__ == "__main__":
    main()
