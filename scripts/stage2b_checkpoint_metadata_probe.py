import json
import os
import pathlib
import traceback
import urllib.parse


PROJECT = pathlib.Path("/workspace/realtime_vla_flash_project")
OUT_METADATA = PROJECT / "results/stage2b_metadata_probe.json"
OUT_CANDIDATES = PROJECT / "results/stage2b_checkpoint_candidates.json"


RAW_CANDIDATES = [
    "gs://openpi-assets/checkpoints/pi0_libero",
    "gs://openpi-assets/checkpoints/pi0_libero/params",
    "gs://openpi-assets/checkpoints/pi0_libero_torch",
    "gs://openpi-assets/checkpoints/pi0_libero_torch/params",
    "gs://openpi-assets/checkpoints/pi0_base",
    "gs://openpi-assets/checkpoints/pi0_base/params",
    "gs://openpi-assets/checkpoints/pi05_libero",
    "gs://openpi-assets/checkpoints/pi05_libero/params",
    "s3://openpi-assets/checkpoints/pi0_libero",
    "s3://openpi-assets/checkpoints/pi0_libero/params",
    "/openpi-assets/checkpoints/pi0_libero_torch",
    "/openpi-assets/checkpoints/pi0_libero",
    str(PROJECT / "checkpoints/base_candidates/pi0_libero"),
    str(PROJECT / "checkpoints/base_candidates/pi0_libero_torch"),
]


def scheme_for(path: str) -> str:
    parsed = urllib.parse.urlparse(path)
    return parsed.scheme or "local"


def basename(path: str) -> str:
    return path.rstrip("/").rsplit("/", 1)[-1]


def parent(path: str) -> str:
    return path.rstrip("/").rsplit("/", 1)[0]


def local_probe(path: str) -> dict:
    p = pathlib.Path(path)
    exists = p.exists()
    is_dir = p.is_dir() if exists else False
    sample_entries = []
    total_size = None
    if exists:
        if p.is_dir():
            entries = sorted(p.iterdir(), key=lambda item: item.name)[:50]
            sample_entries = [
                {
                    "name": item.name,
                    "type": "directory" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else 0,
                }
                for item in entries
            ]
            total_size = sum(item.stat().st_size for item in p.rglob("*") if item.is_file())
        else:
            sample_entries = [{"name": p.name, "type": "file", "size": p.stat().st_size}]
            total_size = p.stat().st_size

    root = p if not p.name == "params" else p.parent
    params = root / "params"
    assets = root / "assets"
    assets_samples = []
    params_samples = []
    if assets.is_dir():
        assets_samples = [str(item.relative_to(assets)) for item in list(assets.rglob("*"))[:80]]
    if params.is_dir():
        params_samples = [str(item.relative_to(params)) for item in list(params.rglob("*"))[:80]]

    names = [entry["name"] for entry in sample_entries]
    return {
        "exists": exists,
        "is_dir_like": is_dir,
        "metadata_method": "local_pathlib",
        "entry_count": len(sample_entries),
        "sample_entries": sample_entries,
        "total_size_bytes_if_available": total_size,
        "has_params_subdir": params.is_dir(),
        "has_assets_subdir": assets.is_dir(),
        "has_norm_stats_json": any("norm_stats" in name and name.endswith(".json") for name in assets_samples),
        "has_checkpoint_metadata": any(
            marker in name
            for name in names + params_samples
            for marker in ["_CHECKPOINT_METADATA", "_METADATA", "manifest.ocdbt", "checkpoint"]
        ),
        "params_sample_entries": params_samples[:30],
        "assets_sample_entries": assets_samples[:30],
    }


def remote_list(fs, path: str):
    entries = fs.ls(path, detail=True)
    if isinstance(entries, dict):
        entries = list(entries.values())
    return entries


def remote_exists(fs, path: str) -> bool:
    try:
        return bool(fs.exists(path))
    except Exception:
        try:
            fs.info(path)
            return True
        except Exception:
            return False


def remote_is_dir(fs, path: str) -> bool:
    try:
        info = fs.info(path)
        if info.get("type") == "directory":
            return True
        name = str(info.get("name", ""))
        return info.get("size") == 0 and name.endswith("/")
    except Exception:
        try:
            remote_list(fs, path)
            return True
        except Exception:
            return False


