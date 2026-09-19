#!/usr/bin/env python3
"""Debug VkDescriptorSetLayoutCreateInfo."""
import ctypes

# Load vulkan
lib = ctypes.CDLL('libvulkan.so.1')

class VkDescriptorSetLayoutBinding(ctypes.Structure):
    _fields_ = [
        ('binding', ctypes.c_uint32),
        ('descriptorType', ctypes.c_int),
        ('descriptorCount', ctypes.c_uint32),
        ('stageFlags', ctypes.c_int),
        ('pImmutableSamplers', ctypes.c_void_p),
    ]

class VkDescriptorSetLayoutCreateInfo(ctypes.Structure):
    _fields_ = [
        ('sType', ctypes.c_int),
        ('pNext', ctypes.c_void_p),
        ('flags', ctypes.c_uint32),
        ('bindingCount', ctypes.c_uint32),
        ('pBindings', ctypes.POINTER(VkDescriptorSetLayoutBinding)),
    ]

# Test creating the structure
bindings = (VkDescriptorSetLayoutBinding * 7)()
for i in range(7):
    bindings[i].binding = i
    bindings[i].descriptorType = 0x00000005  # STORAGE_BUFFER
    bindings[i].descriptorCount = 1
    bindings[i].stageFlags = 0x00000020  # COMPUTE_BIT

layout_info = VkDescriptorSetLayoutCreateInfo()
layout_info.sType = 0x00000010  # DESCRIPTOR_SET_LAYOUT_CREATE_INFO
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