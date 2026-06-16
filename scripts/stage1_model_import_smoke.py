import json
import pathlib
import platform
import subprocess
import sys
import textwrap
import traceback


PROJECT = pathlib.Path("/workspace/realtime_vla_flash_project")
OUT = PROJECT / "results/stage1_model_env.json"


def run_probe(name: str, code: str, timeout: int = 60):
    try:
        proc = subprocess.run(
            [sys.executable, "-c", code],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
        payload = {
            "status": "ok" if proc.returncode == 0 else "error",
            "exit_status": proc.returncode,
            "stdout": proc.stdout.strip()[-4000:],
            "stderr": proc.stderr.strip()[-4000:],
        }
        try:
            payload["json"] = json.loads(proc.stdout)
        except Exception:
            pass
        return payload
    except subprocess.TimeoutExpired as exc:
        return {
            "status": "timeout",
            "timeout_seconds": timeout,
            "stdout": (exc.stdout or "")[-4000:] if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr or "")[-4000:] if isinstance(exc.stderr, str) else "",
        }
    except Exception as exc:
        return {
            "status": "exception",
            "error_type": type(exc).__name__,
            "error": str(exc),
        }


VERSION_CODE = """
import json
name = {name!r}
mod = __import__(name)
print(json.dumps({{"version": getattr(mod, "__version__", "unknown")}}))
"""


def main():
    module_names = ["torch", "triton", "jax", "transformers", "numpy", "openpi"]
    modules = {
        name: run_probe(name, VERSION_CODE.format(name=name), timeout=45)
        for name in module_names
    }

    nested_imports = {}
    for name in ["openpi.training.config", "openpi.policies.policy_config"]:
        nested_imports[name] = run_probe(
            name,
            VERSION_CODE.format(name=name),
            timeout=240,
        )

    torch_cuda = run_probe(
        "torch_cuda",
        textwrap.dedent(
            """
            import json
            import torch
            payload = {
                "torch_cuda_available": torch.cuda.is_available(),
                "torch_cuda_version": torch.version.cuda,
            }
            if torch.cuda.is_available():
                payload["torch_gpu_name"] = torch.cuda.get_device_name(0)
                payload["torch_device_capability"] = list(torch.cuda.get_device_capability(0))
            print(json.dumps(payload))
            """
        ),
        timeout=60,
    )

    jax_devices = run_probe(
        "jax_devices",
        textwrap.dedent(
            """
            import json
            import jax
            print(json.dumps({"jax_devices": [str(device) for device in jax.devices()]}))
            """
        ),
        timeout=60,
    )

    transformers_replace = run_probe(
        "transformers_replace_check",
        textwrap.dedent(
            """
            import json
            from openpi.models_pytorch.transformers_replace.models.siglip import check
            print(json.dumps({
                "transformers_replace_check": check.check_whether_transformers_replace_is_installed_correctly()
            }))
            """
        ),
        timeout=60,
    )

    payload = {
        "status": "ok",
        "python": sys.version,
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "modules": modules,
        "nested_imports": nested_imports,
        "torch_cuda_probe": torch_cuda,
        "jax_devices_probe": jax_devices,
        "transformers_replace_probe": transformers_replace,
    }

    if any(item.get("status") not in {"ok"} for item in modules.values()):
        payload["status"] = "partial"
    if any(item.get("status") not in {"ok"} for item in nested_imports.values()):
        payload["status"] = "partial"

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
