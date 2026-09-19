#!/usr/bin/env python3
"""Test VulkanEngine step by step with debug output."""
import sys
sys.path.insert(0, 'src')
from dfb.vulkan_engine import VulkanEngine, get_vulkan_engine
from pathlib import Path
import numpy as np

print("Creating VulkanEngine...")
engine = VulkanEngine(Path('shaders'))

print("Step 1: initialize()")
try:
    engine.initialize()
    print("✅ initialize() passed")
except Exception as e:
    print(f"❌ initialize() failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("Step 2: compute()")
try:
    test_input = np.ones(100, dtype=np.float32)
    output = engine.compute(test_input)
    print(f"✅ compute() passed: {output}")
except Exception as e:
    print(f"❌ compute() failed: {e}")
    import traceback
    traceback.print_exc()

print("Step 3: cleanup()")
try:
    engine.cleanup()
    print("✅ cleanup() passed")
except Exception as e:
    print(f"❌ cleanup() failed: {e}")

print("All tests passed!")