def remote_probe(path: str) -> dict:
    import fsspec

    fs, fs_path = fsspec.core.url_to_fs(path)
    exists = remote_exists(fs, fs_path)
    is_dir = remote_is_dir(fs, fs_path) if exists else False
    entries = []
    if exists and is_dir:
        entries = remote_list(fs, fs_path)
    elif exists:
        entries = [fs.info(fs_path)]

    sample_entries = []
    total = 0
    total_available = False
    for entry in entries[:80]:
        name = str(entry.get("name", ""))
        sample_entries.append(
            {
                "name": pathlib.PurePosixPath(name).name,
                "path_tail": "/".join(pathlib.PurePosixPath(name).parts[-4:]),
                "type": entry.get("type"),
                "size": entry.get("size"),
            }
        )
        if isinstance(entry.get("size"), int):
            total += entry["size"]
            total_available = True

    root = fs_path if basename(fs_path) != "params" else parent(fs_path)
    params_path = root.rstrip("/") + "/params"
    assets_path = root.rstrip("/") + "/assets"
    has_params = remote_exists(fs, params_path)
    has_assets = remote_exists(fs, assets_path)

    params_samples = []
    assets_samples = []
    if has_params and remote_is_dir(fs, params_path):
        try:
            params_samples = [
                "/".join(pathlib.PurePosixPath(str(item.get("name", ""))).parts[-4:])
                for item in remote_list(fs, params_path)[:80]
            ]
        except Exception:
            params_samples = []
    if has_assets and remote_is_dir(fs, assets_path):
        try:
            assets_first = remote_list(fs, assets_path)[:80]
            assets_samples = [
                "/".join(pathlib.PurePosixPath(str(item.get("name", ""))).parts[-5:])
                for item in assets_first
            ]
            for item in assets_first[:20]:
                if item.get("type") == "directory":
                    sub = str(item.get("name", ""))
                    try:
                        assets_samples.extend(
                            [
                                "/".join(pathlib.PurePosixPath(str(child.get("name", ""))).parts[-5:])
                                for child in remote_list(fs, sub)[:80]
                            ]
                        )
                    except Exception:
                        pass
        except Exception:
            assets_samples = []

    checkpoint_markers = ["_CHECKPOINT_METADATA", "_METADATA", "manifest.ocdbt", "checkpoint"]
    return {
        "exists": exists,
        "is_dir_like": is_dir,
        "metadata_method": "fsspec_ls_info",
        "entry_count": len(entries),
        "sample_entries": sample_entries,
        "total_size_bytes_if_available": total if total_available else None,
        "has_params_subdir": has_params,
        "has_assets_subdir": has_assets,
        "has_norm_stats_json": any("norm_stats" in sample and sample.endswith(".json") for sample in assets_samples),
        "has_checkpoint_metadata": any(marker in sample for sample in params_samples for marker in checkpoint_markers),
        "params_sample_entries": params_samples[:30],
        "assets_sample_entries": assets_samples[:30],
    }


def classify(path: str, probe: dict) -> tuple[str, str, bool]:
    exists = bool(probe.get("exists"))
    has_params = bool(probe.get("has_params_subdir"))
    has_assets = bool(probe.get("has_assets_subdir"))
    has_metadata = bool(probe.get("has_checkpoint_metadata"))

    if "pi05_libero" in path:
        return "PUBLIC_PI05_LIBERO_MISMATCH", "pi05_libero was inspected only and is not compatible with the pi0_libero draft unless proven otherwise.", False
    if "pi0_base" in path:
        return "BASE_PI0_PRETRAIN_ONLY", "pi0_base is a pretraining/fine-tuning base, not the paper-compatible pi0_libero policy checkpoint.", False
    if path.startswith("/openpi-assets/") and not exists:
        return "LOCAL_PLACEHOLDER_ONLY", "README/default local placeholder path does not exist on this pod.", False
    if not exists:
        return "NOT_FOUND", "Candidate path was not found or could not be listed as existing.", False
    if "pi0_libero_torch" in path:
        return "MATCH_FLASH_PI0_LIBERO_TORCH_ONLY", "Candidate appears to be a PyTorch checkpoint reference, but base conversion requires a JAX/Orbax checkpoint root.", False
    if "pi0_libero" in path and basename(path) != "params" and has_params and has_assets and has_metadata:
        return "MATCH_FLASH_PI0_LIBERO_JAX", "Candidate has params, assets, and Orbax/JAX checkpoint metadata and is shaped for convert_for_triton --jax-path.", True
    if "pi0_libero" in path and basename(path) == "params":
        return "NOT_FOUND" if not exists else "UNKNOWN_ACCESS_ERROR", "Params subdir alone is not suitable for --jax-path because converter appends /params and also needs sibling assets.", False
    return "UNKNOWN_ACCESS_ERROR", "Candidate exists or was partially visible but did not meet a known safe classification.", False


def probe_one(path: str) -> dict:
    result = {
        "path": path,
        "scheme": scheme_for(path),
        "exists": False,
        "is_dir_like": False,
        "metadata_method": None,
        "entry_count": 0,
        "sample_entries": [],
        "total_size_bytes_if_available": None,
        "has_params_subdir": False,
        "has_assets_subdir": False,
        "has_norm_stats_json": False,
        "has_checkpoint_metadata": False,
        "error_type": None,
        "error": None,
    }
    try:
        update = local_probe(path) if result["scheme"] == "local" else remote_probe(path)
        result.update(update)
    except Exception as exc:
        result["error_type"] = type(exc).__name__
        result["error"] = str(exc)
    classification, reason, selected = classify(path, result)
    result["classification"] = classification
    result["reason"] = reason
    result["selected_candidate"] = selected
    return result


def main():
    candidates = [path.replace("$PROJECT", str(PROJECT)) for path in RAW_CANDIDATES]
    results = [probe_one(path) for path in candidates]
    payload = {
        "status": "ok",
        "note": "Metadata-only probe: no checkpoint contents were downloaded.",
        "candidates": results,
    }
    OUT_METADATA.parent.mkdir(parents=True, exist_ok=True)
    OUT_METADATA.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    OUT_CANDIDATES.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        payload = {
            "status": "failure",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }
        OUT_METADATA.parent.mkdir(parents=True, exist_ok=True)
        OUT_METADATA.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        OUT_CANDIDATES.write_text("[]\n", encoding="utf-8")
        print(json.dumps(payload, indent=2))
        raise
