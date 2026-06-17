# -*- coding: utf-8 -*-
import os
import glob
from loguru import logger

def detect_gpus() -> list[dict]:
    gpus = []

    # 1. Détection NVIDIA via pynvml (officiel et précis)
    try:
        import pynvml
        pynvml.nvmlInit()
        count = pynvml.nvmlDeviceGetCount()
        for i in range(count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            name = pynvml.nvmlDeviceGetName(handle)
            # Décoder si octets
            if isinstance(name, bytes):
                name = name.decode("utf-8", errors="ignore")
            
            # Récupérer la VRAM
            mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            vram_total = mem_info.total / (1024 * 1024)  # MB
            
            gpus.append({
                "vendor": "NVIDIA",
                "name": name,
                "source": "nvml",
                "index": i,
                "handle": handle,
                "vram_total": vram_total
            })
        logger.info(f"Détecté {len(gpus)} GPU(s) NVIDIA via NVML.")
    except Exception as e:
        logger.debug(f"Pas de GPU NVIDIA ou échec NVML : {e}")

    # 2. Détection alternative sous Linux via /sys/class/drm
    if not gpus and os.path.exists("/sys/class/drm"):
        try:
            cards = glob.glob("/sys/class/drm/card[0-9]")
            for card in cards:
                # Lecture des fichiers device/vendor et device/device
                vendor_path = os.path.join(card, "device", "vendor")
                device_path = os.path.join(card, "device", "device")
                if os.path.exists(vendor_path):
                    with open(vendor_path, "r") as f:
                        vendor_id = f.read().strip()
                    
                    vendor = "Unknown"
                    if "0x10de" in vendor_id:
                        vendor = "NVIDIA"
                    elif "0x1002" in vendor_id or "0x1022" in vendor_id:
                        vendor = "AMD"
                    elif "0x8086" in vendor_id:
                        vendor = "Intel"
                    
                    gpus.append({
                        "vendor": vendor,
                        "name": f"GPU Intégré/Dédié ({vendor})",
                        "source": "sysfs",
                        "path": card,
                        "vram_total": 0.0  # Non déterminable facilement par sysfs
                    })
            logger.info(f"Détecté {len(gpus)} GPU(s) via /sys/class/drm.")
        except Exception as e:
            logger.debug(f"Échec de la détection GPU Linux sysfs : {e}")

    # 3. Fallback GPUtil pour NVIDIA
    if not gpus:
        try:
            import GPUtil
            for g in GPUtil.getGPUs():
                gpus.append({
                    "vendor": "NVIDIA",
                    "name": g.name,
                    "source": "gputil",
                    "id": g.id,
                    "vram_total": g.memoryTotal
                })
            logger.info(f"Détecté {len(gpus)} GPU(s) NVIDIA via GPUtil.")
        except Exception as e:
            logger.debug(f"Échec GPUtil : {e}")

    # 4. Fallback générique si rien n'est détecté
    if not gpus:
        logger.info("Aucun GPU dédié détecté, utilisation des données d'affichage de base.")
        # Ajout d'un GPU générique par défaut (souvent Intel/AMD intégré)
        gpus.append({
            "vendor": "Intel/AMD",
            "name": "GPU Intégré",
            "source": "generic",
            "vram_total": 0.0
        })

    return gpus

def get_gpu_dynamic_data(gpu: dict) -> dict:
    """
    Récupère les mesures dynamiques pour un GPU donné.
    """
    data = {
        "utilization": 0.0,
        "temperature": 0.0,
        "vram_used": 0.0,
        "vram_percent": 0.0,
        "fan_speed": None,
        "power_draw": None
    }
    
    source = gpu.get("source")
    
    if source == "nvml":
        try:
            import pynvml
            handle = gpu["handle"]
            
            # Utilisation GPU et mémoire
            try:
                rates = pynvml.nvmlDeviceGetUtilizationRates(handle)
                data["utilization"] = float(rates.gpu)
            except Exception:
                pass
                
            # Température
            try:
                data["temperature"] = float(pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU))
            except Exception:
                pass
                
            # Utilisation VRAM
            try:
                mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                data["vram_used"] = mem_info.used / (1024 * 1024)  # MB
                if gpu["vram_total"] > 0:
                    data["vram_percent"] = (data["vram_used"] / gpu["vram_total"]) * 100
            except Exception:
                pass
                
            # Vitesse ventilateur
            try:
                data["fan_speed"] = int(pynvml.nvmlDeviceGetFanSpeed(handle))
            except Exception:
                pass
                
            # Puissance consommée
            try:
                data["power_draw"] = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0  # Watts
            except Exception:
                pass
                
        except Exception as e:
            logger.error(f"Erreur de lecture dynamique NVML : {e}")

    elif source == "gputil":
        try:
            import GPUtil
            gpus = GPUtil.getGPUs()
            for g in gpus:
                if g.id == gpu.get("id"):
                    data["utilization"] = g.load * 100
                    data["temperature"] = g.temperature
                    data["vram_used"] = g.memoryUsed
                    if g.memoryTotal > 0:
                        data["vram_percent"] = (g.memoryUsed / g.memoryTotal) * 100
                    break
        except Exception:
            pass
            
    elif source == "sysfs" and gpu.get("vendor") == "AMD":
        # Lecture des températures et taux d'utilisation spécifiques d'AMD sous Linux
        path = gpu.get("path")
        try:
            # Chercher dans hwmon de la carte graphique
            hwmon_dirs = glob.glob(os.path.join(path, "device", "hwmon", "hwmon*"))
            if hwmon_dirs:
                temp_file = os.path.join(hwmon_dirs[0], "temp1_input")
                if os.path.exists(temp_file):
                    with open(temp_file, "r") as f:
                        data["temperature"] = float(f.read().strip()) / 1000.0

            # Utilisation
            busy_file = os.path.join(path, "device", "gpu_busy_percent")
            if os.path.exists(busy_file):
                with open(busy_file, "r") as f:
                    data["utilization"] = float(f.read().strip())
        except Exception:
            pass

    return data
