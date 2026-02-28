"""
System monitoring utilities for MCADV.

Provides CPU temperature, throttle detection, power-draw estimation,
and optional battery-level queries.
"""

import os
import subprocess
from typing import Optional


class SystemMonitor:
    """Lightweight hardware monitor suitable for Pi and Ubuntu Desktop."""

    # Paths used on Raspberry Pi / Linux
    _TEMP_PATHS = [
        "/sys/class/thermal/thermal_zone0/temp",
        "/sys/devices/virtual/thermal/thermal_zone0/temp",
    ]
    _THROTTLE_PATH = "/sys/devices/platform/soc/soc:firmware/get_throttled"
    _BATTERY_PATHS = [
        "/sys/class/power_supply/BAT0/capacity",
        "/sys/class/power_supply/BAT1/capacity",
        "/sys/class/power_supply/battery/capacity",
    ]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _read_file(path: str) -> Optional[str]:
        try:
            with open(path) as fh:
                return fh.read().strip()
        except OSError:
            return None

    @staticmethod
    def _run(cmd: list) -> Optional[str]:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            return result.stdout.strip() if result.returncode == 0 else None
        except (OSError, subprocess.TimeoutExpired):
            return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_cpu_temperature(self) -> Optional[float]:
        """
        Return CPU temperature in degrees Celsius, or None if unavailable.

        Tries Linux thermal-zone sysfs files first, then ``vcgencmd``
        (Raspberry Pi firmware tool), then the ``sensors`` command.
        """
        # Linux sysfs (value in millidegrees)
        for path in self._TEMP_PATHS:
            raw = self._read_file(path)
            if raw:
                try:
                    return int(raw) / 1000.0
                except ValueError:
                    pass

        # Raspberry Pi firmware
        out = self._run(["vcgencmd", "measure_temp"])
        if out and out.startswith("temp="):
            try:
                return float(out.split("=")[1].replace("'C", ""))
            except (IndexError, ValueError):
                pass

        # lm-sensors fallback (not all systems have it)
        out = self._run(["sensors", "-j"])
        if out:
            try:
                import json

                data = json.loads(out)
                for chip in data.values():
                    for feature in chip.values():
                        if isinstance(feature, dict):
                            for key, val in feature.items():
                                if "input" in key and isinstance(val, (int, float)):
                                    return float(val)
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                pass

        return None

    def is_throttled(self) -> bool:
        """
        Return True if the Pi is currently CPU/power throttled.

        Uses ``vcgencmd get_throttled``; always returns False on
        non-Raspberry-Pi hardware where the command is unavailable.
        """
        # vcgencmd (Pi only)
        out = self._run(["vcgencmd", "get_throttled"])
        if out and out.startswith("throttled="):
            try:
                val = int(out.split("=")[1], 16)
                # Bits 0-3 indicate active throttle conditions
                return bool(val & 0xF)
            except (IndexError, ValueError):
                pass

        # Sysfs fallback (some Pi kernels expose this)
        raw = self._read_file(self._THROTTLE_PATH)
        if raw:
            try:
                return bool(int(raw, 16) & 0xF)
            except ValueError:
                pass

        return False

    def get_power_draw(self) -> Optional[float]:
        """
        Estimate current power draw in watts.

        Returns a rough estimate based on CPU load and known hardware
        TDP values.  Returns None when estimation is not possible.
        """
        try:
            import psutil  # optional dependency

            cpu_percent = psutil.cpu_percent(interval=0.5)
        except ImportError:
            # Fallback: read /proc/stat manually for a single sample
            stat1 = self._read_file("/proc/stat")
            if not stat1:
                return None
            import time

            time.sleep(0.5)
            stat2 = self._read_file("/proc/stat")
            if not stat2:
                return None
            try:
                vals1 = list(map(int, stat1.splitlines()[0].split()[1:]))
                vals2 = list(map(int, stat2.splitlines()[0].split()[1:]))
                idle1, idle2 = vals1[3], vals2[3]
                total1, total2 = sum(vals1), sum(vals2)
                cpu_percent = (1.0 - (idle2 - idle1) / (total2 - total1)) * 100.0
            except (ValueError, ZeroDivisionError):
                return None

        # Simple linear estimate: idle_watts + load_factor * cpu_percent
        # Values are conservative averages for Pi-class hardware.
        idle_watts = 2.0
        load_factor = 0.08  # ~10 W at 100% CPU load for Pi 5
        return round(idle_watts + load_factor * cpu_percent, 2)

    def get_battery_level(self) -> Optional[int]:
        """
        Return battery capacity as a percentage (0-100), or None.

        Checks standard Linux power-supply sysfs paths.  Returns None
        when no battery or UPS is detected.
        """
        for path in self._BATTERY_PATHS:
            raw = self._read_file(path)
            if raw:
                try:
                    level = int(raw)
                    if 0 <= level <= 100:
                        return level
                except ValueError:
                    pass
        return None

    def get_summary(self) -> dict:
        """Return a dict with all available monitoring data."""
        return {
            "cpu_temperature_c": self.get_cpu_temperature(),
            "is_throttled": self.is_throttled(),
            "estimated_power_w": self.get_power_draw(),
            "battery_percent": self.get_battery_level(),
            "cpu_count": os.cpu_count(),
        }


if __name__ == "__main__":
    import json

    monitor = SystemMonitor()
    print(json.dumps(monitor.get_summary(), indent=2))
