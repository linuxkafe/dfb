"""Vulkan compute engine for Fly Brain decision inference."""
import os
import ctypes
import numpy as np
from pathlib import Path
from typing import Optional, Tuple, List
from dataclasses import dataclass


# Vulkan constants
VK_API_VERSION_1_0 = 0  # Use 0 to let loader pick default
VK_STRUCTURE_TYPE_APPLICATION_INFO = 0
VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO = 1
VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO = 2
VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO = 3
VK_STRUCTURE_TYPE_SUBMIT_INFO = 4
VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO = 5
VK_STRUCTURE_TYPE_FENCE_CREATE_INFO = 8
VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO = 12
VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO = 16
VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO = 18
VK_STRUCTURE_TYPE_GRAPHICS_PIPELINE_CREATE_INFO = 28
VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO = 29
VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO = 30
VK_STRUCTURE_TYPE_SAMPLER_CREATE_INFO = 31
VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO = 32
VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO = 33
VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO = 34
VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET = 35
VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO = 39
VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO = 40
VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO = 42
VK_STRUCTURE_TYPE_MEMORY_BARRIER = 46
VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT = 0x00000020
VK_ACCESS_SHADER_READ_BIT = 0x00000020
VK_ACCESS_SHADER_WRITE_BIT = 0x00000040

VK_QUEUE_COMPUTE_BIT = 0x00000002
VK_BUFFER_USAGE_STORAGE_BUFFER_BIT = 0x00000200
VK_BUFFER_USAGE_TRANSFER_SRC_BIT = 0x00000001
VK_BUFFER_USAGE_TRANSFER_DST_BIT = 0x00000004
VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT = 0x00000001
VK_MEMORY_PROPERTY_HOST_COHERENT_BIT = 0x00000002
VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT = 0x00000004
VK_SHADER_STAGE_COMPUTE_BIT = 0x00000020
VK_PIPELINE_BIND_POINT_COMPUTE = 0x00000001
VK_DESCRIPTOR_TYPE_STORAGE_BUFFER = 0x00000007
VK_COMMAND_BUFFER_LEVEL_PRIMARY = 0x00000000
VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT = 0x00000002
VK_FENCE_CREATE_SIGNALED_BIT = 0x00000001
VK_SUCCESS = 0

VK_NULL_HANDLE = 0
VK_WHOLE_SIZE = 0xFFFFFFFFFFFFFFFF


