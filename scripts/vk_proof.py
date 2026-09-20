import faulthandler
import sys
from pathlib import Path

faulthandler.enable()

sys.path.insert(0, str(Path(__file__).resolve().parent))
from src.dfb.vulkan_engine import VulkanEngine

def main():
    shader_dir = Path("/home/deck/.local/share/dfb/shaders")
    eng = VulkanEngine(shader_dir)
    eng.initialize()
    import numpy as np
    inp = np.ones(100, dtype=np.float32) * 0.5
    out = eng.compute(inp)
    print(f"VK-PROOF output={out.tolist()}")
    print(f"VK-PROOF argmax={int(out.argmax())} shape={out.shape}")
    eng.cleanup()
    print("VK-PROOF OK")
    return 0

if __name__ == "__main__":
    sys.exit(main())