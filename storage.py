# -*- coding: utf-8 -*-
import os
from datetime import datetime, timedelta
from peewee import SqliteDatabase, Model, CharField, FloatField, DateTimeField, BooleanField, IntegerField
from loguru import logger

# Répertoire de données
DB_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, "aeotherm.db")

db = SqliteDatabase(DB_PATH)

class BaseModel(Model):
    class Meta:
        database = db

class Setting(BaseModel):
    key = CharField(unique=True)
    value = CharField()

class ThermalRecord(BaseModel):
    timestamp = DateTimeField(default=datetime.now, index=True)
    cpu_temp = FloatField()
    gpu_temp = FloatField()
    cpu_load = FloatField()
    ram_percent = FloatField()

class AlertRecord(BaseModel):
    timestamp = DateTimeField(default=datetime.now, index=True)
    component = CharField()       # "CPU" | "GPU" | "RAM" | "DISK" | "SYSTEM"
    severity = CharField()        # "WARNING" | "CRITICAL"
    message = CharField()
    value = FloatField()
    threshold = FloatField()
    acknowledged = BooleanField(default=False)

def init_db():
    try:
        db.connect()
        db.create_tables([Setting, ThermalRecord, AlertRecord])
        logger.info(f"Base de données SQLite initialisée à : {DB_PATH}")
        
        # Pré-remplir la table des paramètres à partir du fichier default_config.json si elle est vide
        if Setting.select().count() == 0:
            import json
            config_path = os.path.join(os.path.dirname(__file__), "config", "default_config.json")
            if os.path.exists(config_path):
                try:
                    with open(config_path, "r", encoding="utf-8") as f:
                        defaults = json.load(f)
                    for k, v in defaults.items():
                        Setting.create(key=k, value=str(v))
                    logger.info("Base de données initialisée avec les paramètres par défaut.")
                except Exception as ex:
                    logger.error(f"Erreur de lecture de default_config.json : {ex}")
    except Exception as e:
        logger.error(f"Erreur d'initialisation de la base de données : {e}")

def save_thermal_record(cpu_temp: float, gpu_temp: float, cpu_load: float, ram_percent: float):
    try:
        ThermalRecord.create(
            cpu_temp=cpu_temp,
            gpu_temp=gpu_temp,
            cpu_load=cpu_load,
            ram_percent=ram_percent
        )
    except Exception as e:
        logger.error(f"Impossible de sauvegarder la métrique thermique : {e}")

def save_alert_record(component: str, severity: str, message: str, value: float, threshold: float):
    try:
        AlertRecord.create(
            component=component,
            severity=severity,
            message=message,
            value=value,
            threshold=threshold
        )
    except Exception as e:
        logger.error(f"Impossible de sauvegarder l'alerte : {e}")

def prune_old_data(hours_to_keep: int = 1):
    """
    Supprime les anciens enregistrements de métriques thermiques pour éviter que la base ne grossisse trop.
    """
    try:
        cutoff = datetime.now() - timedelta(hours=hours_to_keep)
        deleted = ThermalRecord.delete().where(ThermalRecord.timestamp < cutoff).execute()
        if deleted > 0:
            logger.debug(f"Nettoyage : {deleted} anciennes mesures supprimées de l'historique.")
    except Exception as e:
        logger.error(f"Erreur lors de la purge de l'historique : {e}")

# Fonctions d'accès aux paramètres
def get_setting(key: str, default: str) -> str:
    try:
        setting = Setting.get(Setting.key == key)
        return setting.value
    except Setting.DoesNotExist:
        return default
    except Exception:
        return default

def set_setting(key: str, value: str):
    try:
        setting, created = Setting.get_or_create(key=key, defaults={"value": value})
        if not created:
            setting.value = value
            setting.save()
    except Exception as e:
        logger.error(f"Impossible de sauvegarder le paramètre {key} : {e}")
