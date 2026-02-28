# Physical Hardware Setup

## Enclosures

### Bot Server (Pi 5)

- **Official Raspberry Pi 5 Case** – Active cooling fan included; recommended for continuous operation
- **Argon ONE M.3 Case** – Adds M.2 NVMe SSD support; better for storage-intensive deployments
- Ensure **adequate ventilation** – do not block fan exhaust
- Heat sink required if running without the official case

### Radio Gateway (Pi Zero 2W)

- **Weatherproof/IP65 case** for outdoor deployments
- Ensure **antenna port** is accessible (extend externally if possible)
- Route power cable with strain relief to prevent connector damage
- Keep case away from metal surfaces that could attenuate the LoRa signal

## Antenna Placement

### Best Practices

- Keep LoRa antenna **vertical** (upright) for maximum omnidirectional range
- Avoid placing antenna inside metal enclosures – use an external antenna if possible
- Maintain **line-of-sight** to other LoRa nodes where possible
- Minimum clearance of 30 cm from large metal objects (vehicles, equipment racks)

### Mounting Options

| Option | Range Improvement | Notes |
|--------|------------------|-------|
| Internal antenna (default) | Baseline | Simple; limited by case |
| Pigtail + external whip | +3–6 dB | Best for indoor/outdoor deployments |
| Elevated mounting (pole/mast) | Significant | Each doubling of height increases range |

## Cooling Requirements

### Bot Server (Pi 5 / Pi 4)

- **Active cooling fan required** for continuous operation (LLM inference is CPU-intensive)
- Target CPU temperature: **< 70°C** under sustained load
- Monitor with:

```bash
./scripts/monitoring/monitor_power_temp.sh --once
```

- If temperature exceeds 80°C: add heat sink, improve airflow, or switch to a smaller model

### Radio Gateway (Pi Zero 2W)

- **Passive cooling is sufficient** – typical load is very low
- A small heat sink on the SoC is recommended for warm climates
- Ensure case has ventilation slots if deployed in an enclosure

## Cable Management

### General Guidelines

- Use **quality USB cables** (rated for both data and power delivery)
- For power-critical deployments, prefer cables ≥ 22 AWG for power lines
- **Secure all connections** with cable ties or hot glue where vibration or movement is expected
- Provide **strain relief** at connector entry points – especially important for Pi Zero OTG connections
- Label cables clearly if deploying multiple devices

### Pi 5 Power Cable

The Pi 5 requires a **USB-C cable rated for 5 A** (or the official Pi 5 PSU).
Standard USB-C cables rated for only 3 A will cause under-voltage throttling.

### Pi Zero 2W OTG Connection

- Use a **micro-USB OTG adapter** (male micro-USB to female USB-A) for the LoRa radio
- Alternatively use a powered USB hub if connecting multiple peripherals

## Field Deployment Checklist

Before taking equipment to a field event:

- [ ] All cables securely connected and strain-relieved
- [ ] Enclosures closed and weatherproofed (if outdoor)
- [ ] Antennas positioned vertically and externally (if possible)
- [ ] Temperature test run: `./scripts/monitoring/monitor_power_temp.sh --once`
- [ ] Battery charged (≥ 80% recommended)
- [ ] Pre-deployment check passed: `./scripts/pre_deployment_check.sh`
- [ ] Full integration test passed: `./scripts/testing/test_distributed_integration.sh --bot-server <host>`
- [ ] Spare microSD card with OS image available (for emergencies)
