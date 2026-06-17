# -*- coding: utf-8 -*-
import sys
import os
import platform
import psutil
from loguru import logger

def get_platform():
    s = sys.platform
    if s.startswith("win"):
        return "windows"
    if s.startswith("linux"):
        return "linux"
    if s.startswith("darwin"):
        return "macos"
    return "unknown"

class HardwareBackend:
    """
    Classe de base - définit l'interface d'accès matériel commune à tous les OS.
    """
    def __init__(self):
        logger.info(f"Initialisation du backend générique sur {platform.system()}")

    def get_cpu_info(self) -> dict:
        try:
            import cpuinfo
            info = cpuinfo.get_cpu_info()
            brand = info.get("brand_raw", "Processeur inconnu")
            hz = info.get("hz_advertised_friendly", "N/A")
            arch = info.get("arch", "Unknown")
        except Exception as e:
            logger.warning(f"Impossible d'importer cpuinfo : {e}")
            brand = "Processeur Générique"
            hz = "N/A"
            arch = platform.machine()

        return {
            "name": brand,
            "cores_physical": psutil.cpu_count(logical=False) or 1,
            "cores_logical": psutil.cpu_count(logical=True) or 1,
            "frequency_base": hz,
            "architecture": arch
        }

    def get_cpu_load(self) -> tuple[float, list[float]]:
        try:
            # Récupère l'utilisation globale et par cœur
            global_load = psutil.cpu_percent(interval=None)
            per_core = psutil.cpu_percent(interval=None, percpu=True)
            return global_load, per_core
        except Exception as e:
            logger.error(f"Erreur de lecture de la charge CPU : {e}")
            return 0.0, []

    def get_cpu_temp(self) -> tuple[float, list[float]]:
        # Backend générique : retourne 0.0
        return 0.0, []

    def get_ram_info(self) -> dict:
        try:
            mem = psutil.virtual_memory()
            swap = psutil.swap_memory()
            return {
                "total": mem.total / (1024 * 1024),  # MB
                "used": mem.used / (1024 * 1024),    # MB
                "available": mem.available / (1024 * 1024), # MB
                "usage_percent": mem.percent,
                "swap_total": swap.total / (1024 * 1024),
                "swap_used": swap.used / (1024 * 1024),
                "swap_percent": swap.percent,
                "frequency": None,
                "type": None
            }
        except Exception as e:
            logger.error(f"Erreur RAM : {e}")
            return {"total": 0, "used": 0, "available": 0, "usage_percent": 0.0}

    def get_disks_info(self) -> list[dict]:
        disks = []
        try:
            for part in psutil.disk_partitions(all=False):
                if not part.device or 'loop' in part.device or 'ram' in part.device:
                    continue
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    disks.append({
                        "name": part.device,
                        "path": part.mountpoint,
                        "total": usage.total / (1024 * 1024 * 1024),  # GB
                        "used": usage.used / (1024 * 1024 * 1024),    # GB
                        "free": usage.free / (1024 * 1024 * 1024),    # GB
                        "usage_percent": usage.percent,
                        "interface": "SATA/NVMe" if "nvme" in part.device else "SATA",
                        "temperature": None,
                        "smart_status": "Unknown"
                    })
                except Exception:
                    continue
        except Exception as e:
            logger.error(f"Erreur partitions disques : {e}")
        return disks

    def get_net_info(self) -> tuple[float, float]:
        try:
            # Retourne les octets totaux (envoyés, reçus) pour calcul ultérieur de vitesse
            counters = psutil.net_io_counters()
            return counters.bytes_recv, counters.bytes_sent
        except Exception as e:
            logger.error(f"Erreur réseau : {e}")
            return 0.0, 0.0

    def get_battery_info(self) -> dict:
        try:
            batt = psutil.sensors_battery()
            if batt:
                return {
                    "hasBattery": True,
                    "isCharging": batt.power_plugged,
                    "percent": batt.percent,
                    "secsleft": batt.secsleft
                }
        except Exception as e:
            logger.debug(f"Erreur capteur batterie : {e}")
        return {"hasBattery": False, "isCharging": False, "percent": 0}

    def get_gpu_info(self) -> list[dict]:
        return []

    def get_motherboard_info(self) -> dict:
        return {
            "manufacturer": "N/A",
            "model": "N/A",
            "bios_version": "N/A",
            "fan_speeds": [],
            "voltages": {}
        }


