# Power Management Guide

## Power Consumption

### Bot Server

| Hardware | Idle | Load | Peak |
|----------|------|------|------|
| Pi 5 8 GB | ~5 W | ~15 W | ~25 W |
| Pi 4 8 GB | ~3 W | ~10 W | ~15 W |
| Ubuntu Desktop | ~20 W | ~50 W+ | ~100 W+ |

### Radio Gateway

| Component | Power Draw |
|-----------|------------|
| Pi Zero 2W | 0.4–1.5 W |
| LoRa radio (idle) | 0.1 W |
| LoRa radio (TX) | 0.5–1 W |
| **Total** | **1–3 W** |

## Battery Sizing

### Radio Gateway (24-hour operation)

| Parameter | Value |
|-----------|-------|
| Average power | 2.5 W |
| Daily consumption | 60 Wh |
| Recommended battery | 20,000 mAh USB bank |
| Estimated runtime | ~30 hours |

### Bot Server – Pi 5 (8-hour event)

| Parameter | Value |
|-----------|-------|
| Average power | 12 W |
| Event consumption | 96 Wh |
| Recommended battery | 25,000 mAh USB-C PD (65 W+) |
| Estimated runtime | ~8–10 hours |

## Recommended Hardware

### Radio Gateway Power Supply

| Product Type | Capacity | Suitable For |
|-------------|----------|-------------|
| USB battery bank (USB-A, ≥10,000 mAh) | 37–74 Wh | 12–30 hr runtime |
| USB-C battery bank (20,000 mAh) | 74 Wh | ~30 hr runtime |
| Solar panel (5 V, 5–10 W) | N/A | Indefinite outdoor operation |

### Bot Server (Pi 5) Power Supply

| Product Type | Notes |
|-------------|-------|
| Official Pi 5 USB-C PSU (5 V 5 A) | Required for full performance |
| USB-C PD battery bank (65 W, 25,000 mAh) | ~8–10 hr field operation |
| Laptop-grade UPS with USB-C PD | Best for indoor events |

## Power Monitoring

Monitor power and temperature in real time:

```bash
# One-shot check
./scripts/monitoring/monitor_power_temp.sh --once

# Continuous monitoring (refreshes every 30 s)
./scripts/monitoring/monitor_power_temp.sh

# Custom refresh interval
./scripts/monitoring/monitor_power_temp.sh --interval 60
```

Key metrics reported:
- CPU temperature (°C)
- Throttle state (Pi-specific via `vcgencmd`)
- Estimated power draw (W)
- Battery level (% – if UPS detected)

## Temperature Limits

| Alert Level | Temperature | Action |
|-------------|-------------|--------|
| Normal | < 70°C | No action required |
| Warning | 70–79°C | Improve cooling/airflow |
| Critical | ≥ 80°C | Reduce load or add active cooling |

## Reducing Power Consumption

### Pi 5 / Pi 4

```bash
# Disable unused interfaces
sudo raspi-config nonint do_bluetooth 1   # Disable Bluetooth
sudo raspi-config nonint do_camera 1      # Disable camera interface

# Use a smaller Ollama model
ollama pull llama3.2:1b    # ~2 W less than llama3.1:8b under load
```

### Pi Zero 2W

```bash
# Disable HDMI output (saves ~30 mW)
sudo tvservice -o

# Disable unused interfaces in /boot/config.txt
dtoverlay=disable-bt
dtparam=camera_auto_detect=0
```

## Solar Power Considerations

For extended outdoor deployments:

- **Radio Gateway:** A 10 W solar panel with a 20,000 mAh battery provides indefinite runtime in sunny conditions.
- **Bot Server (Pi 5):** Requires a 30–50 W solar panel plus large battery bank due to higher load.
- Ensure the solar charge controller supports 5 V output or use a USB PD trigger module.
