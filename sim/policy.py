"""Tiny MLP policy for pendulum."""
import torch
import torch.nn as nn
import numpy as np
from pathlib import Path


class PolicyNet(nn.Module):
    """2-layer MLP: state_dim -> 64 -> 64 -> action_dim."""
    def __init__(self, state_dim: int = 2, action_dim: int = 1, hidden: int = 64):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 64),
            nn.ReLU(),
            nn.Linear(64, action_dim),
            nn.Tanh(),  # action in [-1,1]
        )
        # deterministic init
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight)
                nn.init.zeros_(m.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


def export_onnx(model_path: Path = Path("policy.onnx"), opset: int = 17):
    """Export PolicyNet to ONNX."""
    model = PolicyNet()
    model.eval()
    dummy = torch.randn(1, 2, dtype=torch.float32)  # batch=1, state_dim=2
    torch.onnx.export(
        model,
        dummy,
        model_path,
        export_params=True,
        opset_version=opset,
        do_constant_folding=True,
        input_names=["state"],
        output_names=["action"],
        dynamic_axes={"state": {0: "batch"}, "action": {0: "batch"}},
    )
    print(f"Exported ONNX to {model_path}")


class PolicyWrapper:
    """Runtime wrapper using ONNX Runtime (Vulkan EP preferred)."""
    def __init__(self, onnx_path: Path, providers=None):
        import onnxruntime as ort
        if providers is None:
            providers = ["VulkanExecutionProvider", "CPUExecutionProvider"]
        self.session = ort.InferenceSession(str(onnx_path), providers=providers)
        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name
        print(f"ONNX Runtime providers: {self.session.get_providers()}")

    def predict(self, state: np.ndarray) -> np.ndarray:
        """state: (2,) or (1,2) float32 -> action (1,) float32."""
        if state.ndim == 1:
            state = state[None, :]
        state = state.astype(np.float32)
        action = self.session.run([self.output_name], {self.input_name: state})[0]
        return action.squeeze()


if __name__ == "__main__":
    # quick export test
    export_onnx()