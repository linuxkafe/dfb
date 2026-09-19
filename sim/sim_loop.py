"""Simulation loop: MuJoCo physics + policy inference."""
import time
import numpy as np
import mujoco
from sim.policy import PolicyWrapper


def run_simulation(
    model_path: str = "sim/mujoco_model.xml",
    policy_path: str = "policy.onnx",
    steps: int = 1000,
    providers=None,
):
    """Run MuJoCo simulation with policy inference each step."""
    # Load MuJoCo model
    model = mujoco.MjModel.from_xml_path(model_path)
    data = mujoco.MjData(model)

    # Load policy
    policy = PolicyWrapper(policy_path)

    # State extraction: for pendulum, state = [angle, angular_vel]
    def get_state(d):
        # qpos[0] = hinge angle, qvel[0] = angular velocity
        return np.array([d.qpos[0], d.qvel[0]], dtype=np.float32)

    latencies = []
    for i in range(steps):
        state = get_state(data)

        # Inference
        t0 = time.perf_counter()
        action = policy.predict(state)
        latencies.append(time.perf_counter() - t0)

        # Apply action (torque)
        data.ctrl[0] = np.clip(action, -1.0, 1.0)

        # Physics step
        mujoco.mj_step(model, data)

    avg_lat = np.mean(latencies) * 1000  # ms
    print(f"Ran {steps} steps. Avg inference latency: {avg_lat:.3f} ms")
    return latencies


if __name__ == "__main__":
    run_simulation(steps=100)