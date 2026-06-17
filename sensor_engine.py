# -*- coding: utf-8 -*-
import time
import psutil
from datetime import datetime
from loguru import logger

from platform_layer import create_backend
from gpu_detector import detect_gpus, get_gpu_dynamic_data
from models import CpuData, GpuData, RamData, DiskData, SystemData

class SensorEngine:
    def __init__(self):
        logger.info("Initialisation du moteur de capteurs AeroTherm...")
        self.backend = create_backend()
        self.gpus_detected = detect_gpus()
        
        # Variables d'état pour le calcul des débits disques et réseau
        self.last_time = time.time()
        self.last_net_recv = 0.0
        self.last_net_sent = 0.0
        self.last_disk_read = 0.0
        self.last_disk_write = 0.0
        
        # Initialisation des compteurs I/O
        try:
            net_io = psutil.net_io_counters()
            self.last_net_recv = net_io.bytes_recv
            self.last_net_sent = net_io.bytes_sent
        except Exception:
            pass
            
        try:
            disk_io = psutil.disk_io_counters()
            if disk_io:
                self.last_disk_read = disk_io.read_bytes
                self.last_disk_write = disk_io.write_bytes
        except Exception:
            pass

    def collect_all(self) -> SystemData:
        """
        Collecte toutes les données système en temps réel.
        """
        now = time.time()
        dt = now - self.last_time
        if dt <= 0:
            dt = 1.0
        self.last_time = now

        # 1. Collecte CPU
        cpu_info = self.backend.get_cpu_info()
        global_load, per_core_load = self.backend.get_cpu_load()
        main_temp, core_temps = self.backend.get_cpu_temp()
        
        # Fréquence actuelle et max
        freq_curr = 0.0
        freq_max = 0.0
        try:
            freq = psutil.cpu_freq()
            if freq:
                freq_curr = freq.current
                freq_max = freq.max
        except Exception:
            pass

        cpu_data = CpuData(
            name=cpu_info["name"],
            cores_physical=cpu_info["cores_physical"],
            cores_logical=cpu_info["cores_logical"],
            usage_total=global_load,
            usage_per_core=per_core_load,
            temperature_total=main_temp,
            temperature_per_core=core_temps,
            frequency_current=freq_curr,
            frequency_max=freq_max
        )

        # 2. Collecte GPU
        gpus_data = []
        for gpu in self.gpus_detected:
            dyn_data = get_gpu_dynamic_data(gpu)
            gpus_data.append(GpuData(
                name=gpu["name"],
                vendor=gpu["vendor"],
                vram_total=gpu["vram_total"],
                vram_used=dyn_data["vram_used"],
                vram_percent=dyn_data["vram_percent"],
                usage=dyn_data["utilization"],
                temperature=dyn_data["temperature"],
                fan_speed=dyn_data["fan_speed"],
                power_draw=dyn_data["power_draw"]
            ))

        # 3. Collecte RAM
        ram_info = self.backend.get_ram_info()
        ram_data = RamData(
            total=ram_info["total"],
            used=ram_info["used"],
            available=ram_info["available"],
            usage_percent=ram_info["usage_percent"],
            swap_total=ram_info["swap_total"],
            swap_used=ram_info["swap_used"],
            swap_percent=ram_info["swap_percent"]
        )

        # 4. Collecte Débit Réseau (calcul de vitesse en MB/s)
        net_rx_speed = 0.0
        net_tx_speed = 0.0
        try:
            net_io = psutil.net_io_counters()
            net_rx_speed = max(0.0, (net_io.bytes_recv - self.last_net_recv) / dt)
            net_tx_speed = max(0.0, (net_io.bytes_sent - self.last_net_sent) / dt)
            self.last_net_recv = net_io.bytes_recv
            self.last_net_sent = net_io.bytes_sent
        except Exception:
            pass

        # 5. Collecte Débit Global Disques
        disk_r_speed = 0.0
        disk_w_speed = 0.0
        try:
            disk_io = psutil.disk_io_counters()
            if disk_io:
                disk_r_speed = max(0.0, (disk_io.read_bytes - self.last_disk_read) / dt)
                disk_w_speed = max(0.0, (disk_io.write_bytes - self.last_disk_write) / dt)
                self.last_disk_read = disk_io.read_bytes
                self.last_disk_write = disk_io.write_bytes
        except Exception:
            pass

        # 6. Collecte détails disques individuels
        disks_data = []
        raw_disks = self.backend.get_disks_info()
        for d in raw_disks:
            # S.M.A.R.T. et température disque si pySMART disponible (dégradé gracieusement)
            temp_disk = None
            smart_status = "Unknown"
            
            # Pour l'instant, on affecte les vitesses moyennes globales à chaque disque actif (ou 0)
            disks_data.append(DiskData(
                name=d["name"],
                path=d["path"],
                total=d["total"],
                used=d["used"],
                free=d["free"],
                usage_percent=d["usage_percent"],
                interface=d["interface"],
                temperature=temp_disk,
                smart_status=smart_status,
                read_speed=disk_r_speed / (len(raw_disks) or 1),  # Répartition moyenne indicative
                write_speed=disk_w_speed / (len(raw_disks) or 1)
            ))

        # 7. Collecte Batterie
        battery_data = self.backend.get_battery_info()

        # 8. Uptime
        uptime = 0.0
        try:
            uptime = time.time() - psutil.boot_time()
        except Exception:
            pass

        return SystemData(
            cpu=cpu_data,
            gpus=gpus_data,
            ram=ram_data,
            disks=disks_data,
            network={"rx_sec": net_rx_speed, "tx_sec": net_tx_speed},
            battery=battery_data,
            uptime=uptime
        )

if __name__ == "__main__":
    # Test console autonome
    engine = SensorEngine()
    print("Début de la collecte autonome pour test (Ctrl+C pour quitter)...")
    try:
        while True:
            data = engine.collect_all()
            print(f"\n--- Relevé de {data.timestamp.strftime('%H:%M:%S')} ---")
            print(f"CPU : {data.cpu.name} | Charge : {data.cpu.usage_total:.1f}% | Temp : {data.cpu.temperature_total:.1f}°C")
            print(f"RAM : {data.ram.used:.1f}MB / {data.ram.total:.1f}MB ({data.ram.usage_percent:.1f}%)")
            for gpu in data.gpus:
                print(f"GPU : {gpu.name} ({gpu.vendor}) | Charge : {gpu.usage:.1f}% | Temp : {gpu.temperature:.1f}°C")
            for disk in data.disks:
                print(f"Disque : {disk.path} ({disk.name}) | Utilisation : {disk.usage_percent:.1f}%")
            print(f"Réseau : Recu {data.network['rx_sec']/1024:.1f} KB/s | Envoye {data.network['tx_sec']/1024:.1f} KB/s")
            if data.battery["hasBattery"]:
                print(f"Batterie : {data.battery['percent']}% {'(En Charge)' if data.battery['isCharging'] else '(Décharge)'}")
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nTest console arrêté.")
