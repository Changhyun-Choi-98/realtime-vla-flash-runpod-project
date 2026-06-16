import json
import pathlib
import subprocess
import sys


PROJECT = pathlib.Path("/workspace/realtime_vla_flash_project")
OFFICIAL_DIR = PROJECT / "repos/realtime-vla-flash"
RESULTS = PROJECT / "results"
PATCHES = PROJECT / "patches"
CLIENT = OFFICIAL_DIR / "scripts/spec/spec_client_libero.py"


def replace_once(text: str, old: str, new: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected one match for patch chunk, found {count}")
    return text.replace(old, new, 1)


def patch_client() -> None:
    text = CLIENT.read_text(encoding="utf-8")
    original = text

    if "def _stage5_perturb_config" not in text:
        anchor = "\n\ndef eval_libero(args: Args) -> None:\n"
        helper = '''

def _stage5_perturb_config() -> Dict[str, Any]:
    enabled = str(__import__("os").environ.get("STAGE5_CAMERA_PERTURB", "0")).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    env = __import__("os").environ
    return {
        "enabled": bool(enabled),
        "condition": str(env.get("STAGE5_PERTURB_CONDITION", "none")),
        "target_key": str(env.get("STAGE5_PERTURB_TARGET_KEY", "robot0_eye_in_hand_image")),
        "mode": str(env.get("STAGE5_PERTURB_MODE", "none")),
        "period": int(env.get("STAGE5_PERTURB_PERIOD", "0") or 0),
        "seed": int(env.get("STAGE5_PERTURB_SEED", "7") or 7),
    }


def _stage5_apply_camera_perturb(
    *,
    obs: Dict[str, Any],
    wrist_img: np.ndarray,
    policy_query_index: int,
) -> Tuple[np.ndarray, Dict[str, Any]]:
    cfg = _stage5_perturb_config()
    info: Dict[str, Any] = {
        "stage5_perturb_enabled": bool(cfg["enabled"]),
        "stage5_perturb_condition": str(cfg["condition"]),
        "stage5_perturb_target_key": str(cfg["target_key"]),
        "stage5_perturb_applied": False,
        "stage5_perturb_query_index": int(policy_query_index),
        "stage5_perturb_mode": str(cfg["mode"]),
        "stage5_perturb_period": int(cfg["period"]),
    }
    if not cfg["enabled"]:
        return wrist_img, info
    if str(cfg["target_key"]) not in obs:
        return wrist_img, info
    mode = str(cfg["mode"])
    period = max(1, int(cfg["period"] or 1))
    apply = mode == "zero_all" or (mode == "zero_periodic" and int(policy_query_index) % period == 0)
    if not apply:
        return wrist_img, info
    info["stage5_perturb_applied"] = True
    return np.zeros_like(wrist_img), info
'''
        text = replace_once(text, anchor, helper + anchor)

    old = """                        element = {
                            "observation/image": img,
                            "observation/wrist_image": wrist_img,
"""
    new = """                        wrist_img, stage5_perturb_info = _stage5_apply_camera_perturb(
                            obs=obs,
                            wrist_img=wrist_img,
                            policy_query_index=infer_id,
                        )
                        element = {
                            "observation/image": img,
                            "observation/wrist_image": wrist_img,
"""
    if "stage5_perturb_info = _stage5_apply_camera_perturb" not in text:
        text = replace_once(text, old, new)

    old = """                            client_roundtrip_ms=client_roundtrip_ms,
                            chunk_actions=chunk_actions,
                        )
"""
    new = """                            client_roundtrip_ms=client_roundtrip_ms,
                            chunk_actions=chunk_actions,
                            stage5_perturb_info=stage5_perturb_info,
                        )
"""
    if "stage5_perturb_info=stage5_perturb_info" not in text:
        text = replace_once(text, old, new)

    old = """    client_roundtrip_ms: float,
    chunk_actions: np.ndarray,
) -> Dict[str, Any]:
"""
    new = """    client_roundtrip_ms: float,
    chunk_actions: np.ndarray,
    stage5_perturb_info: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
"""
    if "stage5_perturb_info: Optional[Dict[str, Any]]" not in text:
        text = replace_once(text, old, new)

    old = """    policy_time_ms, serve_time_ms = _policy_and_serve_time_ms(server_timing)
    return {
"""
    new = """    policy_time_ms, serve_time_ms = _policy_and_serve_time_ms(server_timing)
    perturb_info = dict(stage5_perturb_info or {})
    return {
"""
    if "perturb_info = dict(stage5_perturb_info or {})" not in text:
        text = replace_once(text, old, new)

    old = """        "chunk_actions": np.asarray(chunk_actions, dtype=np.float32).tolist(),
        "sample_actions_ms": _float_or_none(policy_timing.get("sample_actions_ms")),
"""
    new = """        "chunk_actions": np.asarray(chunk_actions, dtype=np.float32).tolist(),
        "stage5_perturb_enabled": bool(perturb_info.get("stage5_perturb_enabled", False)),
        "stage5_perturb_condition": str(perturb_info.get("stage5_perturb_condition", "none")),
        "stage5_perturb_target_key": str(perturb_info.get("stage5_perturb_target_key", "")),
        "stage5_perturb_applied": bool(perturb_info.get("stage5_perturb_applied", False)),
        "stage5_perturb_query_index": int(perturb_info.get("stage5_perturb_query_index", -1)),
        "stage5_perturb_mode": str(perturb_info.get("stage5_perturb_mode", "none")),
        "stage5_perturb_period": int(perturb_info.get("stage5_perturb_period", 0)),
        "sample_actions_ms": _float_or_none(policy_timing.get("sample_actions_ms")),
"""
    if '"stage5_perturb_enabled": bool(perturb_info.get' not in text:
        text = replace_once(text, old, new)

    old = """        "client_roundtrip_ms": infer_record.get("client_roundtrip_ms"),
        "total_ms": infer_record["total_ms"],
"""
    new = """        "client_roundtrip_ms": infer_record.get("client_roundtrip_ms"),
        "stage5_perturb_enabled": bool(infer_record.get("stage5_perturb_enabled", False)),
        "stage5_perturb_condition": str(infer_record.get("stage5_perturb_condition", "none")),
        "stage5_perturb_target_key": str(infer_record.get("stage5_perturb_target_key", "")),
        "stage5_perturb_applied": bool(infer_record.get("stage5_perturb_applied", False)),
        "stage5_perturb_query_index": int(infer_record.get("stage5_perturb_query_index", -1)),
        "stage5_perturb_mode": str(infer_record.get("stage5_perturb_mode", "none")),
        "stage5_perturb_period": int(infer_record.get("stage5_perturb_period", 0)),
        "total_ms": infer_record["total_ms"],
"""
    if '"stage5_perturb_condition": str(infer_record.get' not in text:
        text = replace_once(text, old, new)

    if text != original:
        CLIENT.write_text(text, encoding="utf-8")


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    PATCHES.mkdir(parents=True, exist_ok=True)
    audit_path = RESULTS / "stage5_observation_audit.json"
    audit = json.loads(audit_path.read_text()) if audit_path.exists() else {}
    if audit.get("confidence") not in {"high", "medium"}:
        payload = {
            "decision": "BLOCKED_OBSERVATION_PATCH_TARGET_UNKNOWN",
            "reason": "Observation patch target confidence was below medium.",
        }
        (RESULTS / "stage5_decision.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(json.dumps(payload, indent=2))
        sys.exit(1)

    patch_client()
    diff = subprocess.check_output(
        ["git", "diff", "--", "scripts/spec/spec_client_libero.py"],
        cwd=OFFICIAL_DIR,
        text=True,
    )
    (PATCHES / "stage5_client_camera_perturb.patch").write_text(diff, encoding="utf-8")
    payload = {
        "status": "patched" if "stage5_perturb" in diff else "already_patched_or_no_diff",
        "target_file": str(CLIENT),
        "patch_file": str(PATCHES / "stage5_client_camera_perturb.patch"),
        "target_image_key": "robot0_eye_in_hand_image",
        "default_behavior_unchanged": True,
        "preserved_stage6_timing_fields": "policy_time_gpu_sync_ms" in CLIENT.read_text(encoding="utf-8"),
        "added_log_fields": [
            "stage5_perturb_enabled",
            "stage5_perturb_condition",
            "stage5_perturb_target_key",
            "stage5_perturb_applied",
            "stage5_perturb_query_index",
            "stage5_perturb_mode",
            "stage5_perturb_period",
        ],
    }
    (RESULTS / "stage5_patch_status.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
