import dataclasses
import json
import pathlib
import re
import shutil
import subprocess
import traceback
from typing import Any


PROJECT = pathlib.Path("/workspace/realtime_vla_flash_project")
OFFICIAL_DIR = PROJECT / "repos/realtime-vla-flash"
OUT = PROJECT / "results/stage2_checkpoint_audit.json"


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def safe_text(value: Any) -> str:
    try:
        return str(value)
    except Exception:
        return repr(value)


def extract_paths_from_text(text: str) -> list[str]:
    patterns = [
        r"gs://[^\s`'\",)]+",
        r"/[A-Za-z0-9._~:/-]*checkpoints[A-Za-z0-9._~:/-]*",
    ]
    found = []
    for pattern in patterns:
        found.extend(re.findall(pattern, text))
    return sorted(set(found))


def summarize_config(config_name: str) -> dict[str, Any]:
    from openpi.training import config as training_config

    item = {"name": config_name, "resolution": "not_attempted"}
    try:
        cfg = training_config.get_config(config_name)
        item["resolution"] = "ok"
        item["model_type"] = type(cfg.model).__name__
        item["data_type"] = type(cfg.data).__name__
        item["weight_loader_type"] = type(cfg.weight_loader).__name__
        item["weight_loader"] = safe_text(cfg.weight_loader)
        item["weight_loader_paths"] = extract_paths_from_text(safe_text(cfg.weight_loader))
        item["pytorch_weight_path"] = cfg.pytorch_weight_path
        item["batch_size"] = cfg.batch_size
        item["num_train_steps"] = cfg.num_train_steps
        item["action_horizon"] = getattr(cfg.model, "action_horizon", None)
        item["action_dim"] = getattr(cfg.model, "action_dim", None)
        item["pi05"] = getattr(cfg.model, "pi05", None)
        try:
            data_cfg = cfg.data.create(cfg.assets_dirs, cfg.model)
            item["asset_id"] = getattr(data_cfg.assets, "asset_id", None)
            item["assets_dirs"] = [str(path) for path in getattr(data_cfg, "assets_dirs", [])]
        except Exception as exc:
            item["data_create_error"] = f"{type(exc).__name__}: {exc}"
    except Exception as exc:
        item["resolution"] = "error"
        item["error_type"] = type(exc).__name__
        item["error"] = str(exc)
    return item


def check_gs_metadata(path: str) -> dict[str, Any]:
    result = {"path": path, "status": "not_attempted"}
    try:
        import fsspec

        fs, fs_path = fsspec.core.url_to_fs(path)
        entries = fs.ls(fs_path, detail=True)
        result["status"] = "ok"
        result["entry_count"] = len(entries)
        result["sample"] = [
            {
                "name": pathlib.PurePosixPath(str(entry.get("name", ""))).name,
                "type": entry.get("type"),
                "size": entry.get("size"),
            }
            for entry in entries[:20]
        ]
    except Exception as exc:
        result["status"] = "error"
        result["error_type"] = type(exc).__name__
        result["error"] = str(exc)
    return result


def main():
    from openpi.training import config as training_config

    all_config_names = sorted(getattr(training_config, "_CONFIGS_DICT", {}).keys())
    libero_config_names = sorted([name for name in all_config_names if "libero" in name.lower()])
    focus = sorted(set(["pi0_libero", "pi05_libero", *libero_config_names]))

    readme_text = ""
    for rel in ["README.md", "README_OPENPI.md", "examples/libero/README.md"]:
        path = OFFICIAL_DIR / rel
        if path.exists():
            readme_text += f"\n\n## {rel}\n" + path.read_text(encoding="utf-8", errors="replace")

    configs = [summarize_config(name) for name in focus]
    readme_paths = extract_paths_from_text(readme_text)

    quickstart_base_candidate = "/openpi-assets/checkpoints/pi0_libero_torch"
    base_candidates = sorted(
        set(
            [
                "gs://openpi-assets/checkpoints/pi0_base",
                "gs://openpi-assets/checkpoints/pi0_base/params",
                "gs://openpi-assets/checkpoints/pi05_base",
                "gs://openpi-assets/checkpoints/pi05_base/params",
                "gs://openpi-assets/checkpoints/pi05_libero",
                quickstart_base_candidate,
            ]
            + readme_paths
            + [path for cfg in configs for path in cfg.get("weight_loader_paths", [])]
        )
    )

    payload = {
        "status": "ok",
        "available_libero_configs": libero_config_names,
        "focused_configs": configs,
        "readme_checkpoint_paths": readme_paths,
        "base_checkpoint_candidates": base_candidates,
        "quickstart_base_candidate": {
            "path": quickstart_base_candidate,
            "exists_locally": pathlib.Path(quickstart_base_candidate).exists(),
            "source": "README.md Train Draft Model section references --checkpoint-dir /openpi-assets/checkpoints/pi0_libero_torch",
        },
        "tooling": {
            "gsutil": command_exists("gsutil"),
            "huggingface-cli": command_exists("huggingface-cli"),
            "gcloud": command_exists("gcloud"),
        },
        "fsspec_metadata": {
            "gs://openpi-assets/checkpoints/pi05_libero": check_gs_metadata(
                "gs://openpi-assets/checkpoints/pi05_libero"
            )
        },
        "official_base_checkpoint_assessment": {
            "pi0_libero_weight_loader": "gs://openpi-assets/checkpoints/pi0_base/params",
            "pi05_libero_weight_loader": "gs://openpi-assets/checkpoints/pi05_base/params",
            "flash_quickstart_base_conversion_requires": "local JAX checkpoint directory passed via --jax-path, plus assets/",
            "resolved_for_forced_download": False,
            "reason": "Repo quick start uses placeholder /path/to/jax/checkpoint and /openpi-assets/checkpoints/pi0_libero_torch. The audit identifies candidate paths but does not prove a small, official, directly downloadable pi0_libero JAX checkpoint for base conversion.",
        },
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
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
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(json.dumps(payload, indent=2))
        raise
