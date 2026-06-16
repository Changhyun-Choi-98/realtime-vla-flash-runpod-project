import json
import pathlib
import subprocess
import sys


PROJECT = pathlib.Path("/workspace/realtime_vla_flash_project")
OFFICIAL_DIR = PROJECT / "repos/realtime-vla-flash"
RESULTS = PROJECT / "results"
PATCHES = PROJECT / "patches"
SERVER = OFFICIAL_DIR / "scripts/spec/spec_serve_policy.py"
CLIENT = OFFICIAL_DIR / "scripts/spec/spec_client_libero.py"


SERVER_ANCHOR = """    def _run_spec_session(
"""


def replace_once(text: str, old: str, new: str, *, path: pathlib.Path) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected one match in {path} for patch chunk, found {count}")
    return text.replace(old, new, 1)


def ensure_helpers(text: str) -> str:
    if "def _stage6_sync_profile_enabled" in text:
        return text
    helper = '''
    @staticmethod
    def _stage6_sync_profile_enabled() -> bool:
        return os.environ.get("STAGE6_SYNC_PROFILE", "").strip().lower() in {"1", "true", "yes", "on"}

    def _stage6_sync_if_needed(self) -> bool:
        if self._stage6_sync_profile_enabled() and torch.cuda.is_available() and self._device.startswith("cuda"):
            torch.cuda.synchronize()
            return True
        return False

    @staticmethod
    def _stage6_add_sync_timing(timing: dict[str, Any], *, sync_ms: float, wall_ms: float, sync_used: bool) -> None:
        if not TritonServerPolicy._stage6_sync_profile_enabled():
            return
        timing["policy_time_gpu_sync_ms"] = float(sync_ms)
        timing["policy_time_wall_ms"] = float(wall_ms)
        timing["gpu_sync_before_after_used"] = 1.0 if sync_used else 0.0
        timing["timing_patch_stage"] = "stage6"
        timing["timing_patch_note"] = "torch.cuda.synchronize before and after server-side action generation when CUDA is available"

'''
    return replace_once(text, SERVER_ANCHOR, helper + SERVER_ANCHOR, path=SERVER)