def load_vulkan():
    """Load libvulkan.so and define function signatures."""
    try:
        lib = ctypes.CDLL("libvulkan.so.1")
    except OSError:
        try:
            lib = ctypes.CDLL("libvulkan.so")
        except OSError as e:
            raise RuntimeError("Cannot load libvulkan.so. Install vulkan-tools/vulkan-runtime.") from e

    # Define function prototypes
    lib.vkCreateInstance.argtypes = [ctypes.POINTER(VkInstanceCreateInfo), ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint64)]
    lib.vkCreateInstance.restype = ctypes.c_int

    lib.vkEnumeratePhysicalDevices.argtypes = [ctypes.c_uint64, ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_uint64)]
    lib.vkEnumeratePhysicalDevices.restype = ctypes.c_int

    lib.vkGetPhysicalDeviceQueueFamilyProperties.argtypes = [ctypes.c_uint64, ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(VkQueueFamilyProperties)]
    lib.vkGetPhysicalDeviceQueueFamilyProperties.restype = None

    lib.vkCreateDevice.argtypes = [ctypes.c_uint64, ctypes.POINTER(VkDeviceCreateInfo), ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint64)]
    lib.vkCreateDevice.restype = ctypes.c_int

    lib.vkGetDeviceQueue.argtypes = [ctypes.c_uint64, ctypes.c_uint32, ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint64)]
    lib.vkGetDeviceQueue.restype = None

    lib.vkCreateCommandPool.argtypes = [ctypes.c_uint64, ctypes.POINTER(VkCommandPoolCreateInfo), ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint64)]
    lib.vkCreateCommandPool.restype = ctypes.c_int

    lib.vkAllocateCommandBuffers.argtypes = [ctypes.c_uint64, ctypes.POINTER(VkCommandBufferAllocateInfo), ctypes.POINTER(ctypes.c_uint64)]
    lib.vkAllocateCommandBuffers.restype = ctypes.c_int

    lib.vkCreateFence.argtypes = [ctypes.c_uint64, ctypes.POINTER(VkFenceCreateInfo), ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint64)]
    lib.vkCreateFence.restype = ctypes.c_int

    lib.vkWaitForFences.argtypes = [ctypes.c_uint64, ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint64), ctypes.c_int, ctypes.c_uint64]
    lib.vkWaitForFences.restype = ctypes.c_int

    lib.vkResetFences.argtypes = [ctypes.c_uint64, ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint64)]
    lib.vkResetFences.restype = ctypes.c_int

    lib.vkCreateBuffer.argtypes = [ctypes.c_uint64, ctypes.POINTER(VkBufferCreateInfo), ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint64)]
    lib.vkCreateBuffer.restype = ctypes.c_int

    lib.vkGetBufferMemoryRequirements.argtypes = [ctypes.c_uint64, ctypes.c_uint64, ctypes.POINTER(VkMemoryRequirements)]
    lib.vkGetBufferMemoryRequirements.restype = None

    lib.vkAllocateMemory.argtypes = [ctypes.c_uint64, ctypes.POINTER(VkMemoryAllocateInfo), ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint64)]
    lib.vkAllocateMemory.restype = ctypes.c_int

    lib.vkBindBufferMemory.argtypes = [ctypes.c_uint64, ctypes.c_uint64, ctypes.c_uint64, ctypes.c_uint64]
    lib.vkBindBufferMemory.restype = ctypes.c_int

    lib.vkMapMemory.argtypes = [ctypes.c_uint64, ctypes.c_uint64, ctypes.c_uint64, ctypes.c_uint64, ctypes.c_uint32, ctypes.POINTER(ctypes.c_void_p)]
    lib.vkMapMemory.restype = ctypes.c_int

    lib.vkUnmapMemory.argtypes = [ctypes.c_uint64, ctypes.c_uint64]
    lib.vkUnmapMemory.restype = None

    lib.vkCreateDescriptorSetLayout.argtypes = [ctypes.c_uint64, ctypes.POINTER(VkDescriptorSetLayoutCreateInfo), ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint64)]
    lib.vkCreateDescriptorSetLayout.restype = ctypes.c_int

    lib.vkCreateDescriptorPool.argtypes = [ctypes.c_uint64, ctypes.POINTER(VkDescriptorPoolCreateInfo), ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint64)]
    lib.vkCreateDescriptorPool.restype = ctypes.c_int

    lib.vkAllocateDescriptorSets.argtypes = [ctypes.c_uint64, ctypes.POINTER(VkDescriptorSetAllocateInfo), ctypes.POINTER(ctypes.c_uint64)]
    lib.vkAllocateDescriptorSets.restype = ctypes.c_int

    lib.vkUpdateDescriptorSets.argtypes = [ctypes.c_uint64, ctypes.c_uint32, ctypes.POINTER(VkWriteDescriptorSet), ctypes.c_uint32, ctypes.c_void_p]
    lib.vkUpdateDescriptorSets.restype = None

    lib.vkCreatePipelineLayout.argtypes = [ctypes.c_uint64, ctypes.POINTER(VkPipelineLayoutCreateInfo), ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint64)]
    lib.vkCreatePipelineLayout.restype = ctypes.c_int

    lib.vkCreateShaderModule.argtypes = [ctypes.c_uint64, ctypes.POINTER(VkShaderModuleCreateInfo), ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint64)]
    lib.vkCreateShaderModule.restype = ctypes.c_int

    lib.vkCreateComputePipelines.argtypes = [ctypes.c_uint64, ctypes.c_uint64, ctypes.c_uint32, ctypes.POINTER(VkComputePipelineCreateInfo), ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint64)]
    lib.vkCreateComputePipelines.restype = ctypes.c_int

    lib.vkCmdBindPipeline.argtypes = [ctypes.c_uint64, ctypes.c_int, ctypes.c_uint64]
    lib.vkCmdBindPipeline.restype = None

    lib.vkCmdBindDescriptorSets.argtypes = [ctypes.c_uint64, ctypes.c_int, ctypes.c_uint64, ctypes.c_uint32, ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint64), ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint32)]
    lib.vkCmdBindDescriptorSets.restype = None

    lib.vkCmdDispatch.argtypes = [ctypes.c_uint64, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32]
    lib.vkCmdDispatch.restype = None

    lib.vkCmdPipelineBarrier.argtypes = [ctypes.c_uint64, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32, ctypes.POINTER(VkMemoryBarrier), ctypes.c_uint32, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p]
    lib.vkCmdPipelineBarrier.restype = None

    lib.vkBeginCommandBuffer.argtypes = [ctypes.c_uint64, ctypes.POINTER(VkCommandBufferBeginInfo)]
    lib.vkBeginCommandBuffer.restype = ctypes.c_int

    lib.vkEndCommandBuffer.argtypes = [ctypes.c_uint64]
    lib.vkEndCommandBuffer.restype = ctypes.c_int

    lib.vkQueueSubmit.argtypes = [ctypes.c_uint64, ctypes.c_uint32, ctypes.POINTER(VkSubmitInfo), ctypes.c_uint64]
    lib.vkQueueSubmit.restype = ctypes.c_int

    lib.vkQueueWaitIdle.argtypes = [ctypes.c_uint64]
    lib.vkQueueWaitIdle.restype = ctypes.c_int

    lib.vkDestroyPipeline.argtypes = [ctypes.c_uint64, ctypes.c_uint64, ctypes.c_void_p]
    lib.vkDestroyPipeline.restype = None

    lib.vkDestroyPipelineLayout.argtypes = [ctypes.c_uint64, ctypes.c_uint64, ctypes.c_void_p]
    lib.vkDestroyPipelineLayout.restype = None

    lib.vkDestroyShaderModule.argtypes = [ctypes.c_uint64, ctypes.c_uint64, ctypes.c_void_p]
    lib.vkDestroyShaderModule.restype = None

    lib.vkDestroyDescriptorSetLayout.argtypes = [ctypes.c_uint64, ctypes.c_uint64, ctypes.c_void_p]
    lib.vkDestroyDescriptorSetLayout.restype = None

    lib.vkDestroyDescriptorPool.argtypes = [ctypes.c_uint64, ctypes.c_uint64, ctypes.c_void_p]
    lib.vkDestroyDescriptorPool.restype = None

    lib.vkDestroyCommandPool.argtypes = [ctypes.c_uint64, ctypes.c_uint64, ctypes.c_void_p]
    lib.vkDestroyCommandPool.restype = None

    lib.vkDestroyFence.argtypes = [ctypes.c_uint64, ctypes.c_uint64, ctypes.c_void_p]
    lib.vkDestroyFence.restype = None

    lib.vkDestroyBuffer.argtypes = [ctypes.c_uint64, ctypes.c_uint64, ctypes.c_void_p]
    lib.vkDestroyBuffer.restype = None

    lib.vkFreeMemory.argtypes = [ctypes.c_uint64, ctypes.c_uint64, ctypes.c_void_p]
    lib.vkFreeMemory.restype = None

    lib.vkDestroyDevice.argtypes = [ctypes.c_uint64, ctypes.c_void_p]
    lib.vkDestroyDevice.restype = None

    lib.vkDestroyInstance.argtypes = [ctypes.c_uint64, ctypes.c_void_p]
    lib.vkDestroyInstance.restype = None

    lib.vkGetPhysicalDeviceMemoryProperties.argtypes = [ctypes.c_uint64, ctypes.POINTER(VkPhysicalDeviceMemoryProperties)]
    lib.vkGetPhysicalDeviceMemoryProperties.restype = None

    return lib


