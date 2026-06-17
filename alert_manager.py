# -*- coding: utf-8 -*-
import time
from datetime import datetime
from loguru import logger
from plyer import notification

from models import SystemData, Alert
from storage import save_alert_record, get_setting

class AlertManager:
    def __init__(self):
        # Dictionnaire pour limiter la fréquence des notifications (throttle)
        # Permet de ne pas envoyer des toasts toutes les secondes pour la même alerte
        self.last_notification_time = {}
        self.notification_cooldown = 60.0  # Cooldown en secondes (1 minute)

    def _get_thresholds(self) -> dict:
        """
        Récupère les seuils configurés (soit depuis la BD, soit par défaut).
        """
        return {
            "cpu_temp_warn": float(get_setting("cpu_temp_warn", "75.0")),
            "cpu_temp_crit": float(get_setting("cpu_temp_crit", "90.0")),
            "gpu_temp_warn": float(get_setting("gpu_temp_warn", "80.0")),
            "gpu_temp_crit": float(get_setting("gpu_temp_crit", "95.0")),
            "ram_percent_warn": float(get_setting("ram_percent_warn", "85.0")),
            "ram_percent_crit": float(get_setting("ram_percent_crit", "95.0")),
            "disk_percent_warn": float(get_setting("disk_percent_warn", "90.0")),
            "disk_percent_crit": float(get_setting("disk_percent_crit", "95.0")),
        }

    def check(self, data: SystemData) -> list[Alert]:
        """
        Vérifie si les valeurs collectées dépassent les seuils d'alertes.
        Retourne la liste des alertes déclenchées à cet instant.
        """
        thresholds = self._get_thresholds()
        triggered_alerts = []
        now = datetime.now()

        # 1. Vérification CPU
        cpu_temp = data.cpu.temperature_total
        if cpu_temp > 0:
            if cpu_temp >= thresholds["cpu_temp_crit"]:
                triggered_alerts.append(self._create_alert(
                    "CPU", "CRITICAL", f"Température CPU critique : {cpu_temp:.1f}°C !", cpu_temp, thresholds["cpu_temp_crit"], now
                ))
            elif cpu_temp >= thresholds["cpu_temp_warn"]:
                triggered_alerts.append(self._create_alert(
                    "CPU", "WARNING", f"Température CPU élevée : {cpu_temp:.1f}°C.", cpu_temp, thresholds["cpu_temp_warn"], now
                ))

        # 2. Vérification GPU
        for i, gpu in enumerate(data.gpus):
            gpu_temp = gpu.temperature
            if gpu_temp > 0:
                if gpu_temp >= thresholds["gpu_temp_crit"]:
                    triggered_alerts.append(self._create_alert(
                        f"GPU-{i}", "CRITICAL", f"Température GPU ({gpu.name}) critique : {gpu_temp:.1f}°C !", gpu_temp, thresholds["gpu_temp_crit"], now
                    ))
                elif gpu_temp >= thresholds["gpu_temp_warn"]:
                    triggered_alerts.append(self._create_alert(
                        f"GPU-{i}", "WARNING", f"Température GPU ({gpu.name}) élevée : {gpu_temp:.1f}°C.", gpu_temp, thresholds["gpu_temp_warn"], now
                    ))

        # 3. Vérification RAM
        ram_pct = data.ram.usage_percent
        if ram_pct >= thresholds["ram_percent_crit"]:
            triggered_alerts.append(self._create_alert(
                "RAM", "CRITICAL", f"Mémoire vive saturée : {ram_pct:.1f}% utilisée !", ram_pct, thresholds["ram_percent_crit"], now
            ))
        elif ram_pct >= thresholds["ram_percent_warn"]:
            triggered_alerts.append(self._create_alert(
                "RAM", "WARNING", f"Utilisation RAM élevée : {ram_pct:.1f}%.", ram_pct, thresholds["ram_percent_warn"], now
            ))

        # 4. Vérification Disques
        for disk in data.disks:
            disk_pct = disk.usage_percent
            if disk_pct >= thresholds["disk_percent_crit"]:
                triggered_alerts.append(self._create_alert(
                    f"DISK-{disk.path}", "CRITICAL", f"Espace disque critique sur {disk.path} : {disk_pct:.1f}% !", disk_pct, thresholds["disk_percent_crit"], now
                ))
            elif disk_pct >= thresholds["disk_percent_warn"]:
                triggered_alerts.append(self._create_alert(
                    f"DISK-{disk.path}", "WARNING", f"Espace disque saturé sur {disk.path} : {disk_pct:.1f}%.", disk_pct, thresholds["disk_percent_warn"], now
                ))

        # Traiter les alertes déclenchées (notification toast + enregistrement en base)
        for alert in triggered_alerts:
            self._handle_alert(alert)

        return triggered_alerts

    def _create_alert(self, component: str, severity: str, message: str, value: float, threshold: float, now: datetime) -> Alert:
        # Clé unique pour l'alerte
        alert_id = f"{component}_{severity}_{now.strftime('%Y%m%d%H%M')}"
        return Alert(
            id=alert_id,
            component=component,
            severity=severity,
            message=message,
            value=value,
            threshold=threshold,
            timestamp=now
        )

    def _handle_alert(self, alert: Alert):
        # Sauvegarde en base de données
        save_alert_record(
            component=alert.component,
            severity=alert.severity,
            message=alert.message,
            value=alert.value,
            threshold=alert.threshold
        )

        # Limitation de la fréquence d'affichage des toasts système
        throttle_key = f"{alert.component}_{alert.severity}"
        current_time = time.time()
        
        if throttle_key in self.last_notification_time:
            time_elapsed = current_time - self.last_notification_time[throttle_key]
            if time_elapsed < self.notification_cooldown:
                # Trop précoce pour renvoyer une notification toast
                return

        self.last_notification_time[throttle_key] = current_time

        # Envoi de la notification système (Toast)
        try:
            title = f"⚠️ AeroTherm - Alerte {alert.component}"
            if alert.severity == "CRITICAL":
                title = f"🚨 AeroTherm - Alerte CRITIQUE {alert.component}"

            # Notifications système via Plyer
            notification.notify(
                title=title,
                message=alert.message,
                app_name="AeroTherm",
                timeout=5  # durée d'affichage en secondes
            )
            logger.warning(f"Notification envoyée : {alert.message}")
        except Exception as e:
            logger.error(f"Impossible d'afficher la notification système : {e}")
