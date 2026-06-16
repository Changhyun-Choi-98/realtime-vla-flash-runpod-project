import json
import pathlib


PROJECT = pathlib.Path("/workspace/realtime_vla_flash_project")
OFFICIAL_DIR = PROJECT / "repos/realtime-vla-flash"
RESULTS = PROJECT / "results"
TARGET = OFFICIAL_DIR / "scripts/spec/spec_client_libero.py"

TERMS = [
    "agentview_image",
    "robot0_eye_in_hand_image",
    "observation",
    "obs",
    "policy",
    "infer",
    "query",
    "client",
    "websocket",
    "trace.jsonl",
    "infer.jsonl",
    "episode_log.json",
]


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    lines = TARGET.read_text(encoding="utf-8", errors="ignore").splitlines()
    matches = []
    for i, line in enumerate(lines, start=1):
        hits = [term for term in TERMS if term in line]
        if hits:
            matches.append({"line": i, "terms": hits, "excerpt": line.strip()[:240]})

    candidate_regions = []
    for i, line in enumerate(lines, start=1):
        if 'obs["robot0_eye_in_hand_image"]' in line or '"observation/wrist_image"' in line:
            start = max(1, i - 5)
            end = min(len(lines), i + 8)
            candidate_regions.append(
                {
                    "start_line": start,
                    "end_line": end,
                    "excerpt": [f"{j}: {lines[j-1]}" for j in range(start, end + 1)],
                }
            )
    stage6_detected = "policy_time_gpu_sync_ms" in "\n".join(lines)
    confidence = "high" if candidate_regions and stage6_detected else ("medium" if candidate_regions else "low")
    payload = {
        "target_file": str(TARGET),
        "matched_lines": matches,
        "candidate_patch_regions": candidate_regions,
        "recommended_patch_region": "After wrist image resize and before the policy request element is sent via client.infer.",
        "confidence": confidence,
        "existing_stage6_timing_patch_detected": bool(stage6_detected),
    }
    (RESULTS / "stage5_observation_audit.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
