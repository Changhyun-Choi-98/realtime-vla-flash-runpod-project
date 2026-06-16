import json
import os
import pathlib
import sys
import time
import traceback

import numpy as np


def main():
    suite_name = os.environ.get("LIBERO_SUITE", "libero_goal")
    task_id = int(os.environ.get("LIBERO_TASK_ID", "0"))
    n_steps = int(os.environ.get("LIBERO_RANDOM_STEPS", "20"))
    resolution = int(os.environ.get("LIBERO_RES", "128"))
    output_path = pathlib.Path(
        os.environ.get("STAGE_MINUS1_OUTPUT", "results/stage_minus1_libero_smoke.json")
    )

    from libero.libero import benchmark
    from libero.libero import get_libero_path
    from libero.libero.envs import OffScreenRenderEnv

    benchmark_dict = benchmark.get_benchmark_dict()
    task_suite = benchmark_dict[suite_name]()
    task = task_suite.get_task(task_id)
    bddl_file = pathlib.Path(get_libero_path("bddl_files")) / task.problem_folder / task.bddl_file

    result = {
        "status": "started",
        "suite": suite_name,
        "task_id": task_id,
        "task_language": getattr(task, "language", None),
        "bddl_file": str(bddl_file),
        "mujoco_gl": os.environ.get("MUJOCO_GL"),
        "pyopengl_platform": os.environ.get("PYOPENGL_PLATFORM"),
        "resolution": resolution,
        "steps_requested": n_steps,
    }

    t0 = time.perf_counter()
    env = OffScreenRenderEnv(
        bddl_file_name=str(bddl_file),
        camera_heights=resolution,
        camera_widths=resolution,
    )
    env.seed(0)

    obs = env.reset()
    init_states = task_suite.get_task_init_states(task_id)
    obs = env.set_init_state(init_states[0])
    reset_ms = (time.perf_counter() - t0) * 1000.0

    image_shapes = {}
    image_dtypes = {}
    image_minmax = {}

    for key, value in obs.items():
        if "image" in key:
            arr = np.asarray(value)
            image_shapes[key] = list(arr.shape)
            image_dtypes[key] = str(arr.dtype)
            image_minmax[key] = [float(arr.min()), float(arr.max())]

    if len(image_shapes) == 0:
        raise RuntimeError(f"No image observations found. obs keys = {sorted(list(obs.keys()))}")

    action = np.zeros(7, dtype=np.float32)
    action[-1] = -1.0

    rewards = []
    done = False
    step_times_ms = []

    for _ in range(n_steps):
        s0 = time.perf_counter()
        obs, reward, done, info = env.step(action.tolist())
        step_times_ms.append((time.perf_counter() - s0) * 1000.0)
        rewards.append(float(reward))

    final_image_shapes = {}
    for key, value in obs.items():
        if "image" in key:
            final_image_shapes[key] = list(np.asarray(value).shape)

    env.close()

    result.update(
        {
            "status": "success",
            "reset_ms": reset_ms,
            "steps_completed": n_steps,
            "done": bool(done),
            "reward_sum": float(sum(rewards)),
            "obs_keys": sorted(list(obs.keys())),
            "initial_image_shapes": image_shapes,
            "initial_image_dtypes": image_dtypes,
            "initial_image_minmax": image_minmax,
            "final_image_shapes": final_image_shapes,
            "step_ms_mean": float(np.mean(step_times_ms)),
            "step_ms_p50": float(np.percentile(step_times_ms, 50)),
            "step_ms_p95": float(np.percentile(step_times_ms, 95)),
        }
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        payload = {
            "status": "failure",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
            "mujoco_gl": os.environ.get("MUJOCO_GL"),
            "pyopengl_platform": os.environ.get("PYOPENGL_PLATFORM"),
        }
        print(json.dumps(payload, indent=2), file=sys.stderr)
        out = pathlib.Path(
            os.environ.get(
                "STAGE_MINUS1_OUTPUT", "results/stage_minus1_libero_smoke_failure.json"
            )
        )
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        raise
