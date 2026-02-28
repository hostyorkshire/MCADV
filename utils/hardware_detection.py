"""
Hardware role detection utilities for MCADV.

Detects whether this device is a bot server (Pi 4/5 or Ubuntu Desktop)
or a radio gateway (Pi Zero 2W).
"""

import os
import platform
import subprocess
from typing import Dict, Optional


def _read_file(path: str) -> Optional[str]:
    """Read a file and return its contents, or None on error."""
    try:
        with open(path) as fh:
            return fh.read().strip()
    except OSError:
        return None


def _get_pi_model() -> Optional[str]:
    """Return Raspberry Pi model string from /proc/device-tree/model, or None."""
    return _read_file("/proc/device-tree/model")


def _is_ubuntu_desktop() -> bool:
    """Return True if this looks like an Ubuntu Desktop system."""
    if platform.system() != "Linux":
        return False
    os_release = _read_file("/etc/os-release") or ""
    return "ubuntu" in os_release.lower()


def _process_running(name: str) -> bool:
    """Return True if a process matching *name* is currently running."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", name],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    except OSError:
        return False


def detect_hardware_role() -> str:
    """
    Detect if this device is a bot server or radio gateway.

    Returns:
        "bot_server"    – Pi 4, Pi 5, or Ubuntu Desktop
        "radio_gateway" – Pi Zero 2W
        "unknown"       – cannot determine
    """
    pi_model = _get_pi_model()

    if pi_model:
        model_lower = pi_model.lower()
        if "zero 2" in model_lower:
            return "radio_gateway"
        if any(tag in model_lower for tag in ("pi 4", "pi 5", "pi3")):
            return "bot_server"

    if _is_ubuntu_desktop():
        return "bot_server"

    # Fall back to process heuristics
    if _process_running("radio_gateway.py"):
        return "radio_gateway"
    if _process_running("adventure_bot.py"):
        return "bot_server"

    return "unknown"


def get_hardware_info() -> Dict[str, object]:
    """
    Return a dictionary describing the current hardware.

    Keys:
        platform  – "pi_zero_2w", "pi_4", "pi_5", "ubuntu_desktop", or "unknown"
        role      – "bot_server", "radio_gateway", or "unknown"
        ram_mb    – total RAM in MB (int)
        cpu_count – number of logical CPU cores (int)
    """
    pi_model = _get_pi_model()
    hw_platform = "unknown"

    if pi_model:
        model_lower = pi_model.lower()
        if "zero 2" in model_lower:
            hw_platform = "pi_zero_2w"
        elif "pi 5" in model_lower:
            hw_platform = "pi_5"
        elif "pi 4" in model_lower:
            hw_platform = "pi_4"
        elif "pi 3" in model_lower:
            hw_platform = "pi_3"
    elif _is_ubuntu_desktop():
        hw_platform = "ubuntu_desktop"

    # RAM
    ram_mb = 0
    meminfo = _read_file("/proc/meminfo")
    if meminfo:
        for line in meminfo.splitlines():
            if line.startswith("MemTotal:"):
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        ram_mb = int(parts[1]) // 1024
                    except ValueError:
                        pass
                break

    # CPU count
    try:
        cpu_count = os.cpu_count() or 0
    except AttributeError:
        cpu_count = 0

    return {
        "platform": hw_platform,
        "role": detect_hardware_role(),
        "ram_mb": ram_mb,
        "cpu_count": cpu_count,
    }


def print_hardware_banner() -> None:
    """Print a colour-coded banner showing the detected hardware role."""
    GREEN = "\033[0;32m"
    BLUE = "\033[0;34m"
    YELLOW = "\033[1;33m"
    NC = "\033[0m"

    info = get_hardware_info()
    role = info["role"]
    hw_platform = info["platform"]

    platform_labels = {
        "pi_zero_2w": "Pi Zero 2W",
        "pi_5": "Pi 5",
        "pi_4": "Pi 4",
        "pi_3": "Pi 3",
        "ubuntu_desktop": "Ubuntu Desktop",
        "unknown": "Unknown Hardware",
    }
    label = platform_labels.get(str(hw_platform), str(hw_platform))

    if role == "bot_server":
        colour = GREEN
        role_label = "BOT SERVER"
    elif role == "radio_gateway":
        colour = BLUE
        role_label = "RADIO GATEWAY"
    else:
        colour = YELLOW
        role_label = "UNKNOWN ROLE"

    border = "=" * 50
    print(f"\n{colour}{border}{NC}")
    print(f"{colour}  Hardware Role: [{role_label} - {label}]{NC}")
    print(f"{colour}  RAM: {info['ram_mb']} MB  |  CPUs: {info['cpu_count']}{NC}")
    print(f"{colour}{border}{NC}\n")


if __name__ == "__main__":
    print_hardware_banner()
    import json

    print(json.dumps(get_hardware_info(), indent=2))
