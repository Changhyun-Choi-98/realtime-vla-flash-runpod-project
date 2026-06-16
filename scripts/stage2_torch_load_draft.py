import json
import pathlib
import traceback

import torch


PROJECT = pathlib.Path("/workspace/realtime_vla_flash_project")
CKPT = PROJECT / "checkpoints/drafts/draft_libero_goal.pt"
OUT = PROJECT / "results/stage2_draft_load_smoke.json"


def tensor_summary(state_dict):
    tensors = [(name, tensor) for name, tensor in state_dict.items() if isinstance(tensor, torch.Tensor)]
    return {
        "tensor_count": len(tensors),
        "first_20_tensors": [
            {
                "name": name,
                "shape": list(tensor.shape),
                "dtype": str(tensor.dtype),
            }
            for name, tensor in tensors[:20]
        ],
    }


def main():
    payload = {
        "path": str(CKPT),
        "exists": CKPT.exists(),
        "file_size_bytes": CKPT.stat().st_size if CKPT.exists() else None,
    }
    if not CKPT.exists():
        payload["status"] = "missing"
    else:
        obj = torch.load(CKPT, map_location="cpu")
        payload["status"] = "loaded"
        payload["top_level_type"] = type(obj).__name__
        if isinstance(obj, dict):
            keys = [str(key) for key in obj.keys()]
            payload["top_level_keys"] = keys[:100]
            payload["top_level_key_count"] = len(keys)
            if "draft_head" in obj and isinstance(obj["draft_head"], dict):
                payload["state_dict_source"] = "draft_head"
                payload.update(tensor_summary(obj["draft_head"]))
            else:
                payload["state_dict_source"] = "top_level_dict"
                payload.update(tensor_summary(obj))
        else:
            payload["state_dict_source"] = "not_dict"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        payload = {
            "status": "failure",
            "path": str(CKPT),
            "exists": CKPT.exists(),
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(json.dumps(payload, indent=2))
        raise
