import json
import os
import pathlib
import re
from typing import Any


PROJECT = pathlib.Path("/workspace/realtime_vla_flash_project")
OFFICIAL_DIR = PROJECT / "repos/realtime-vla-flash"
RESULTS = PROJECT / "results"

TERMS = [
    "policy_time_ms",
    "serve_time_ms",
    "sample_actions_ms",
    "client_roundtrip_ms",
    "route_type",
    "accepted_prefix_len",
    "time.perf_counter",
    "time.time",
    "torch.cuda.synchronize",
    "cuda.Event",
    "sample_actions",
    "infer.jsonl",
    "trace.jsonl",
    "episode_log.json",
]


def iter_source_files() -> list[pathlib.Path]:
    roots = [
        OFFICIAL_DIR / "scripts",
        OFFICIAL_DIR / "src",
        OFFICIAL_DIR / "packages",
        OFFICIAL_DIR / "examples",
    ]
    skip = {".git", ".venv", "__pycache__", "third_party", "checkpoints", "converted"}
    files: list[pathlib.Path] = []
    for root in roots:
        if not root.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in skip]
            for name in filenames:
                if pathlib.Path(name).suffix in {".py", ".md", ".toml", ".sh"}:
                    files.append(pathlib.Path(dirpath) / name)
    return sorted(files)


def excerpt_for_line(lines: list[str], idx: int) -> str:
    line = lines[idx].rstrip("\n")
    return line[:260]


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    matched_files: dict[str, list[dict[str, Any]]] = {}
    existing_gpu_sync_present = False
    scanned = iter_source_files()
    for path in scanned:
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            continue
        rel = str(path.relative_to(OFFICIAL_DIR))
        for idx, line in enumerate(lines):
            hits = [term for term in TERMS if term in line]
            if not hits:
                continue
            if "torch.cuda.synchronize" in line or "cuda.Event" in line:
                existing_gpu_sync_present = True
            matched_files.setdefault(rel, []).append(
                {
                    "line": idx + 1,
                    "terms": hits,
                    "excerpt": excerpt_for_line(lines, idx),
                }
            )

    server_path = OFFICIAL_DIR / "scripts/spec/spec_serve_policy.py"
    client_path = OFFICIAL_DIR / "scripts/spec/spec_client_libero.py"
    confidence = "high" if server_path.exists() and client_path.exists() else "low"
    payload = {
        "files_scanned": len(scanned),
        "matched_files": matched_files,
        "existing_gpu_sync_present": bool(existing_gpu_sync_present),
        "recommended_patch_file": [
            "scripts/spec/spec_serve_policy.py",
            "scripts/spec/spec_client_libero.py",
        ],
        "recommended_patch_function_or_region": [
            "TritonServerPolicy._run_spec_session full and draft branches",
            "TritonServerPolicy.infer sample_actions_with_timing and fallback branches",
            "spec_client_libero._make_infer_record",
        ],
        "confidence": confidence,
        "interpretation": (
            "Existing action-generation paths already use torch.cuda.synchronize in several places, "
            "but the public infer.jsonl rows do not expose explicit Stage 6 GPU-sync timing fields. "
            "Patch should preserve behavior and add policy_time_gpu_sync_ms/policy_time_wall_ms."
        ),
    }
    (RESULTS / "stage6_timing_source_audit.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