class LinuxBackend(HardwareBackend):
    """
    Implémentation spécifique pour Linux (lm-sensors, sysfs, psutil).
    """
    def __init__(self):
        super().__init__()
        logger.info("Configuration du backend matériel Linux...")

    def get_cpu_temp(self) -> tuple[float, list[float]]:
        main_temp = 0.0
        core_temps = []
        try:
            temps = psutil.sensors_temperatures()
            # Chercher dans l'ordre de priorité
            for key in ("coretemp", "k10temp", "acpitz", "cpu_thermal"):
                if key in temps:
                    sensor_list = temps[key]
                    for sensor in sensor_list:
                        # Si c'est le package ou la température globale
                        if "Package" in sensor.label or not sensor.label:
                            if main_temp == 0.0:
                                main_temp = sensor.current
                        # Si c'est un cœur individuel
                        if "Core" in sensor.label:
                            core_temps.append(sensor.current)
                    
                    # Fallback si pas de température package trouvée
                    if main_temp == 0.0 and sensor_list:
                        main_temp = sensor_list[0].current
                    break
        except Exception as e:
            logger.error(f"Erreur lors de la lecture des températures Linux : {e}")
        
        return main_temp, core_temps

    def get_motherboard_info(self) -> dict:
        fan_speeds = []
        try:
            # Récupérer la vitesse des ventilateurs via psutil
            fans = psutil.sensors_fans()
            for key in fans:
                for fan in fans[key]:
                    fan_speeds.append({"name": fan.label or key, "speed": fan.current})
        except Exception as e:
            logger.debug(f"Pas de ventilateurs détectés via psutil : {e}")
        
        # Récupération basique du fabriquant de carte mère depuis sysfs
        manufacturer = "N/A"
        model = "N/A"
        try:
            if os.path.exists("/sys/class/dmi/id/board_vendor"):
                with open("/sys/class/dmi/id/board_vendor", "r") as f:
                    manufacturer = f.read().strip()
            if os.path.exists("/sys/class/dmi/id/board_name"):
                with open("/sys/class/dmi/id/board_name", "r") as f:
                    model = f.read().strip()
        except Exception:
            pass

        return {
            "manufacturer": manufacturer,
            "model": model,
            "bios_version": "N/A",
            "fan_speeds": fan_speeds,
            "voltages": {}
        }


class WindowsBackend(HardwareBackend):
    """
    Implémentation spécifique pour Windows (LibreHardwareMonitor via pythonnet, WMI, psutil).
    """
    def __init__(self):
        super().__init__()
        logger.info("Configuration du backend matériel Windows...")
        self._lhm = self._try_load_lhm()
        self._wmi = self._try_load_wmi()

    def _try_load_lhm(self):
        try:
            import clr
            # Cherche la DLL localement dans le répertoire de l'application
            dll_path = os.path.join(os.path.dirname(__file__), "LibreHardwareMonitorLib.dll")
            if os.path.exists(dll_path):
                clr.AddReference(dll_path)
                from LibreHardwareMonitor.Hardware import Computer
                c = Computer()
                c.IsCpuEnabled = True
                c.IsGpuEnabled = True
                c.IsMemoryEnabled = True
                c.IsMotherboardEnabled = True
                c.IsStorageEnabled = True
                c.Open()
                logger.info("LibreHardwareMonitor chargé avec succès !")
                return c
            else:
                logger.warning("LibreHardwareMonitorLib.dll introuvable.")
                return None
        except Exception as e:
            logger.warning(f"Échec de l'initialisation de LibreHardwareMonitor : {e}")
            return None

    def _try_load_wmi(self):
        try:
            import wmi
            return wmi.WMI()
        except Exception as e:
            logger.warning(f"Échec du chargement de l'API WMI Windows : {e}")
            return None

    def get_cpu_temp(self) -> tuple[float, list[float]]:
        main_temp = 0.0
        core_temps = []
        
        # Essayer via LibreHardwareMonitor d'abord
        if self._lhm:
            try:
                for hardware in self._lhm.Hardware:
                    if hardware.HardwareType.ToString() == "Cpu":
                        hardware.Update()
                        for sensor in hardware.Sensors:
                            if sensor.SensorType.ToString() == "Temperature":
                                if "Core" in sensor.Name:
                                    core_temps.append(sensor.Value)
                                elif "Package" in sensor.Name or main_temp == 0.0:
                                    main_temp = sensor.Value
                        break
            except Exception as e:
                logger.debug(f"Erreur LHM CPU Temp : {e}")

        # Fallback via WMI
        if main_temp == 0.0 and self._wmi:
            try:
                # Lecture de MSAcpi_ThermalZoneTemperature (retourne en dixièmes de Kelvin)
                for tz in self._wmi.MSAcpi_ThermalZoneTemperature():
                    temp_c = (tz.CurrentTemperature / 10.0) - 273.15
                    if 0 < temp_c < 120:
                        main_temp = temp_c
                        break
            except Exception:
                pass

        return main_temp, core_temps

    def get_motherboard_info(self) -> dict:
        fan_speeds = []
        manufacturer = "N/A"
        model = "N/A"
        
        if self._lhm:
            try:
                for hardware in self._lhm.Hardware:
                    if hardware.HardwareType.ToString() == "Motherboard":
                        hardware.Update()
                        for sensor in hardware.Sensors:
                            if sensor.SensorType.ToString() == "Fan":
                                fan_speeds.append({"name": sensor.Name, "speed": sensor.Value})
            except Exception:
                pass
                
        if self._wmi:
            try:
                for bb in self._wmi.Win32_BaseBoard():
                    manufacturer = bb.Manufacturer
                    model = bb.Product
                    break
            except Exception:
                pass
                
        return {
            "manufacturer": manufacturer,
            "model": model,
            "bios_version": "N/A",
            "fan_speeds": fan_speeds,
            "voltages": {}
        }


def create_backend() -> HardwareBackend:
    """
    Factory - retourne le backend adapté à l'OS.
    """
    plat = get_platform()
    if plat == "linux":
        return LinuxBackend()
    elif plat == "windows":
        return WindowsBackend()
    return HardwareBackend()
