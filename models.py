# -*- coding: utf-8 -*-
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass
class CpuData:
    name: str
    cores_physical: int
    cores_logical: int
    usage_total: float              # %
    usage_per_core: list[float]     # list of %
    temperature_total: float        # °C
    temperature_per_core: list[float]
    frequency_current: float        # MHz
    frequency_max: float            # MHz
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class GpuData:
    name: str
    vendor: str                     # "NVIDIA" | "AMD" | "Intel" | "Unknown"
    vram_total: float               # MB
    vram_used: float                # MB
    vram_percent: float             # %
    usage: float                    # %
    temperature: float              # °C
    fan_speed: Optional[int] = None # RPM or %
    power_draw: Optional[float] = None # W
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class RamData:
    total: float                    # MB
    used: float                     # MB
    available: float                # MB
    usage_percent: float            # %
    swap_total: float               # MB
    swap_used: float                # MB
    swap_percent: float             # %
    frequency: Optional[int] = None
    type: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class DiskData:
    name: str
    path: str                       # Mountpoint (C:, /, /home...)
    total: float                    # GB
    used: float                     # GB
    free: float                     # GB
    usage_percent: float            # %
    temperature: Optional[float] = None  # °C
    smart_status: str = "Unknown"   # "OK" | "Warning" | "Critical" | "Unknown"
    read_speed: float = 0.0         # MB/s
    write_speed: float = 0.0        # MB/s
    interface: str = "SATA"         # "SATA" | "NVMe" | "USB"
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class ProcessInfo:
    pid: int
    name: str
    cpu_percent: float
    memory_mb: float
    status: str
    priority: str
    exe_path: str
    user: str
    read_bytes_per_sec: float = 0.0
    write_bytes_per_sec: float = 0.0

@dataclass
class SystemData:
    cpu: CpuData
    gpus: list[GpuData]
    ram: RamData
    disks: list[DiskData]
    network: dict                   # {"rx_sec": float, "tx_sec": float}
    battery: dict                   # {"hasBattery": bool, "percent": float, "isCharging": bool}
    uptime: float                   # seconds
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class Alert:
    id: str
    component: str                  # "CPU" | "GPU" | "RAM" | "DISK" | "SYSTEM"
    severity: str                   # "WARNING" | "CRITICAL"
    message: str
    value: float
    threshold: float
    timestamp: datetime = field(default_factory=datetime.now)
    acknowledged: bool = False