# Vulkan structures
class VkApplicationInfo(ctypes.Structure):
    _fields_ = [
        ("sType", ctypes.c_int),
        ("pNext", ctypes.c_void_p),
        ("pApplicationName", ctypes.c_char_p),
        ("applicationVersion", ctypes.c_uint32),
        ("pEngineName", ctypes.c_char_p),
        ("engineVersion", ctypes.c_uint32),
        ("apiVersion", ctypes.c_uint32),
    ]


class VkInstanceCreateInfo(ctypes.Structure):
    _fields_ = [
        ("sType", ctypes.c_int),
        ("pNext", ctypes.c_void_p),
        ("flags", ctypes.c_uint32),
        ("pApplicationInfo", ctypes.POINTER(VkApplicationInfo)),
        ("enabledLayerCount", ctypes.c_uint32),
        ("ppEnabledLayerNames", ctypes.POINTER(ctypes.c_char_p)),
        ("enabledExtensionCount", ctypes.c_uint32),
        ("ppEnabledExtensionNames", ctypes.POINTER(ctypes.c_char_p)),
    ]


class VkQueueFamilyProperties(ctypes.Structure):
    _fields_ = [
        ("queueFlags", ctypes.c_uint32),
        ("queueCount", ctypes.c_uint32),
        ("timestampValidBits", ctypes.c_uint32),
        ("minImageTransferGranularity", ctypes.c_uint32 * 3),
    ]


class VkDeviceQueueCreateInfo(ctypes.Structure):
    _fields_ = [
        ("sType", ctypes.c_int),
        ("pNext", ctypes.c_void_p),
        ("flags", ctypes.c_uint32),
        ("queueFamilyIndex", ctypes.c_uint32),
        ("queueCount", ctypes.c_uint32),
        ("pQueuePriorities", ctypes.POINTER(ctypes.c_float)),
    ]


class VkDeviceCreateInfo(ctypes.Structure):
    _fields_ = [
        ("sType", ctypes.c_int),
        ("pNext", ctypes.c_void_p),
        ("flags", ctypes.c_uint32),
        ("queueCreateInfoCount", ctypes.c_uint32),
        ("pQueueCreateInfos", ctypes.POINTER(VkDeviceQueueCreateInfo)),
        ("enabledLayerCount", ctypes.c_uint32),
        ("ppEnabledLayerNames", ctypes.POINTER(ctypes.c_char_p)),
        ("enabledExtensionCount", ctypes.c_uint32),
        ("ppEnabledExtensionNames", ctypes.POINTER(ctypes.c_char_p)),
        ("pEnabledFeatures", ctypes.c_void_p),
    ]


class VkCommandPoolCreateInfo(ctypes.Structure):
    _fields_ = [
        ("sType", ctypes.c_int),
        ("pNext", ctypes.c_void_p),
        ("flags", ctypes.c_uint32),
        ("queueFamilyIndex", ctypes.c_uint32),
    ]


class VkCommandBufferAllocateInfo(ctypes.Structure):
    _fields_ = [
        ("sType", ctypes.c_int),
        ("pNext", ctypes.c_void_p),
        ("commandPool", ctypes.c_uint64),
        ("level", ctypes.c_int),
        ("commandBufferCount", ctypes.c_uint32),
    ]


class VkFenceCreateInfo(ctypes.Structure):
    _fields_ = [
        ("sType", ctypes.c_int),
        ("pNext", ctypes.c_void_p),
        ("flags", ctypes.c_uint32),
    ]


class VkBufferCreateInfo(ctypes.Structure):
    _fields_ = [
        ("sType", ctypes.c_int),
        ("pNext", ctypes.c_void_p),
        ("flags", ctypes.c_uint32),
        ("size", ctypes.c_uint64),
        ("usage", ctypes.c_uint32),
        ("sharingMode", ctypes.c_int),
        ("queueFamilyIndexCount", ctypes.c_uint32),
        ("pQueueFamilyIndices", ctypes.POINTER(ctypes.c_uint32)),
    ]


class VkMemoryRequirements(ctypes.Structure):
    _fields_ = [
        ("size", ctypes.c_uint64),
        ("alignment", ctypes.c_uint64),
        ("memoryTypeBits", ctypes.c_uint32),
    ]


class VkMemoryAllocateInfo(ctypes.Structure):
    _fields_ = [
        ("sType", ctypes.c_int),
        ("pNext", ctypes.c_void_p),
        ("allocationSize", ctypes.c_uint64),
        ("memoryTypeIndex", ctypes.c_uint32),
    ]


class VkDescriptorSetLayoutBinding(ctypes.Structure):
    _fields_ = [
        ("binding", ctypes.c_uint32),
        ("descriptorType", ctypes.c_int),
        ("descriptorCount", ctypes.c_uint32),
        ("stageFlags", ctypes.c_int),
        ("pImmutableSamplers", ctypes.c_void_p),
    ]


class VkDescriptorSetLayoutCreateInfo(ctypes.Structure):
    _fields_ = [
        ("sType", ctypes.c_int),
        ("pNext", ctypes.c_void_p),
        ("flags", ctypes.c_uint32),
        ("bindingCount", ctypes.c_uint32),
        ("pBindings", ctypes.POINTER(VkDescriptorSetLayoutBinding)),
    ]


