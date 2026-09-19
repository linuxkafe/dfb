#!/usr/bin/env python3
"""Test VulkanEngine on Steam Deck."""
import sys
sys.path.insert(0, 'src')
from dfb.vulkan_engine import VulkanEngine
from pathlib import Path
import numpy as np

print("Initializing VulkanEngine...")
engine = VulkanEngine(Path('shaders'))
engine.initialize()

print("Running inference...")
test_input = np.ones(100, dtype=np.float32)
output = engine.compute(test_input)
print(f'Output: {output}')
print(f'Argmax: {np.argmax(output)}')

# Test with different input
test_input2 = np.zeros(100, dtype=np.float32)
test_input2[0] = 1.0
output2 = engine.compute(test_input2)
print(f'Output (one-hot): {output2}')
print(f'Argmax: {np.argmax(output2)}')

engine.cleanup()
print("✅ Test passed")