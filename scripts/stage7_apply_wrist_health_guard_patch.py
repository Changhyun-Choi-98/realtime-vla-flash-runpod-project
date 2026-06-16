import json
import pathlib
import subprocess
import sys


PROJECT = pathlib.Path("/workspace/realtime_vla_flash_project")
OFFICIAL_DIR = PROJECT / "repos/realtime-vla-flash"
CLIENT = OFFICIAL_DIR / "scripts/spec/spec_client_libero.py"
RESULTS = PROJECT / "results"
PATCHES = PROJECT / "patches"


def replace_once(text: str, old: str, new: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected one match for patch chunk, found {count}")
    return text.replace(old, new, 1)


def patch_client() -> None:
    text = CLIENT.read_text(encoding="utf-8")
    original = text

    if "def _stage7_guard_config" not in text:
        anchor = "\n\ndef eval_libero(args: Args) -> None:\n"
        helper = '''

def _stage7_guard_config() -> Dict[str, Any]:
    env = __import__("os").environ
    enabled = str(env.get("STAGE7_WRIST_HEALTH_GUARD", "0")).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    return {
        "enabled": bool(enabled),
        "mode": str(env.get("STAGE7_GUARD_MODE", "last_valid_cache")),
        "target_key": str(env.get("STAGE7_GUARD_TARGET_KEY", "observation/wrist_image")),
        "min_std": float(env.get("STAGE7_HEALTH_MIN_STD", "1.0") or 1.0),
        "min_range": float(env.get("STAGE7_HEALTH_MIN_RANGE", "5.0") or 5.0),
        "max_age_queries": int(env.get("STAGE7_CACHE_MAX_AGE_QUERIES", "8") or 8),
        "reset_per_episode": str(env.get("STAGE7_CACHE_RESET_PER_EPISODE", "1")).strip().lower()
        in {"1", "true", "yes", "on"},
    }


def _stage7_empty_guard_state() -> Dict[str, Any]:
    return {
        "last_valid_wrist_image": None,
        "last_valid_query_index": None,
    }


def _stage7_apply_wrist_health_guard(
    *,
    wrist_img: np.ndarray,
    policy_query_index: int,
    guard_state: Dict[str, Any],
) -> Tuple[np.ndarray, Dict[str, Any]]:
    cfg = _stage7_guard_config()
    arr = np.asarray(wrist_img)
    value_range = float(arr.max() - arr.min()) if arr.size else 0.0
    std = float(arr.std()) if arr.size else 0.0
    mean = float(arr.mean()) if arr.size else 0.0
    healthy = bool(std >= float(cfg["min_std"]) and value_range >= float(cfg["min_range"]))
    last_valid = guard_state.get("last_valid_wrist_image")
    last_idx = guard_state.get("last_valid_query_index")
    cache_available = last_valid is not None and last_idx is not None
    cache_age = int(policy_query_index - int(last_idx)) if cache_available else -1
    info: Dict[str, Any] = {
        "stage7_guard_enabled": bool(cfg["enabled"]),
        "stage7_guard_mode": str(cfg["mode"]),
        "stage7_guard_target_key": str(cfg["target_key"]),
        "stage7_wrist_health_mean": mean,
        "stage7_wrist_health_std": std,
        "stage7_wrist_health_range": value_range,
        "stage7_wrist_healthy": healthy,
        "stage7_cache_available": bool(cache_available),
        "stage7_cache_age_queries": int(cache_age),
        "stage7_cache_hit": False,
        "stage7_cache_miss": False,
        "stage7_image_replaced": False,
        "stage7_cache_updated": False,
        "stage7_guard_query_index": int(policy_query_index),
        "stage7_guard_note": "disabled",
    }
    if not cfg["enabled"]:
        return wrist_img, info
    if str(cfg["mode"]) != "last_valid_cache":
        info["stage7_guard_note"] = "unsupported_mode"
        return wrist_img, info
    if healthy:
        guard_state["last_valid_wrist_image"] = np.array(wrist_img, copy=True)
        guard_state["last_valid_query_index"] = int(policy_query_index)
        info["stage7_cache_updated"] = True
        info["stage7_cache_available"] = True
        info["stage7_cache_age_queries"] = 0
        info["stage7_guard_note"] = "healthy_cache_updated"
        return wrist_img, info
    if cache_available and cache_age <= int(cfg["max_age_queries"]):
        info["stage7_cache_hit"] = True
        info["stage7_image_replaced"] = True
        info["stage7_guard_note"] = "unhealthy_replaced_from_cache"
        return np.array(last_valid, copy=True), info
    info["stage7_cache_miss"] = True
    info["stage7_guard_note"] = "unhealthy_no_valid_cache"
    return wrist_img, info
'''
        text = replace_once(text, anchor, helper + anchor)

    old = """            episode_trace: List[Dict[str, Any]] = []
            episode_infers: List[Dict[str, Any]] = []

            executed_steps = 0
"""
    new = """            episode_trace: List[Dict[str, Any]] = []
            episode_infers: List[Dict[str, Any]] = []
            stage7_guard_state = _stage7_empty_guard_state()

            executed_steps = 0
"""
    if "stage7_guard_state = _stage7_empty_guard_state()" not in text:
        text = replace_once(text, old, new)

    old = """                        wrist_img, stage5_perturb_info = _stage5_apply_camera_perturb(
                            obs=obs,
                            wrist_img=wrist_img,
                            policy_query_index=infer_id,
                        )
                        element = {
"""
    new = """                        wrist_img, stage5_perturb_info = _stage5_apply_camera_perturb(
                            obs=obs,
                            wrist_img=wrist_img,
                            policy_query_index=infer_id,
                        )
                        wrist_img, stage7_guard_info = _stage7_apply_wrist_health_guard(
                            wrist_img=wrist_img,
                            policy_query_index=infer_id,
                            guard_state=stage7_guard_state,
                        )
                        element = {
"""
    if "stage7_guard_info = _stage7_apply_wrist_health_guard" not in text:
        text = replace_once(text, old, new)

    old = """                            chunk_actions=chunk_actions,
                            stage5_perturb_info=stage5_perturb_info,
                        )
"""
    new = """                            chunk_actions=chunk_actions,
                            stage5_perturb_info=stage5_perturb_info,
                            stage7_guard_info=stage7_guard_info,
                        )
"""
    if "stage7_guard_info=stage7_guard_info" not in text:
        text = replace_once(text, old, new)

    old = """    chunk_actions: np.ndarray,
    stage5_perturb_info: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
"""
    new = """    chunk_actions: np.ndarray,
    stage5_perturb_info: Optional[Dict[str, Any]] = None,
    stage7_guard_info: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
"""
    if "stage7_guard_info: Optional[Dict[str, Any]]" not in text:
        text = replace_once(text, old, new)

    old = """    policy_time_ms, serve_time_ms = _policy_and_serve_time_ms(server_timing)
    perturb_info = dict(stage5_perturb_info or {})
    return {
"""
    new = """    policy_time_ms, serve_time_ms = _policy_and_serve_time_ms(server_timing)
    perturb_info = dict(stage5_perturb_info or {})
    guard_info = dict(stage7_guard_info or {})
    return {
"""
    if "guard_info = dict(stage7_guard_info or {})" not in text:
        text = replace_once(text, old, new)

    old = """        "stage5_perturb_period": int(perturb_info.get("stage5_perturb_period", 0)),
        "sample_actions_ms": _float_or_none(policy_timing.get("sample_actions_ms")),
"""
    new = """        "stage5_perturb_period": int(perturb_info.get("stage5_perturb_period", 0)),
        "stage7_guard_enabled": bool(guard_info.get("stage7_guard_enabled", False)),
        "stage7_guard_mode": str(guard_info.get("stage7_guard_mode", "")),
        "stage7_guard_target_key": str(guard_info.get("stage7_guard_target_key", "")),
        "stage7_wrist_health_mean": _float_or_none(guard_info.get("stage7_wrist_health_mean")),
        "stage7_wrist_health_std": _float_or_none(guard_info.get("stage7_wrist_health_std")),
        "stage7_wrist_health_range": _float_or_none(guard_info.get("stage7_wrist_health_range")),
        "stage7_wrist_healthy": bool(guard_info.get("stage7_wrist_healthy", False)),
        "stage7_cache_available": bool(guard_info.get("stage7_cache_available", False)),
        "stage7_cache_age_queries": int(guard_info.get("stage7_cache_age_queries", -1)),
        "stage7_cache_hit": bool(guard_info.get("stage7_cache_hit", False)),
        "stage7_cache_miss": bool(guard_info.get("stage7_cache_miss", False)),
        "stage7_image_replaced": bool(guard_info.get("stage7_image_replaced", False)),
        "stage7_cache_updated": bool(guard_info.get("stage7_cache_updated", False)),
        "stage7_guard_query_index": int(guard_info.get("stage7_guard_query_index", -1)),
        "stage7_guard_note": str(guard_info.get("stage7_guard_note", "")),
        "sample_actions_ms": _float_or_none(policy_timing.get("sample_actions_ms")),
"""
    if '"stage7_guard_enabled": bool(guard_info.get' not in text:
        text = replace_once(text, old, new)

    old = """        "stage5_perturb_period": int(infer_record.get("stage5_perturb_period", 0)),
        "total_ms": infer_record["total_ms"],
"""
    new = """        "stage5_perturb_period": int(infer_record.get("stage5_perturb_period", 0)),
        "stage7_guard_enabled": bool(infer_record.get("stage7_guard_enabled", False)),
        "stage7_guard_mode": str(infer_record.get("stage7_guard_mode", "")),
        "stage7_guard_target_key": str(infer_record.get("stage7_guard_target_key", "")),
        "stage7_wrist_health_mean": infer_record.get("stage7_wrist_health_mean"),
        "stage7_wrist_health_std": infer_record.get("stage7_wrist_health_std"),
        "stage7_wrist_health_range": infer_record.get("stage7_wrist_health_range"),
        "stage7_wrist_healthy": bool(infer_record.get("stage7_wrist_healthy", False)),
        "stage7_cache_available": bool(infer_record.get("stage7_cache_available", False)),
        "stage7_cache_age_queries": int(infer_record.get("stage7_cache_age_queries", -1)),
        "stage7_cache_hit": bool(infer_record.get("stage7_cache_hit", False)),
        "stage7_cache_miss": bool(infer_record.get("stage7_cache_miss", False)),
        "stage7_image_replaced": bool(infer_record.get("stage7_image_replaced", False)),
        "stage7_cache_updated": bool(infer_record.get("stage7_cache_updated", False)),
        "stage7_guard_query_index": int(infer_record.get("stage7_guard_query_index", -1)),
        "stage7_guard_note": str(infer_record.get("stage7_guard_note", "")),
        "total_ms": infer_record["total_ms"],
"""
    if '"stage7_guard_enabled": bool(infer_record.get' not in text:
        text = replace_once(text, old, new)

    if text != original:
        CLIENT.write_text(text, encoding="utf-8")


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    PATCHES.mkdir(parents=True, exist_ok=True)
    audit_path = RESULTS / "stage7_client_patch_audit.json"
    audit = json.loads(audit_path.read_text()) if audit_path.exists() else {}
    if audit.get("confidence") not in {"high", "medium"} or not audit.get("anti_cheating_order_possible"):
        payload = {
            "decision": "BLOCKED_GUARD_PATCH_TARGET_UNKNOWN",
            "reason": "Patch target confidence was below medium or anti-cheating order was not available.",
        }
        (RESULTS / "stage7_decision.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(json.dumps(payload, indent=2))
        sys.exit(1)

    patch_client()
    diff = subprocess.check_output(
        ["git", "diff", "--", "scripts/spec/spec_client_libero.py"],
        cwd=OFFICIAL_DIR,
        text=True,
    )
    patch_path = PATCHES / "stage7_wrist_health_guard.patch"
    patch_path.write_text(diff, encoding="utf-8")
    client_text = CLIENT.read_text(encoding="utf-8")
    payload = {
        "status": "patched" if "stage7_guard" in diff else "already_patched_or_no_diff",
        "target_file": str(CLIENT),
        "patch_file": str(patch_path),
        "extension_name": "WristHealthGuard",
        "guard_target_key": "observation/wrist_image",
        "default_behavior_unchanged": True,
        "stage5_patch_preserved": "stage5_perturb_info" in client_text,
        "stage6_patch_preserved": "policy_time_gpu_sync_ms" in client_text,
        "anti_cheating_order": "stage5 dropout before stage7 guard before policy request",
        "added_log_fields": [
            "stage7_guard_enabled",
            "stage7_guard_mode",
            "stage7_guard_target_key",
            "stage7_wrist_health_mean",
            "stage7_wrist_health_std",
            "stage7_wrist_health_range",
            "stage7_wrist_healthy",
            "stage7_cache_available",
            "stage7_cache_age_queries",
            "stage7_cache_hit",
            "stage7_cache_miss",
            "stage7_image_replaced",
            "stage7_cache_updated",
            "stage7_guard_query_index",
            "stage7_guard_note",
        ],
    }
    (RESULTS / "stage7_patch_status.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
