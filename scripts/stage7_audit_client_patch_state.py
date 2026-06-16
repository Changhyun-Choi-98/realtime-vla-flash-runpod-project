import json
import pathlib
import re


PROJECT = pathlib.Path("/workspace/realtime_vla_flash_project")
OFFICIAL_DIR = PROJECT / "repos/realtime-vla-flash"
TARGET = OFFICIAL_DIR / "scripts/spec/spec_client_libero.py"
RESULTS = PROJECT / "results"


PATTERNS = [
    "STAGE5_CAMERA_PERTURB",
    "stage5_perturb_enabled",
    "robot0_eye_in_hand_image",
    "observation/wrist_image",
    "policy_time_gpu_sync_ms",
    "client_roundtrip_ms",
    "infer.jsonl",
    "trace.jsonl",
    "episode_log.json",
    "stage5_perturb_info = _stage5_apply_camera_perturb",
    "element = {",
]


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    text = TARGET.read_text(encoding="utf-8")
    lines = text.splitlines()
    matched = []
    for i, line in enumerate(lines, start=1):
        if any(pattern in line for pattern in PATTERNS):
            matched.append({"line": i, "text": line.rstrip()})

    stage5 = "stage5_perturb_info = _stage5_apply_camera_perturb" in text and "stage5_perturb_enabled" in text
    stage6 = "policy_time_gpu_sync_ms" in text and "timing_patch_stage" in text
    region = None
    confidence = "low"
    anti_cheating_possible = False
    for i, line in enumerate(lines, start=1):
        if "stage5_perturb_info = _stage5_apply_camera_perturb" in line:
            window = "\n".join(lines[i - 1 : i + 12])
            if '"observation/wrist_image": wrist_img' in window:
                region = {
                    "after": "wrist_img, stage5_perturb_info = _stage5_apply_camera_perturb(...)",
                    "before": "element = { ... 'observation/wrist_image': wrist_img ... }",
                    "line": i,
                }
                confidence = "high"
                anti_cheating_possible = True
            break

    payload = {
        "target_file": str(TARGET),
        "stage5_patch_detected": bool(stage5),
        "stage6_timing_patch_detected": bool(stage6),
        "recommended_insert_region": region,
        "confidence": confidence,
        "anti_cheating_order_possible": bool(anti_cheating_possible),
        "matched_lines": matched,
    }
    out = RESULTS / "stage7_client_patch_audit.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
