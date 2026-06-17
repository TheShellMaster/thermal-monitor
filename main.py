# -*- coding: utf-8 -*-
import sys
import os
from PyQt6.QtWidgets import QApplication
from loguru import logger

# Configuration du logging
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
logger.add(os.path.join(LOG_DIR, "aeotherm.log"), rotation="5 MB", level="INFO", encoding="utf-8")

from storage import init_db, get_setting
from scheduler import DataScheduler
from main_window import AeroThermMainWindow

def main():
    logger.info("=== Lancement d'AeroTherm ===")
    
    # 1. Initialisation de la base de données SQLite
    init_db()
    
    # 2. Lecture de la configuration d'intervalle
    try:
        interval_str = get_setting("refresh_interval", "1.0")
        interval = float(interval_str)
    except Exception:
        interval = 1.0

    # 3. Démarrage du thread de collecte en arrière-plan
    scheduler = DataScheduler(interval=interval)
    scheduler.start()

    # 4. Lancement de l'IHM PyQt6
    app = QApplication(sys.argv)
    
    # Définition de la police globale de l'application
    font = app.font()
    font.setFamily("Outfit")
    app.setFont(font)
    
    window = AeroThermMainWindow(scheduler)
    window.show()

    # Boucle d'événements Qt
    exit_code = app.exec()
    
    # Arrêt propre du thread de collecte à la fermeture de la fenêtre
    logger.info("Fermeture de l'IHM détectée. Arrêt des services...")
    scheduler.stop()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
