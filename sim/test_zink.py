"""Zink/OpenGL over Vulkan sanity test."""
import os
import sys
import subprocess

def test_zink():
    """Run a minimal GLFW/OpenGL window with Zink."""
    # Ensure Zink is used
    env = os.environ.copy()
    env["MESA_LOADER_DRIVER_OVERRIDE"] = "zink"
    env["GALLIUM_DRIVER"] = "zink"

    # Simple test using glxinfo to verify Zink
    try:
        result = subprocess.run(
            ["glxinfo", "-B"],
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
        )
        print("glxinfo output:")
        print(result.stdout)
        if "zink" in result.stdout.lower():
            print("✅ Zink detected in GL driver")
            return True
        else:
            print("⚠️ Zink not detected")
            return False
    except FileNotFoundError:
        print("glxinfo not installed; install mesa-utils")
        return False
    except subprocess.TimeoutExpired:
        print("glxinfo timed out")
        return False


if __name__ == "__main__":
    ok = test_zink()
    sys.exit(0 if ok else 1)