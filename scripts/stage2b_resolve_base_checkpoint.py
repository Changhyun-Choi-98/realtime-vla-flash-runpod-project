import json
import os
import pathlib
import subprocess
import traceback


PROJECT = pathlib.Path("/workspace/realtime_vla_flash_project")
METADATA = PROJECT / "results/stage2b_metadata_probe.json"
OUT = PROJECT / "results/stage2b_base_resolution_decision.json"
DOWNLOAD_LOG = PROJECT / "logs/stage2b_base_download.txt"


def write_download_log(lines):
    DOWNLOAD_LOG.parent.mkdir(parents=True, exist_ok=True)
    DOWNLOAD_LOG.write_text("\n".join(lines) + "\n", encoding="utf-8")


def sample_files(path: pathlib.Path, limit: int = 100):
    if not path.exists():
        return []
    if path.is_file():
        return [path.name]
    return [str(item.relative_to(path)) for item in path.rglob("*") if item.is_file()][:limit]


def file_count(path: pathlib.Path, limit: int = 1_000_000) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        return 1
    count = 0
    for item in path.rglob("*"):
        if item.is_file():
            count += 1
            if count >= limit:
                break
    return count


def du_sh(path: pathlib.Path) -> str:
    try:
        return subprocess.check_output(["du", "-sh", str(path)], text=True, stderr=subprocess.STDOUT).split()[0]
    except Exception as exc:
        return f"unavailable: {type(exc).__name__}: {exc}"


def validate_download(path: pathlib.Path):
    params = path / "params"
    assets = path / "assets"
    params_files = sample_files(params, limit=120)
    assets_files = sample_files(assets, limit=120)
    has_checkpoint_metadata = any(
        marker in item
        for item in params_files
        for marker in ["_CHECKPOINT_METADATA", "_METADATA", "manifest.ocdbt", "checkpoint"]
    )
    has_norm_stats = any("norm_stats" in item and item.endswith(".json") for item in assets_files)
    return {
        "downloaded_path": str(path),
        "downloaded_path_exists": path.exists(),
        "contains_params": params.is_dir(),
        "contains_assets": assets.is_dir(),
        "has_checkpoint_metadata": has_checkpoint_metadata,
        "has_norm_stats_json": has_norm_stats,
        "du_sh": du_sh(path) if path.exists() else None,
        "file_count": file_count(path),
        "sample_files": sample_files(path, limit=120),
        "params_sample_files": params_files[:40],
        "assets_sample_files": assets_files[:40],
    }


def main():
    metadata = json.loads(METADATA.read_text())
    candidates = metadata.get("candidates", [])
    matches = [item for item in candidates if item.get("classification") == "MATCH_FLASH_PI0_LIBERO_JAX"]

    if not matches:
        payload = {
            "decision": "BLOCKED_NO_PUBLIC_PI0_LIBERO_JAX_CHECKPOINT",
            "reason": "Metadata-only probe found no candidate classified as MATCH_FLASH_PI0_LIBERO_JAX.",
            "selected_candidate": None,
        }
        write_download_log(
            [
                "BASE_DOWNLOAD_STATUS=SKIPPED",
                "reason=no public pi0_libero JAX checkpoint candidate was classified as suitable",
            ]
        )
        OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(json.dumps(payload, indent=2))
        return 0

    if len(matches) > 1:
        payload = {
            "decision": "BLOCKED_MULTIPLE_AMBIGUOUS_PI0_LIBERO_CANDIDATES",
            "reason": "More than one metadata candidate matched MATCH_FLASH_PI0_LIBERO_JAX.",
            "matches": matches,
        }
        write_download_log(
            [
                "BASE_DOWNLOAD_STATUS=SKIPPED",
                "reason=multiple ambiguous pi0_libero JAX candidates",
            ]
        )
        OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(json.dumps(payload, indent=2))
        return 0

    candidate = matches[0]
    candidate_path = candidate["path"]
    os.environ["OPENPI_DATA_HOME"] = str(PROJECT / "checkpoints/base_candidates/openpi_cache")
    log_lines = [
        "BASE_DOWNLOAD_STATUS=STARTED",
        f"candidate={candidate_path}",
        f"openpi_data_home={os.environ['OPENPI_DATA_HOME']}",
        "risk=may download a large public base checkpoint directory; selected only because metadata classified it as MATCH_FLASH_PI0_LIBERO_JAX",
    ]
    write_download_log(log_lines)

    try:
        from openpi.shared import download

        local_path = pathlib.Path(download.maybe_download(candidate_path)).resolve()
    except Exception as exc:
        payload = {
            "decision": "BLOCKED_DOWNLOAD_FAILED",
            "selected_candidate": candidate,
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
        write_download_log(log_lines + [f"BASE_DOWNLOAD_STATUS=FAILED", f"error_type={type(exc).__name__}", f"error={exc}"])
        OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(json.dumps(payload, indent=2))
        return 1

    validation = validate_download(local_path)
    valid = (
        validation["downloaded_path_exists"]
        and validation["contains_params"]
        and validation["contains_assets"]
        and validation["has_checkpoint_metadata"]
    )

    if not valid:
        payload = {
            "decision": "BLOCKED_DOWNLOADED_STRUCTURE_INVALID",
            "selected_candidate": candidate,
            "base_jax_path": str(local_path),
            "validation": validation,
        }
        write_download_log(log_lines + ["BASE_DOWNLOAD_STATUS=DOWNLOADED_BUT_INVALID", json.dumps(validation, indent=2)])
        OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(json.dumps(payload, indent=2))
        return 1

    payload = {
        "decision": "BASE_CHECKPOINT_RESOLVED",
        "selected_candidate": candidate,
        "base_jax_path": str(local_path),
        "validation": validation,
    }
    write_download_log(log_lines + ["BASE_DOWNLOAD_STATUS=RESOLVED", json.dumps(validation, indent=2)])
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        payload = {
            "decision": "BLOCKED_DOWNLOAD_FAILED",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        write_download_log([f"BASE_DOWNLOAD_STATUS=FAILED", f"error_type={type(exc).__name__}", f"error={exc}"])
        print(json.dumps(payload, indent=2))
        raise
