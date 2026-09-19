#!/usr/bin/env python3
"""Debug Vulkan queue families on Deck."""
import ctypes

# Load vulkan
lib = ctypes.CDLL('libvulkan.so.1')

# Define minimal structures
class VkApplicationInfo(ctypes.Structure):
    _fields_ = [
        ('sType', ctypes.c_int),
        ('pNext', ctypes.c_void_p),
        ('pApplicationName', ctypes.c_char_p),
        ('applicationVersion', ctypes.c_uint32),
        ('pEngineName', ctypes.c_char_p),
        ('engineVersion', ctypes.c_uint32),
        ('apiVersion', ctypes.c_uint32),
    ]

class VkInstanceCreateInfo(ctypes.Structure):
    _fields_ = [
        ('sType', ctypes.c_int),
        ('pNext', ctypes.c_void_p),
        ('flags', ctypes.c_uint32),
        ('pApplicationInfo', ctypes.POINTER(VkApplicationInfo)),
        ('enabledLayerCount', ctypes.c_uint32),
        ('ppEnabledLayerNames', ctypes.POINTER(ctypes.c_char_p)),
        ('enabledExtensionCount', ctypes.c_uint32),
        ('ppEnabledExtensionNames', ctypes.POINTER(ctypes.c_char_p)),
    ]

class VkQueueFamilyProperties(ctypes.Structure):
    _fields_ = [
        ('queueFlags', ctypes.c_uint32),
        ('queueCount', ctypes.c_uint32),
        ('timestampValidBits', ctypes.c_uint32),
        ('minImageTransferGranularity', ctypes.c_uint32 * 3),
    ]

VK_STRUCTURE_TYPE_APPLICATION_INFO = 0
VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO = 1
VK_API_VERSION_1_0 = 0

app_info = VkApplicationInfo()
app_info.sType = VK_STRUCTURE_TYPE_APPLICATION_INFO
app_info.pApplicationName = b'Test'
app_info.applicationVersion = 1
app_info.pEngineName = b'Test'
app_info.engineVersion = 1
app_info.apiVersion = VK_API_VERSION_1_0

create_info = VkInstanceCreateInfo()
create_info.sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO
create_info.pApplicationInfo = ctypes.pointer(app_info)

instance = ctypes.c_uint64()
lib.vkCreateInstance.argtypes = [ctypes.POINTER(VkInstanceCreateInfo), ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint64)]
lib.vkCreateInstance.restype = ctypes.c_int

result = lib.vkCreateInstance(ctypes.pointer(create_info), None, ctypes.pointer(instance))
print(f'vkCreateInstance: {result}')

# Enumerate physical devices
device_count = ctypes.c_uint32()
lib.vkEnumeratePhysicalDevices.argtypes = [ctypes.c_uint64, ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_uint64)]
lib.vkEnumeratePhysicalDevices.restype = ctypes.c_int

lib.vkEnumeratePhysicalDevices(instance, ctypes.pointer(device_count), None)
print(f'Device count: {device_count.value}')

devices = (ctypes.c_uint64 * device_count.value)()
lib.vkEnumeratePhysicalDevices(instance, ctypes.pointer(device_count), devices)
physical_device = devices[0]

# Get queue family properties
queue_count = ctypes.c_uint32()
lib.vkGetPhysicalDeviceQueueFamilyProperties.argtypes = [ctypes.c_uint64, ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(VkQueueFamilyProperties)]
lib.vkGetPhysicalDeviceQueueFamilyProperties.restype = None

lib.vkGetPhysicalDeviceQueueFamilyProperties(physical_device, ctypes.pointer(queue_count), None)
print(f'Queue family count: {queue_count.value}')

queue_props = (VkQueueFamilyProperties * queue_count.value)()
lib.vkGetPhysicalDeviceQueueFamilyProperties(physical_device, ctypes.pointer(queue_count), queue_props)

for i in range(queue_count.value):
    flags = queue_props[i].queueFlags
    count = queue_props[i].queueCount
    print(f'Queue family {i}: flags=0x{flags:08x} ({flags}), count={count}')
    if flags & 0x00000020:
        print(f'  -> HAS COMPUTE_BIT')