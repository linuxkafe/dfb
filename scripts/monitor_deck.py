#!/usr/bin/env python3
"""Resource monitor for Steam Deck — runs on Deck, streams CSV to stdout."""
import time
import sys
import os
from typing import Optional

import psutil


def read_max_temp() -> Optional[float]:
    """Read maximum temperature from thermal zones in °C."""
    max_temp = None
    thermal_base = "/sys/class/thermal"
    if not os.path.exists(thermal_base):
        return None

    for zone in os.listdir(thermal_base):
        if zone.startswith("thermal_zone"):
            temp_file = os.path.join(thermal_base, zone, "temp")
            try:
                with open(temp_file, "r") as f:
                    temp_milli = int(f.read().strip())
                    temp_c = temp_milli / 1000.0
                    if max_temp is None or temp_c > max_temp:
                        max_temp = temp_c
            except (ValueError, OSError):
                continue
    return max_temp


def read_power_rapl() -> Optional[float]:
    """Try to read package power from RAPL interface in Watts."""
    rapl_base = "/sys/class/powercap"
    if not os.path.exists(rapl_base):
        return None

    for zone in os.listdir(rapl_base):
        if "intel" in zone.lower() or "amd" in zone.lower() or "package" in zone.lower():
            energy_file = os.path.join(rapl_base, zone, "energy_uj")
            name_file = os.path.join(rapl_base, zone, "name")
            try:
                with open(name_file, "r") as f:
                    name = f.read().strip().lower()
                if "package" in name or "core" in name:
                    with open(energy_file, "r") as f:
                        energy_uj = int(f.read().strip())
                    # Return energy in microjoules; caller computes power delta
                    return energy_uj / 1_000_000.0  # Joules
            except (ValueError, OSError):
                continue
    return None


def read_power_amd_hwmon() -> Optional[float]:
    """Try AMD hwmon for power (Steam Deck Van Gogh APU)."""
    hwmon_base = "/sys/class/hwmon"
    if not os.path.exists(hwmon_base):
        return None

    for hwmon in os.listdir(hwmon_base):
        name_file = os.path.join(hwmon_base, hwmon, "name")
        try:
            with open(name_file, "r") as f:
                name = f.read().strip().lower()
            if "k10temp" in name or "amd" in name or "vg" in name:
                # Look for power1_input (µW) or similar
                for f in os.listdir(os.path.join(hwmon_base, hwmon)):
                    if "power" in f and "input" in f:
                        power_file = os.path.join(hwmon_base, hwmon, f)
                        with open(power_file, "r") as pf:
                            return int(pf.read().strip()) / 1_000_000.0  # Watts
        except (ValueError, OSError):
            continue
    return None


def main():
    print("timestamp,cpu_percent,mem_percent,temp_c,power_w", flush=True)

    last_energy = None
    last_time = time.time()

    # Prime CPU percent
    psutil.cpu_percent(interval=0.1)

    while True:
        now = time.time()
        dt = now - last_time
        last_time = now

        cpu = psutil.cpu_percent(interval=0.05)
        mem = psutil.virtual_memory().percent
        temp = read_max_temp()

        # Power: prefer RAPL delta, fallback to hwmon instantaneous
        power = None
        energy = read_power_rapl()
        if energy is not None and last_energy is not None and dt > 0:
            power = (energy - last_energy) / dt  # Watts
        last_energy = energy

        if power is None:
            power = read_power_amd_hwmon()

        print(f"{now:.3f},{cpu:.1f},{mem:.1f},{temp if temp else 'NaN'},{power if power else 'NaN'}", flush=True)

        time.sleep(max(0.0, 1.0 - dt))


if __name__ == "__main__":
    main()