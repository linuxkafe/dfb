#!/usr/bin/env python3
"""Debug VulkanEngine descriptor set layout creation."""
import sys
sys.path.insert(0, 'src')
from dfb.vulkan_engine import VkDescriptorSetLayoutCreateInfo, VkDescriptorSetLayoutBinding
import ctypes

VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO = 0x00000010
VK_DESCRIPTOR_TYPE_STORAGE_BUFFER = 0x00000005
VK_SHADER_STAGE_COMPUTE_BIT = 0x00000020

# Replicate the exact code from _create_descriptor_set
bindings = (VkDescriptorSetLayoutBinding * 7)()
for i, (binding, desc_type) in enumerate([
    (0, 0x00000005),  # input
    (1, 0x00000005),  # W1
    (2, 0x00000005),  # b1
    (3, 0x00000005),  # hidden
    (4, 0x00000005),  # W2
    (5, 0x00000005),  # b2
    (6, 0x00000005),  # output
]):
    bindings[i].binding = binding
    bindings[i].descriptorType = desc_type
    bindings[i].descriptorCount = 1
    bindings[i].stageFlags = 0x00000020

layout_info = VkDescriptorSetLayoutCreateInfo()
layout_info.sType = 0x00000010
layout_info.pNext = ctypes.c_void_p()
layout_info.flags = 0
layout_info.bindingCount = 7
layout_info.pBindings = ctypes.cast(bindings, ctypes.POINTER(VkDescriptorSetLayoutBinding))

print(f"layout_info type: {type(layout_info)}")
print(f"layout_info.sType: {layout_info.sType}")
print(f"layout_info.pNext: {layout_info.pNext}")
print(f"layout_info.flags: {layout_info.flags}")
print(f"layout_info.bindingCount: {layout_info.bindingCount}")
print(f"layout_info.pBindings: {layout_info.pBindings}")

# Test byref
try:
    ptr = ctypes.byref(layout_info)
    print(f"byref works: {ptr}")
except Exception as e:
    print(f"byref failed: {e}")

# Test pointer
try:
    ptr = ctypes.pointer(layout_info)
    print(f"pointer works: {ptr}")
except Exception as e:
    print(f"pointer failed: {e}")