class VkDescriptorPoolSize(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_int),
        ("descriptorCount", ctypes.c_uint32),
    ]


class VkDescriptorPoolCreateInfo(ctypes.Structure):
    _fields_ = [
        ("sType", ctypes.c_int),
        ("pNext", ctypes.c_void_p),
        ("flags", ctypes.c_uint32),
        ("maxSets", ctypes.c_uint32),
        ("poolSizeCount", ctypes.c_uint32),
        ("pPoolSizes", ctypes.POINTER(VkDescriptorPoolSize)),
    ]


class VkDescriptorSetAllocateInfo(ctypes.Structure):
    _fields_ = [
        ("sType", ctypes.c_int),
        ("pNext", ctypes.c_void_p),
        ("descriptorPool", ctypes.c_uint64),
        ("descriptorSetCount", ctypes.c_uint32),
        ("pSetLayouts", ctypes.POINTER(ctypes.c_uint64)),
    ]


class VkDescriptorBufferInfo(ctypes.Structure):
    _fields_ = [
        ("buffer", ctypes.c_uint64),
        ("offset", ctypes.c_uint64),
        ("range", ctypes.c_uint64),
    ]


class VkWriteDescriptorSet(ctypes.Structure):
    _fields_ = [
        ("sType", ctypes.c_int),
        ("pNext", ctypes.c_void_p),
        ("dstSet", ctypes.c_uint64),
        ("dstBinding", ctypes.c_uint32),
        ("dstArrayElement", ctypes.c_uint32),
        ("descriptorCount", ctypes.c_uint32),
        ("descriptorType", ctypes.c_int),
        ("pImageInfo", ctypes.c_void_p),
        ("pBufferInfo", ctypes.POINTER(VkDescriptorBufferInfo)),
        ("pTexelBufferView", ctypes.c_void_p),
    ]


class VkPipelineLayoutCreateInfo(ctypes.Structure):
    _fields_ = [
        ("sType", ctypes.c_int),
        ("pNext", ctypes.c_void_p),
        ("flags", ctypes.c_uint32),
        ("setLayoutCount", ctypes.c_uint32),
        ("pSetLayouts", ctypes.POINTER(ctypes.c_uint64)),
        ("pushConstantRangeCount", ctypes.c_uint32),
        ("pPushConstantRanges", ctypes.c_void_p),
    ]


class VkShaderModuleCreateInfo(ctypes.Structure):
    _fields_ = [
        ("sType", ctypes.c_int),
        ("pNext", ctypes.c_void_p),
        ("flags", ctypes.c_uint32),
        ("codeSize", ctypes.c_uint64),
        ("pCode", ctypes.POINTER(ctypes.c_uint32)),
    ]


class VkPipelineShaderStageCreateInfo(ctypes.Structure):
    _fields_ = [
        ("sType", ctypes.c_int),
        ("pNext", ctypes.c_void_p),
        ("flags", ctypes.c_uint32),
        ("stage", ctypes.c_int),
        ("module", ctypes.c_uint64),
        ("pName", ctypes.c_char_p),
        ("pSpecializationInfo", ctypes.c_void_p),
    ]


class VkComputePipelineCreateInfo(ctypes.Structure):
    _fields_ = [
        ("sType", ctypes.c_int),
        ("pNext", ctypes.c_void_p),
        ("flags", ctypes.c_uint32),
        ("stage", VkPipelineShaderStageCreateInfo),
        ("layout", ctypes.c_uint64),
        ("basePipelineHandle", ctypes.c_uint64),
        ("basePipelineIndex", ctypes.c_int),
    ]


class VkCommandBufferBeginInfo(ctypes.Structure):
    _fields_ = [
        ("sType", ctypes.c_int),
        ("pNext", ctypes.c_void_p),
        ("flags", ctypes.c_uint32),
        ("pInheritanceInfo", ctypes.c_void_p),
    ]


class VkMemoryBarrier(ctypes.Structure):
    _fields_ = [
        ("sType", ctypes.c_int),
        ("pNext", ctypes.c_void_p),
        ("srcAccessMask", ctypes.c_uint32),
        ("dstAccessMask", ctypes.c_uint32),
    ]


class VkSubmitInfo(ctypes.Structure):
    _fields_ = [
        ("sType", ctypes.c_int),
        ("pNext", ctypes.c_void_p),
        ("waitSemaphoreCount", ctypes.c_uint32),
        ("pWaitSemaphores", ctypes.POINTER(ctypes.c_uint64)),
        ("pWaitDstStageMask", ctypes.POINTER(ctypes.c_uint32)),
        ("commandBufferCount", ctypes.c_uint32),
        ("pCommandBuffers", ctypes.POINTER(ctypes.c_uint64)),
        ("signalSemaphoreCount", ctypes.c_uint32),
        ("pSignalSemaphores", ctypes.POINTER(ctypes.c_uint64)),
    ]


class VkMemoryType(ctypes.Structure):
    _fields_ = [
        ("propertyFlags", ctypes.c_uint32),
        ("heapIndex", ctypes.c_uint32),
    ]


class VkMemoryHeap(ctypes.Structure):
    _fields_ = [
        ("size", ctypes.c_uint64),
        ("flags", ctypes.c_uint32),
    ]


class VkPhysicalDeviceMemoryProperties(ctypes.Structure):
    _fields_ = [
        ("memoryTypeCount", ctypes.c_uint32),
        ("memoryTypes", VkMemoryType * 32),
        ("memoryHeapCount", ctypes.c_uint32),
        ("memoryHeaps", VkMemoryHeap * 16),
    ]


