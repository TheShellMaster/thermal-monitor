# -*- coding: utf-8 -*-
import threading
import time
from loguru import logger

from sensor_engine import SensorEngine
from alert_manager import AlertManager
from storage import save_thermal_record, prune_old_data

class DataScheduler:
    def __init__(self, interval: float = 1.0):
        self.interval = interval
        self.engine = SensorEngine()
        self.alerts = AlertManager()
        self._running = False
        self._thread = None
        self._callbacks = []
        
        # Compteur pour ne pas écrire en base à chaque cycle (ex: écrire toutes les 5s)
        self.db_write_interval = 5.0
        self.last_db_write_time = 0.0
        self.last_prune_time = 0.0
        self.prune_interval = 300.0  # Purger les vieilles données toutes les 5 minutes

    def register_callback(self, callback_fn):
        """
        Permet à l'IHM Qt de s'enregistrer pour recevoir les données actualisées.
        """
        self._callbacks.append(callback_fn)

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info(f"Scheduler démarré. Intervalle de collecte : {self.interval}s")

    def _loop(self):
        while self._running:
            start_cycle = time.time()
            try:
                # 1. Collecte des données matérielles
                data = self.engine.collect_all()
                
                # 2. Vérification des alertes
                triggered_alerts = self.alerts.check(data)
                
                # 3. Enregistrement périodique des données thermiques en base SQLite
                current_time = time.time()
                if current_time - self.last_db_write_time >= self.db_write_interval:
                    gpu_temp = data.gpus[0].temperature if data.gpus else 0.0
                    save_thermal_record(
                        cpu_temp=data.cpu.temperature_total,
                        gpu_temp=gpu_temp,
                        cpu_load=data.cpu.usage_total,
                        ram_percent=data.ram.usage_percent
                    )
                    self.last_db_write_time = current_time

                # 4. Purge périodique de l'historique de la BD (conserver 1 heure par défaut)
                if current_time - self.last_prune_time >= self.prune_interval:
                    prune_old_data(hours_to_keep=1)
                    self.last_prune_time = current_time

                # 5. Transmission des données aux fonctions d'IHM abonnées
                for callback in self._callbacks:
                    try:
                        callback(data, triggered_alerts)
                    except Exception as e:
                        logger.error(f"Erreur callback IHM : {e}")

            except Exception as e:
                logger.error(f"Erreur critique dans la boucle du scheduler : {e}")

            # Calcul du temps restant pour maintenir un intervalle régulier
            elapsed = time.time() - start_cycle
            sleep_time = max(0.01, self.interval - elapsed)
            time.sleep(sleep_time)

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        logger.info("Scheduler arrêté.")