def patch_server() -> None:
    text = SERVER.read_text(encoding="utf-8")
    original = text
    text = ensure_helpers(text)

    old = """        if torch.cuda.is_available() and self._device.startswith("cuda"):
            torch.cuda.synchronize()
        t0 = time.perf_counter()
        stage_timing: dict[str, float] = {}
"""
    new = """        sync_used = self._stage6_sync_if_needed()
        if not sync_used and torch.cuda.is_available() and self._device.startswith("cuda"):
            torch.cuda.synchronize()
        t0 = time.perf_counter()
        stage_timing: dict[str, float] = {}
"""
    text = replace_once(text, old, new, path=SERVER)

    old = """        if torch.cuda.is_available() and self._device.startswith("cuda"):
            torch.cuda.synchronize()
        return actions, (time.perf_counter() - t0) * 1000.0, stage_timing
"""
    new = """        if sync_used:
            self._stage6_sync_if_needed()
        elif torch.cuda.is_available() and self._device.startswith("cuda"):
            torch.cuda.synchronize()
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        self._stage6_add_sync_timing(
            stage_timing,
            sync_ms=elapsed_ms,
            wall_ms=elapsed_ms,
            sync_used=sync_used or (torch.cuda.is_available() and self._device.startswith("cuda")),
        )
        return actions, elapsed_ms, stage_timing
"""
    text = replace_once(text, old, new, path=SERVER)

    old = """        if torch.cuda.is_available() and self._device.startswith("cuda"):
            torch.cuda.synchronize()
        t0 = time.perf_counter()

        prepared = session.prepare_observation(images=images, state=state)
"""
    new = """        sync_used = self._stage6_sync_if_needed()
        if not sync_used and torch.cuda.is_available() and self._device.startswith("cuda"):
            torch.cuda.synchronize()
        t0 = time.perf_counter()

        prepared = session.prepare_observation(images=images, state=state)
"""
    text = replace_once(text, old, new, path=SERVER)

    old = """            outputs["accepted_prefix_len"] = accepted_prefix_len
            sample_actions_ms = (time.perf_counter() - t0) * 1000.0
            timing = {
                "sample_actions_ms": float(sample_actions_ms),
                "encoder_ms": float(stage_timing.get("encoder_ms", float("nan"))),
            }
"""
    new = """            outputs["accepted_prefix_len"] = accepted_prefix_len
            if sync_used:
                self._stage6_sync_if_needed()
            sample_actions_ms = (time.perf_counter() - t0) * 1000.0
            timing = {
                "sample_actions_ms": float(sample_actions_ms),
                "encoder_ms": float(stage_timing.get("encoder_ms", float("nan"))),
            }
            self._stage6_add_sync_timing(
                timing,
                sync_ms=sample_actions_ms,
                wall_ms=sample_actions_ms,
                sync_used=sync_used,
            )
"""
    text = replace_once(text, old, new, path=SERVER)

    old = """        outputs = self._format_outputs(transformed=transformed, actions=x0_out)
        accepted_prefix_len_scalar = float(accepted_prefix_len.to(dtype=torch.float32).mean().item())
        outputs["accepted_prefix_len"] = int(round(accepted_prefix_len_scalar))
        sample_actions_ms = (time.perf_counter() - t0) * 1000.0
        encoder_ms = float(draft_timing.get("encoder_ms", float("nan")))
"""
    new = """        outputs = self._format_outputs(transformed=transformed, actions=x0_out)
        accepted_prefix_len_scalar = float(accepted_prefix_len.to(dtype=torch.float32).mean().item())
        outputs["accepted_prefix_len"] = int(round(accepted_prefix_len_scalar))
        if sync_used:
            self._stage6_sync_if_needed()
        sample_actions_ms = (time.perf_counter() - t0) * 1000.0
        encoder_ms = float(draft_timing.get("encoder_ms", float("nan")))
"""
    text = replace_once(text, old, new, path=SERVER)

    old = """            "route_type": "draft",
        }
        _set_legacy_timing_compat_fields(timing)
"""
    new = """            "route_type": "draft",
        }
        self._stage6_add_sync_timing(
            timing,
            sync_ms=sample_actions_ms,
            wall_ms=sample_actions_ms,
            sync_used=sync_used,
        )
        _set_legacy_timing_compat_fields(timing)
"""
    text = replace_once(text, old, new, path=SERVER)

    old = """        if hasattr(self._runtime_pool, "sample_actions_with_timing"):
            if torch.cuda.is_available() and self._device.startswith("cuda"):
                torch.cuda.synchronize()
            t0 = time.perf_counter()
"""
    new = """        if hasattr(self._runtime_pool, "sample_actions_with_timing"):
            sync_used = self._stage6_sync_if_needed()
            if not sync_used and torch.cuda.is_available() and self._device.startswith("cuda"):
                torch.cuda.synchronize()
            t0 = time.perf_counter()
"""
    text = replace_once(text, old, new, path=SERVER)

    old = """            if torch.cuda.is_available() and self._device.startswith("cuda"):
                torch.cuda.synchronize()
            sample_actions_ms = (time.perf_counter() - t0) * 1000.0
            outputs = self._format_outputs(transformed=transformed, actions=self._as_action_batch(actions))
"""
    new = """            if sync_used:
                self._stage6_sync_if_needed()
            elif torch.cuda.is_available() and self._device.startswith("cuda"):
                torch.cuda.synchronize()
            sample_actions_ms = (time.perf_counter() - t0) * 1000.0
            outputs = self._format_outputs(transformed=transformed, actions=self._as_action_batch(actions))
"""
    text = replace_once(text, old, new, path=SERVER)

    old = """            policy_timing = {
                "sample_actions_ms": float(sample_actions_ms),
                **stage_timing,
            }
"""
    new = """            policy_timing = {
                "sample_actions_ms": float(sample_actions_ms),
                **stage_timing,
            }
            self._stage6_add_sync_timing(
                policy_timing,
                sync_ms=sample_actions_ms,
                wall_ms=sample_actions_ms,
                sync_used=sync_used or (torch.cuda.is_available() and self._device.startswith("cuda")),
            )
"""
    text = replace_once(text, old, new, path=SERVER)

    old = """        outputs["policy_timing"] = {
            "sample_actions_ms": float(sample_actions_ms),
            "encoder_ms": float(stage_timing.get("encoder_ms", float("nan"))),
"""
    new = """        policy_timing = {
            "sample_actions_ms": float(sample_actions_ms),
            "encoder_ms": float(stage_timing.get("encoder_ms", float("nan"))),
"""
    text = replace_once(text, old, new, path=SERVER)

    old = """            "route_type": "full",
        }
        self._log_response(outputs)
        return outputs
"""
    new = """            "route_type": "full",
        }
        self._stage6_add_sync_timing(
            policy_timing,
            sync_ms=float(sample_actions_ms),
            wall_ms=float(sample_actions_ms),
            sync_used=bool(policy_timing.get("gpu_sync_before_after_used", 0.0)) or (torch.cuda.is_available() and self._device.startswith("cuda")),
        )
        outputs["policy_timing"] = policy_timing
        self._log_response(outputs)
        return outputs
"""
    text = replace_once(text, old, new, path=SERVER)

    if text != original:
        SERVER.write_text(text, encoding="utf-8")