@dataclass
class Buffer:
    buffer: int
    memory: int
    size: int
    mapped_ptr: Optional[ctypes.c_void_p] = None


class VulkanEngine:
    """Minimal Vulkan compute engine for 2-layer MLP inference."""

    def __init__(self, shader_dir: Path):
        self.lib = load_vulkan()
        self.shader_dir = shader_dir
        self.instance = VK_NULL_HANDLE
        self.physical_device = VK_NULL_HANDLE
        self.device = VK_NULL_HANDLE
        self.queue = VK_NULL_HANDLE
        self.queue_family_index = 0
        self.command_pool = VK_NULL_HANDLE
        self.command_buffer = VK_NULL_HANDLE
        self.fence = VK_NULL_HANDLE
        self.pipeline_layout: dict[str, ctypes.c_uint64] = {}
        self.hidden_pipeline = ctypes.c_uint64()
        self.output_pipeline = ctypes.c_uint64()
        self.hidden_shader_module = ctypes.c_uint64()
        self.output_shader_module = ctypes.c_uint64()
        self.descriptor_set_layout: dict[str, ctypes.c_uint64] = {}
        self.descriptor_pool: dict[str, ctypes.c_uint64] = {}
        self.descriptor_set: dict[str, ctypes.c_uint64] = {}
        self.buffers: dict[str, Buffer] = {}
        self.memory_properties = None
        self._initialized = False

        # Network dimensions
        self.input_size = 100
        self.hidden_size = 64
        self.output_size = 4

        # Fixed random weights (deterministic seed)
        np.random.seed(42)
        self.W1 = np.random.randn(self.hidden_size, self.input_size).astype(np.float32) * 0.1
        self.b1 = np.random.randn(self.hidden_size).astype(np.float32) * 0.1
        self.W2 = np.random.randn(self.output_size, self.hidden_size).astype(np.float32) * 0.1
        self.b2 = np.random.randn(self.output_size).astype(np.float32) * 0.1

    def _check(self, result: int, msg: str):
        if result != VK_SUCCESS:
            raise RuntimeError(f"{msg}: VkResult={result}")

    def initialize(self):
        if self._initialized:
            return

        # 1. Create instance
        app_info = VkApplicationInfo()
        app_info.sType = VK_STRUCTURE_TYPE_APPLICATION_INFO
        app_info.pApplicationName = b"FlyBrain"
        app_info.applicationVersion = 1
        app_info.pEngineName = b"FlyBrainEngine"
        app_info.engineVersion = 1
        app_info.apiVersion = VK_API_VERSION_1_0

        create_info = VkInstanceCreateInfo()
        create_info.sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO
        create_info.pApplicationInfo = ctypes.pointer(app_info)

        self.instance = ctypes.c_uint64()
        self._check(self.lib.vkCreateInstance(ctypes.pointer(create_info), None, ctypes.pointer(self.instance)), "vkCreateInstance")

        # 2. Pick physical device
        device_count = ctypes.c_uint32()
        self.lib.vkEnumeratePhysicalDevices(self.instance, ctypes.pointer(device_count), None)
        if device_count.value == 0:
            raise RuntimeError("No Vulkan physical devices found")

        devices = (ctypes.c_uint64 * device_count.value)()
        self.lib.vkEnumeratePhysicalDevices(self.instance, ctypes.pointer(device_count), devices)
        self.physical_device = devices[0]  # Use first

        # 3. Find compute queue family
        queue_count = ctypes.c_uint32()
        self.lib.vkGetPhysicalDeviceQueueFamilyProperties(self.physical_device, ctypes.pointer(queue_count), None)
        queue_props = (VkQueueFamilyProperties * queue_count.value)()
        self.lib.vkGetPhysicalDeviceQueueFamilyProperties(self.physical_device, ctypes.pointer(queue_count), queue_props)

        compute_family = None
        for i in range(queue_count.value):
            if queue_props[i].queueFlags & VK_QUEUE_COMPUTE_BIT:
                compute_family = i
                break

        if compute_family is None:
            raise RuntimeError("No compute queue family found")
        self.queue_family_index = compute_family

        # 4. Create logical device
        queue_priority = ctypes.c_float(1.0)
        queue_create_info = VkDeviceQueueCreateInfo()
        queue_create_info.sType = VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO
        queue_create_info.queueFamilyIndex = self.queue_family_index
        queue_create_info.queueCount = 1
        queue_create_info.pQueuePriorities = ctypes.pointer(queue_priority)

        device_create_info = VkDeviceCreateInfo()
        device_create_info.sType = VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO
        device_create_info.queueCreateInfoCount = 1
        device_create_info.pQueueCreateInfos = ctypes.pointer(queue_create_info)

        self.device = ctypes.c_uint64()
        self._check(self.lib.vkCreateDevice(self.physical_device, ctypes.pointer(device_create_info), None, ctypes.pointer(self.device)), "vkCreateDevice")

        # 5. Get queue
        self.queue = ctypes.c_uint64()
        self.lib.vkGetDeviceQueue(self.device, self.queue_family_index, 0, ctypes.pointer(self.queue))

        # 6. Create command pool
        pool_info = VkCommandPoolCreateInfo()
        pool_info.sType = VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO
        pool_info.flags = VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT
        pool_info.queueFamilyIndex = self.queue_family_index
        self.command_pool = ctypes.c_uint64()
        self._check(self.lib.vkCreateCommandPool(self.device, ctypes.pointer(pool_info), None, ctypes.pointer(self.command_pool)), "vkCreateCommandPool")

        # 7. Allocate command buffer
        alloc_info = VkCommandBufferAllocateInfo()
        alloc_info.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO
        alloc_info.commandPool = self.command_pool
        alloc_info.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY
        alloc_info.commandBufferCount = 1
        self.command_buffer = ctypes.c_uint64()
        self._check(self.lib.vkAllocateCommandBuffers(self.device, ctypes.pointer(alloc_info), ctypes.pointer(self.command_buffer)), "vkAllocateCommandBuffers")

        # 8. Create fence
        fence_info = VkFenceCreateInfo()
        fence_info.sType = VK_STRUCTURE_TYPE_FENCE_CREATE_INFO
        fence_info.flags = VK_FENCE_CREATE_SIGNALED_BIT
        self.fence = ctypes.c_uint64()
        self._check(self.lib.vkCreateFence(self.device, ctypes.pointer(fence_info), None, ctypes.pointer(self.fence)), "vkCreateFence")

        # 9. Create buffers
        self._create_buffers()

        # 10. Create descriptor set layout, pool, set
        self._create_descriptor_set()

        # 11. Create pipelines
        self._create_pipelines()

        self._initialized = True
        print("✅ VulkanEngine initialized")

    def _get_memory_type(self, type_bits: int, properties: int) -> int:
        # Query memory properties using a properly-sized struct
        mem_props = VkPhysicalDeviceMemoryProperties()
        self.lib.vkGetPhysicalDeviceMemoryProperties(self.physical_device, ctypes.pointer(mem_props))

        for i in range(mem_props.memoryTypeCount):
            if (type_bits & (1 << i)) and (mem_props.memoryTypes[i].propertyFlags & properties) == properties:
                return i

        raise RuntimeError(f"No suitable memory type found for type_bits={type_bits}, properties={properties}")

    def _create_buffer(self, name: str, size: int, usage: int, host_visible: bool = True) -> Buffer:
        buf_info = VkBufferCreateInfo()
        buf_info.sType = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO
        buf_info.size = size
        buf_info.usage = usage
        buf_info.sharingMode = 0  # VK_SHARING_MODE_EXCLUSIVE

        buf = ctypes.c_uint64()
        self._check(self.lib.vkCreateBuffer(self.device, ctypes.pointer(buf_info), None, ctypes.pointer(buf)), f"vkCreateBuffer {name}")

        mem_req = VkMemoryRequirements()
        self.lib.vkGetBufferMemoryRequirements(self.device, buf, ctypes.pointer(mem_req))

        props = VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT
        if not host_visible:
            props = VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT

        mem_type = self._get_memory_type(mem_req.memoryTypeBits, props)

        alloc_info = VkMemoryAllocateInfo()
        alloc_info.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO
        alloc_info.allocationSize = mem_req.size
        alloc_info.memoryTypeIndex = mem_type

        mem = ctypes.c_uint64()
        self._check(self.lib.vkAllocateMemory(self.device, ctypes.pointer(alloc_info), None, ctypes.pointer(mem)), f"vkAllocateMemory {name}")

        self._check(self.lib.vkBindBufferMemory(self.device, buf, mem, 0), f"vkBindBufferMemory {name}")

        mapped = ctypes.c_void_p()
        if host_visible:
            self._check(self.lib.vkMapMemory(self.device, mem, 0, VK_WHOLE_SIZE, 0, ctypes.pointer(mapped)), f"vkMapMemory {name}")

        return Buffer(buffer=buf.value, memory=mem.value, size=mem_req.size, mapped_ptr=mapped)

    def _create_buffers(self):
        # Input: 100 floats
        self.buffers["input"] = self._create_buffer("input", self.input_size * 4, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT | VK_BUFFER_USAGE_TRANSFER_DST_BIT)

        # Hidden: 64 floats
        self.buffers["hidden"] = self._create_buffer("hidden", self.hidden_size * 4, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT)

        # Output: 4 floats
        self.buffers["output"] = self._create_buffer("output", self.output_size * 4, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT | VK_BUFFER_USAGE_TRANSFER_SRC_BIT)

        # Weights (host-visible, write once)
        self.buffers["W1"] = self._create_buffer("W1", self.hidden_size * self.input_size * 4, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT)
        self.buffers["b1"] = self._create_buffer("b1", self.hidden_size * 4, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT)
        self.buffers["W2"] = self._create_buffer("W2", self.output_size * self.hidden_size * 4, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT)
        self.buffers["b2"] = self._create_buffer("b2", self.output_size * 4, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT)

        # Upload weights
        self._upload_weights()

    def _upload_weights(self):
        for name, data in [("W1", self.W1), ("b1", self.b1), ("W2", self.W2), ("b2", self.b2)]:
            buf = self.buffers[name]
            if buf.mapped_ptr:
                ctypes.memmove(buf.mapped_ptr, data.ctypes.data, data.nbytes)

    def _create_descriptor_set(self):
        # Two descriptor layouts/sets, one per pipeline stage.
        # hidden.comp: 0=input, 1=W1, 2=b1, 3=hidden
        # output.comp: 0=hidden, 1=W2, 2=b2, 3=output
        layouts = {
            "hidden": [(0, "input"), (1, "W1"), (2, "b1"), (3, "hidden")],
            "output": [(0, "hidden"), (1, "W2"), (2, "b2"), (3, "output")],
        }
        self.descriptor_set_layout = {}
        self.descriptor_pool = {}
        self.descriptor_set = {}
        for stage in ("hidden", "output"):
            bindings = (VkDescriptorSetLayoutBinding * len(layouts[stage]))()
            for i, (binding, _name) in enumerate(layouts[stage]):
                bindings[i].binding = binding
                bindings[i].descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER
                bindings[i].descriptorCount = 1
                bindings[i].stageFlags = VK_SHADER_STAGE_COMPUTE_BIT

            layout_info = VkDescriptorSetLayoutCreateInfo()
            layout_info.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO
            layout_info.pNext = ctypes.c_void_p()
            layout_info.flags = 0
            layout_info.bindingCount = len(layouts[stage])
            layout_info.pBindings = ctypes.cast(bindings, ctypes.POINTER(VkDescriptorSetLayoutBinding))
            layout_handle = ctypes.c_uint64()
            self._check(self.lib.vkCreateDescriptorSetLayout(self.device, ctypes.pointer(layout_info), None, ctypes.byref(layout_handle)), f"vkCreateDescriptorSetLayout {stage}")
            self.descriptor_set_layout[stage] = layout_handle

            pool_sizes = (VkDescriptorPoolSize * 1)()
            pool_sizes[0].type = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER
            pool_sizes[0].descriptorCount = len(layouts[stage])

            pool_info = VkDescriptorPoolCreateInfo()
            pool_info.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO
            pool_info.pNext = ctypes.c_void_p()
            pool_info.flags = 0
            pool_info.maxSets = 1
            pool_info.poolSizeCount = 1
            pool_info.pPoolSizes = pool_sizes
            pool_handle = ctypes.c_uint64()
            self._check(self.lib.vkCreateDescriptorPool(self.device, ctypes.pointer(pool_info), None, ctypes.byref(pool_handle)), f"vkCreateDescriptorPool {stage}")
            self.descriptor_pool[stage] = pool_handle

            alloc_info = VkDescriptorSetAllocateInfo()
            alloc_info.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO
            alloc_info.pNext = ctypes.c_void_p()
            alloc_info.descriptorPool = pool_handle.value
            alloc_info.descriptorSetCount = 1
            alloc_info.pSetLayouts = ctypes.pointer(layout_handle)
            set_handle = ctypes.c_uint64()
            self._check(self.lib.vkAllocateDescriptorSets(self.device, ctypes.pointer(alloc_info), ctypes.byref(set_handle)), f"vkAllocateDescriptorSets {stage}")
            self.descriptor_set[stage] = set_handle

            buffer_infos = []
            for binding, name in layouts[stage]:
                buf = self.buffers[name]
                info = VkDescriptorBufferInfo()
                info.buffer = buf.buffer
                info.offset = 0
                info.range = VK_WHOLE_SIZE
                buffer_infos.append(info)

            writes = (VkWriteDescriptorSet * len(layouts[stage]))()
            for i, ((binding, _name), buf_info) in enumerate(zip(layouts[stage], buffer_infos)):
                writes[i].sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET
                writes[i].dstSet = set_handle.value
                writes[i].dstBinding = binding
                writes[i].descriptorCount = 1
                writes[i].descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER
                writes[i].pBufferInfo = ctypes.pointer(buf_info)

            self.lib.vkUpdateDescriptorSets(self.device, len(layouts[stage]), writes, 0, None)

    def _load_shader(self, path: Path) -> int:
        with open(path, "rb") as f:
            code = f.read()
        if len(code) % 4 != 0:
            raise ValueError(f"SPIR-V size not multiple of 4: {path}")
        code_uint32 = (ctypes.c_uint32 * (len(code) // 4)).from_buffer_copy(code)

        create_info = VkShaderModuleCreateInfo()
        create_info.sType = VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO
        create_info.codeSize = len(code)
        create_info.pCode = code_uint32

        module = ctypes.c_uint64()
        self._check(self.lib.vkCreateShaderModule(self.device, ctypes.pointer(create_info), None, ctypes.pointer(module)), f"vkCreateShaderModule {path}")
        return module.value

    def _create_pipelines(self):
        # Pipeline layout (one per stage, each references its own descriptor set)
        for stage in ("hidden", "output"):
            layout_info = VkPipelineLayoutCreateInfo()
            layout_info.sType = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO
            layout_info.setLayoutCount = 1
            layout_info.pSetLayouts = ctypes.pointer(self.descriptor_set_layout[stage])
            layout_handle = ctypes.c_uint64()
            self._check(self.lib.vkCreatePipelineLayout(self.device, ctypes.pointer(layout_info), None, ctypes.pointer(layout_handle)), f"vkCreatePipelineLayout {stage}")
            self.pipeline_layout[stage] = layout_handle

        # Hidden layer pipeline
        self.hidden_shader_module = self._load_shader(self.shader_dir / "hidden.spv")
        stage_info = VkPipelineShaderStageCreateInfo()
        stage_info.sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO
        stage_info.stage = VK_SHADER_STAGE_COMPUTE_BIT
        stage_info.module = self.hidden_shader_module
        stage_info.pName = b"main"

        pipe_info = VkComputePipelineCreateInfo()
        pipe_info.sType = VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO
        pipe_info.stage = stage_info
        pipe_info.layout = self.pipeline_layout["hidden"].value
        self._check(self.lib.vkCreateComputePipelines(self.device, VK_NULL_HANDLE, 1, ctypes.pointer(pipe_info), None, ctypes.pointer(self.hidden_pipeline)), "vkCreateComputePipelines hidden")

        # Output layer pipeline
        self.output_shader_module = self._load_shader(self.shader_dir / "output.spv")
        stage_info.module = self.output_shader_module
        pipe_info.stage = stage_info
        pipe_info.layout = self.pipeline_layout["output"].value
        self._check(self.lib.vkCreateComputePipelines(self.device, VK_NULL_HANDLE, 1, ctypes.pointer(pipe_info), None, ctypes.pointer(self.output_pipeline)), "vkCreateComputePipelines output")

    def _submit(self) -> None:
        submit_info = VkSubmitInfo()
        submit_info.sType = VK_STRUCTURE_TYPE_SUBMIT_INFO
        submit_info.commandBufferCount = 1
        submit_info.pCommandBuffers = ctypes.pointer(self.command_buffer)
        self._check(self.lib.vkQueueSubmit(self.queue, 1, ctypes.pointer(submit_info), self.fence), "vkQueueSubmit")
        self._check(self.lib.vkWaitForFences(self.device, 1, ctypes.pointer(self.fence), 1, 1_000_000_000), "vkWaitForFences")

    def compute(self, input_grid: np.ndarray) -> np.ndarray:
        """Run inference: input_grid (100,) -> output logits (4,)."""
        if not self._initialized:
            raise RuntimeError("VulkanEngine not initialized")

        # Upload input
        buf = self.buffers["input"]
        ctypes.memmove(buf.mapped_ptr, input_grid.ctypes.data, input_grid.nbytes)

        begin_info = VkCommandBufferBeginInfo()
        begin_info.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO

        # Pass 1: hidden layer (own submission so its writes are visible to pass 2)
        self._check(self.lib.vkResetFences(self.device, 1, ctypes.pointer(self.fence)), "vkResetFences")
        self._check(self.lib.vkBeginCommandBuffer(self.command_buffer, ctypes.pointer(begin_info)), "vkBeginCommandBuffer")
        self.lib.vkCmdBindPipeline(self.command_buffer, VK_PIPELINE_BIND_POINT_COMPUTE, self.hidden_pipeline)
        self.lib.vkCmdBindDescriptorSets(self.command_buffer, VK_PIPELINE_BIND_POINT_COMPUTE, self.pipeline_layout["hidden"], 0, 1, ctypes.pointer(self.descriptor_set["hidden"]), 0, None)
        self.lib.vkCmdDispatch(self.command_buffer, 1, 1, 1)  # 1 workgroup of 64 threads -> 64 hidden units
        self._check(self.lib.vkEndCommandBuffer(self.command_buffer), "vkEndCommandBuffer")
        self._submit()

        # Pass 2: output layer (separate submission: ordering + memory visibility across submissions)
        self._check(self.lib.vkResetFences(self.device, 1, ctypes.pointer(self.fence)), "vkResetFences")
        self._check(self.lib.vkBeginCommandBuffer(self.command_buffer, ctypes.pointer(begin_info)), "vkBeginCommandBuffer")
        self.lib.vkCmdBindPipeline(self.command_buffer, VK_PIPELINE_BIND_POINT_COMPUTE, self.output_pipeline)
        self.lib.vkCmdBindDescriptorSets(self.command_buffer, VK_PIPELINE_BIND_POINT_COMPUTE, self.pipeline_layout["output"], 0, 1, ctypes.pointer(self.descriptor_set["output"]), 0, None)
        self.lib.vkCmdDispatch(self.command_buffer, 1, 1, 1)  # 1 workgroup of 4 threads -> 4 outputs
        self._check(self.lib.vkEndCommandBuffer(self.command_buffer), "vkEndCommandBuffer")
        self._submit()

        # Download output
        out_buf = self.buffers["output"]
        output = np.zeros(self.output_size, dtype=np.float32)
        ctypes.memmove(output.ctypes.data, out_buf.mapped_ptr, output.nbytes)

        return output

    def cleanup(self):
        if not self._initialized:
            return

        self.lib.vkDeviceWaitIdle(self.device)

        for pipeline in [self.hidden_pipeline, self.output_pipeline]:
            if pipeline != VK_NULL_HANDLE:
                self.lib.vkDestroyPipeline(self.device, pipeline, None)

        for module in [self.hidden_shader_module, self.output_shader_module]:
            if module != VK_NULL_HANDLE:
                self.lib.vkDestroyShaderModule(self.device, module, None)

        for layout_handle in self.pipeline_layout.values():
            if layout_handle.value != VK_NULL_HANDLE:
                self.lib.vkDestroyPipelineLayout(self.device, layout_handle, None)

        for layout_handle in self.descriptor_set_layout.values():
            if layout_handle.value != VK_NULL_HANDLE:
                self.lib.vkDestroyDescriptorSetLayout(self.device, layout_handle, None)

        for pool_handle in self.descriptor_pool.values():
            if pool_handle.value != VK_NULL_HANDLE:
                self.lib.vkDestroyDescriptorPool(self.device, pool_handle, None)

        if self.command_pool != VK_NULL_HANDLE:
            self.lib.vkDestroyCommandPool(self.device, self.command_pool, None)

        if self.fence != VK_NULL_HANDLE:
            self.lib.vkDestroyFence(self.device, self.fence, None)

        for buf in self.buffers.values():
            if buf.buffer != VK_NULL_HANDLE:
                self.lib.vkDestroyBuffer(self.device, buf.buffer, None)
            if buf.memory != VK_NULL_HANDLE:
                self.lib.vkFreeMemory(self.device, buf.memory, None)

        if self.device != VK_NULL_HANDLE:
            self.lib.vkDestroyDevice(self.device, None)

        if self.instance != VK_NULL_HANDLE:
            self.lib.vkDestroyInstance(self.instance, None)

        self._initialized = False
        print("🧹 VulkanEngine cleaned up")


# Global singleton
_vulkan_engine: Optional[VulkanEngine] = None


def get_vulkan_engine(shader_dir: Optional[Path] = None) -> VulkanEngine:
    global _vulkan_engine
    if _vulkan_engine is None:
        if shader_dir is None:
            shader_dir = Path(__file__).parent.parent / "shaders"
        _vulkan_engine = VulkanEngine(shader_dir)
        _vulkan_engine.initialize()
    return _vulkan_engine


def shutdown_vulkan_engine():
    global _vulkan_engine
    if _vulkan_engine is not None:
        _vulkan_engine.cleanup()
        _vulkan_engine = None