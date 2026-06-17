# 🌡️ AeroTherm - Cross-Platform Hardware Thermal Monitor (v3.0.0)

[![Python Support](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue?style=flat-square)](https://python.org)
[![Platform Support](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-brightgreen?style=flat-square)](#)

**AeroTherm v3.0.0** est une application de bureau native développée en **Python** avec une interface graphique **PyQt6**. Elle surveille en temps réel l'utilisation, les températures et l'état de santé de vos composants (CPU, GPU, RAM, Disques durs et SSD, Réseau et Batterie).

Cette version intègre un gestionnaire de processus permettant d'agir directement (tuer un processus, modifier sa priorité) en cas de charge thermique excessive.

---

## ✨ Fonctionnalités clés (v3.0.0 Pro Python)

* 🚀 **Moteur d'abstraction OS** : Couche unifiée détectant dynamiquement le système hôte (WMI / LibreHardwareMonitor sous Windows, `/sys/class/` / `lm-sensors` sous Linux).
* 🎮 **Gestion multi-GPU** : Détection dynamique de GPU NVIDIA (NVML), AMD et Intel (lecture de l'utilisation et de la température).
* 📋 **Gestionnaire de processus actif** : Liste en temps réel des processus les plus gourmands en CPU, avec possibilité d'arrêter (`kill`) un processus ou de modifier sa priorité (`nice`) d'un simple clic droit.
* 🌡️ **Seuils d'alertes & notifications** : Personnalisez vos seuils de température ou de charge. Des notifications système (toasts Plyer) vous préviennent en cas de dépassement.
* 💾 **Base de données SQLite** : Historise l'évolution thermique locale et enregistre le journal des alertes.
* 📈 **Graphique historique** : Courbes de température en temps réel haute performance propulsées par `pyqtgraph`.
* 💎 **UI Glassmorphism moderne** : Interface native élégante arborant un thème sombre soigné avec des jauges dessinées vectoriellement.

---

## 🏃‍♂️ Démarrage rapide

### Prérequis

* **Python 3.11+**
* **Linux (Ubuntu/Debian)** :
  ```bash
  sudo apt update && sudo apt install lm-sensors -y
  sudo sensors-detect --auto  # Pour scanner vos capteurs de température
  ```

### Installation

1. Initialisez l'environnement virtuel (optionnel mais recommandé) :
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. Installez les dépendances :
   ```bash
   pip install -r requirements.txt
   ```

### Lancement

Démarrez l'application principale :
```bash
python3 main.py
```

---

## 📁 Architecture du Code

```
thermal-monitor/
├── widgets/
│   ├── gauge_widget.py     # Jauge circulaire personnalisée (QPainter)
│   ├── chart_widget.py     # Graphique en temps réel (pyqtgraph)
│   └── process_table.py    # Tableau interactif des processus
├── config/
│   └── default_config.json # Configuration par défaut
├── data/
│   └── aeotherm.db         # Base de données SQLite locale
├── logs/
│   └── aeotherm.log        # Fichier journal d'AeroTherm (Loguru)
├── platform_layer.py       # Abstraction matérielle OS (Win/Linux)
├── gpu_detector.py         # Détection dynamique des GPUs
├── models.py               # Modèles de données (Dataclasses)
├── sensor_engine.py        # Agrégation des relevés physiques
├── process_manager.py      # Module de contrôle des processus (psutil)
├── alert_manager.py        # Gestion des seuils et alertes
├── scheduler.py            # Thread de collecte en tâche de fond
├── main_window.py          # Fenêtre principale (Feuille de style QSS)
├── main.py                 # Point d'entrée principal
└── requirements.txt        # Dépendances du projet
```

---

## 📄 Licence
Ce projet est sous licence MIT. Fait avec passion pour la sécurité de votre matériel.