def patch_client() -> None:
    text = CLIENT.read_text(encoding="utf-8")
    original = text
    old = """        "sample_actions_ms": _float_or_none(policy_timing.get("sample_actions_ms")),
        "policy_time_ms": policy_time_ms,
        "serve_time_ms": serve_time_ms,
"""
    new = """        "sample_actions_ms": _float_or_none(policy_timing.get("sample_actions_ms")),
        "policy_time_gpu_sync_ms": _float_or_none(policy_timing.get("policy_time_gpu_sync_ms")),
        "policy_time_wall_ms": _float_or_none(policy_timing.get("policy_time_wall_ms")),
        "gpu_sync_before_after_used": int(round(float(policy_timing.get("gpu_sync_before_after_used", 0.0)))),
        "timing_patch_stage": str(policy_timing.get("timing_patch_stage", "")),
        "timing_patch_note": str(policy_timing.get("timing_patch_note", "")),
        "policy_time_ms": policy_time_ms,
        "serve_time_ms": serve_time_ms,
"""
    text = replace_once(text, old, new, path=CLIENT)
    if text != original:
        CLIENT.write_text(text, encoding="utf-8")


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    PATCHES.mkdir(parents=True, exist_ok=True)
    audit_path = RESULTS / "stage6_timing_source_audit.json"
    audit = json.loads(audit_path.read_text()) if audit_path.exists() else {}
    if audit.get("confidence") not in {"high", "medium"}:
        payload = {
            "decision": "BLOCKED_TIMING_INSTRUMENTATION_TARGET_UNKNOWN",
            "reason": "Audit confidence was below medium; refusing to patch.",
        }
        (RESULTS / "stage6_decision.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(json.dumps(payload, indent=2))
        sys.exit(1)

    patch_server()
    patch_client()
    diff = subprocess.check_output(
        ["git", "diff", "--", "scripts/spec/spec_serve_policy.py", "scripts/spec/spec_client_libero.py"],
        cwd=OFFICIAL_DIR,
        text=True,
    )
    (PATCHES / "stage6_server_timing.patch").write_text(diff, encoding="utf-8")
    payload = {
        "status": "patched" if diff.strip() else "already_patched_or_no_diff",
        "patched_files": [
            "scripts/spec/spec_serve_policy.py",
            "scripts/spec/spec_client_libero.py",
        ],
        "patch_file": str(PATCHES / "stage6_server_timing.patch"),
        "added_fields": [
            "policy_time_gpu_sync_ms",
            "policy_time_wall_ms",
            "gpu_sync_before_after_used",
            "timing_patch_stage",
            "timing_patch_note",
        ],
    }
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
