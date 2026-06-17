# -*- coding: utf-8 -*-
from PyQt6.QtWidgets import (QMainWindow, QWidget, QTabWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QGridLayout, QGroupBox, 
                             QFormLayout, QSlider, QCheckBox, QPushButton, 
                             QListWidget, QMessageBox, QComboBox)
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QFont, QIcon, QColor

from models import SystemData
from scheduler import DataScheduler
from widgets.gauge_widget import CircularGaugeWidget
from widgets.chart_widget import ThermalHistoryChart
from widgets.process_table import ProcessTableWidget
from storage import get_setting, set_setting

class AeroThermMainWindow(QMainWindow):
    def __init__(self, scheduler: DataScheduler):
        super().__init__()
        self.scheduler = scheduler
        self.max_cpu_temp = 0.0
        self.max_gpu_temp = 0.0
        
        self.init_ui()
        
        # Enregistrement du callback de données
        self.scheduler.register_callback(self.on_data_received)

    def init_ui(self):
        self.setWindowTitle("AeroTherm | Surveillance Thermique & Matérielle")
        self.resize(1200, 850)
        self.setMinimumSize(1000, 750)
        
        # Chargement du style QSS global (Sombre, Glassmorphism, Premium)
        self.apply_premium_stylesheet()

        # Widget Central contenant les onglets
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Création des onglets
        self.tab_overview = QWidget()
        self.tab_cpu = QWidget()
        self.tab_gpus = QWidget()
        self.tab_storage = QWidget()
        self.tab_processes = QWidget()
        self.tab_alerts = QWidget()
        self.tab_settings = QWidget()

        self.tabs.addTab(self.tab_overview, "🖥️ Vue d'ensemble")
        self.tabs.addTab(self.tab_cpu, "⚙️ CPU")
        self.tabs.addTab(self.tab_gpus, "🎮 GPU")
        self.tabs.addTab(self.tab_storage, "🗄️ Stockage")
        self.tabs.addTab(self.tab_processes, "📋 Processus")
        self.tabs.addTab(self.tab_alerts, "🔔 Alertes actives")
        self.tabs.addTab(self.tab_settings, "⚙️ Paramètres")

        # Initialisation de chaque onglet
        self.init_overview_tab()
        self.init_cpu_tab()
        self.init_gpu_tab()
        self.init_storage_tab()
        self.init_processes_tab()
        self.init_alerts_tab()
        self.init_settings_tab()

    def init_overview_tab(self):
        layout = QGridLayout(self.tab_overview)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # 1. Jauges principales (Ligne 0, Colonnes 0-2)
        gauges_widget = QWidget()
        gauges_widget.setObjectName("OverviewGaugesCard")
        gauges_layout = QHBoxLayout(gauges_widget)
        
        self.gauge_temp = CircularGaugeWidget("Température CPU", "°C")
        self.gauge_load = CircularGaugeWidget("Charge CPU", "%")
        self.gauge_ram = CircularGaugeWidget("Utilisation RAM", "%")
        
        gauges_layout.addWidget(self.gauge_temp)
        gauges_layout.addWidget(self.gauge_load)
        gauges_layout.addWidget(self.gauge_ram)
        
        layout.addWidget(gauges_widget, 0, 0, 1, 3)

        # 2. Infos Matérielles Statiques (Ligne 1, Colonne 0)
        info_card = QGroupBox("Informations Système")
        info_card.setObjectName("SystemInfoCard")
        info_layout = QFormLayout(info_card)
        info_layout.setSpacing(12)
        
        self.lbl_os = QLabel("Détection...")
        self.lbl_cpu_name = QLabel("Détection...")
        self.lbl_host = QLabel("Détection...")
        self.lbl_uptime = QLabel("Détection...")
        
        info_layout.addRow("Système :", self.lbl_os)
        info_layout.addRow("Processeur :", self.lbl_cpu_name)
        info_layout.addRow("Hôte :", self.lbl_host)
        info_layout.addRow("Uptime :", self.lbl_uptime)
        
        layout.addWidget(info_card, 1, 0, 1, 1)

        # 3. Graphique Historique (Ligne 1, Colonnes 1-2)
        chart_card = QWidget()
        chart_card.setObjectName("ChartCard")
        chart_layout = QVBoxLayout(chart_card)
        
        self.chart = ThermalHistoryChart()
        chart_layout.addWidget(self.chart)
        
        layout.addWidget(chart_card, 1, 1, 1, 2)

        # 4. Flux Réseau & Stockage mini-list (Ligne 2, Colonnes 0-1)
        net_card = QGroupBox("Réseau & Disques")
        net_card.setObjectName("NetCard")
        net_layout = QFormLayout(net_card)
        net_layout.setSpacing(10)
        
        self.lbl_net_down = QLabel("0 KB/s")
        self.lbl_net_up = QLabel("0 KB/s")
        self.lbl_disks_list = QLabel("Détection...")
        
        net_layout.addRow("Téléchargement :", self.lbl_net_down)
        net_layout.addRow("Téléversement :", self.lbl_net_up)
        net_layout.addRow("Disques montés :", self.lbl_disks_list)
        
        layout.addWidget(net_card, 2, 0, 1, 2)

        # 5. Capteurs Additionnels (Ligne 2, Colonne 2)
        extra_card = QGroupBox("Capteurs Thermiques")
        extra_card.setObjectName("ExtraSensorsCard")
        extra_layout = QVBoxLayout(extra_card)
        
        self.lbl_extra_sensors = QLabel("Aucun capteur additionnel détecté.")
        self.lbl_extra_sensors.setWordWrap(True)
        extra_layout.addWidget(self.lbl_extra_sensors)
        
        layout.addWidget(extra_card, 2, 2, 1, 1)

        # Configuration d'échelle de la grille
        layout.setRowStretch(0, 2)
        layout.setRowStretch(1, 3)
        layout.setRowStretch(2, 2)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(2, 1)

    def init_cpu_tab(self):
        layout = QVBoxLayout(self.tab_cpu)
        layout.setContentsMargins(15, 15, 15, 15)
        
        self.lbl_cpu_detail = QLabel("Détails d'utilisation par cœur du processeur :")
        self.lbl_cpu_detail.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(self.lbl_cpu_detail)

        self.cpu_cores_list = QListWidget()
        layout.addWidget(self.cpu_cores_list)

    def init_gpu_tab(self):
        layout = QVBoxLayout(self.tab_gpus)
        layout.setContentsMargins(15, 15, 15, 15)
        
        self.lbl_gpu_detail = QLabel("Informations et utilisation des cartes graphiques détectées :")
        self.lbl_gpu_detail.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(self.lbl_gpu_detail)

        self.gpu_info_list = QListWidget()
        layout.addWidget(self.gpu_info_list)

    def init_storage_tab(self):
        layout = QVBoxLayout(self.tab_storage)
        layout.setContentsMargins(15, 15, 15, 15)
        
        self.lbl_storage_detail = QLabel("Statut de santé (S.M.A.R.T.) et utilisation de vos disques :")
        self.lbl_storage_detail.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(self.lbl_storage_detail)

        self.storage_info_list = QListWidget()
        layout.addWidget(self.storage_info_list)

    def init_processes_tab(self):
        layout = QVBoxLayout(self.tab_processes)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Intégrer notre widget de processus personnalisé
        self.process_widget = ProcessTableWidget()
        layout.addWidget(self.process_widget)

    def init_alerts_tab(self):
        layout = QVBoxLayout(self.tab_alerts)
        layout.setContentsMargins(15, 15, 15, 15)

        self.lbl_alerts_info = QLabel("Alertes actives et dépassements de seuils récents :")
        self.lbl_alerts_info.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(self.lbl_alerts_info)

        self.alerts_list = QListWidget()
        layout.addWidget(self.alerts_list)

        self.clear_alerts_btn = QPushButton("Effacer l'historique des alertes")
        self.clear_alerts_btn.clicked.connect(self.clear_alerts)
        layout.addWidget(self.clear_alerts_btn)

    def init_settings_tab(self):
        layout = QVBoxLayout(self.tab_settings)
        layout.setContentsMargins(15, 15, 15, 15)

        form_group = QGroupBox("Configuration des seuils thermiques")
        form_layout = QFormLayout(form_group)
        form_layout.setSpacing(15)

        # Seuils CPU Temp
        self.slide_cpu_warn = QSlider(Qt.Orientation.Horizontal)
        self.slide_cpu_warn.setRange(40, 95)
        self.slide_cpu_warn.setValue(int(float(get_setting("cpu_temp_warn", "75.0"))))
        self.lbl_cpu_warn_val = QLabel(f"{self.slide_cpu_warn.value()} °C")
        self.slide_cpu_warn.valueChanged.connect(lambda v: self.lbl_cpu_warn_val.setText(f"{v} °C"))
        
        form_layout.addRow("CPU Avertissement :", self.slide_cpu_warn)
        form_layout.addRow("", self.lbl_cpu_warn_val)

        # Seuils GPU Temp
        self.slide_gpu_warn = QSlider(Qt.Orientation.Horizontal)
        self.slide_gpu_warn.setRange(40, 95)
        self.slide_gpu_warn.setValue(int(float(get_setting("gpu_temp_warn", "80.0"))))
        self.lbl_gpu_warn_val = QLabel(f"{self.slide_gpu_warn.value()} °C")
        self.slide_gpu_warn.valueChanged.connect(lambda v: self.lbl_gpu_warn_val.setText(f"{v} °C"))
        
        form_layout.addRow("GPU Avertissement :", self.slide_gpu_warn)
        form_layout.addRow("", self.lbl_gpu_warn_val)

        # Toggle Notifications
        self.chk_notif = QCheckBox("Activer les notifications système (Toasts)")
        self.chk_notif.setChecked(get_setting("enable_notifications", "true") == "true")
        form_layout.addRow("Notifications :", self.chk_notif)

        # Intervalle de rafraîchissement
        self.combo_interval = QComboBox()
        self.combo_interval.addItems(["0.5 seconde", "1.0 seconde", "2.0 secondes", "5.0 secondes"])
        current_interval = get_setting("refresh_interval", "1.0")
        interval_index = {"0.5": 0, "1.0": 1, "2.0": 2, "5.0": 3}.get(current_interval, 1)
        self.combo_interval.setCurrentIndex(interval_index)
        form_layout.addRow("Intervalle de rafraîchissement :", self.combo_interval)

        layout.addWidget(form_group)

        # Bouton Enregistrer
        save_btn = QPushButton("Enregistrer les Paramètres")
        save_btn.setStyleSheet("height: 40px; font-weight: bold; background: linear-gradient(135deg, #00f0ff, #8a2be2);")
        save_btn.clicked.connect(self.save_settings)
        layout.addWidget(save_btn)
        
        layout.addStretch()

    @pyqtSlot(object, list)
    def on_data_received(self, data: SystemData, alerts: list):
        """
        Reçoit périodiquement les relevés physiques et met à jour l'IHM.
        """
        # --- 1. Onglet Vue d'ensemble ---
        # Jauges
        self.gauge_temp.set_value(data.cpu.temperature_total)
        self.gauge_load.set_value(data.cpu.usage_total)
        self.gauge_ram.set_value(data.ram.usage_percent)
        
        # Maxima
        if data.cpu.temperature_total > self.max_cpu_temp:
            self.max_cpu_temp = data.cpu.temperature_total
            self.gauge_temp.set_sub_text(f"Max historique : {self.max_cpu_temp:.1f} °C")
            
        self.gauge_load.set_sub_text(f"{data.cpu.cores_logical} cœurs logiques")
        self.gauge_ram.set_sub_text(f"{data.ram.used/1024:.1f} / {data.ram.total/1024:.1f} GB")

        # Informations statiques
        self.lbl_os.setText(f"{platform.system()} {platform.release()}")
        self.lbl_cpu_name.setText(data.cpu.name)
        self.lbl_host.setText(platform.node())
        
        # Uptime
        hours, remainder = divmod(int(data.uptime), 3600)
        minutes, seconds = divmod(remainder, 60)
        self.lbl_uptime.setText(f"{hours}h {minutes}m {seconds}s")

        # Graphique
        gpu_temp = data.gpus[0].temperature if data.gpus else 0.0
        self.chart.update_history(data.cpu.temperature_total, gpu_temp)

        # Réseau
        self.lbl_net_down.setText(self.format_speed(data.network["rx_sec"]))
        self.lbl_net_up.setText(self.format_speed(data.network["tx_sec"]))

        # Disques (mini-liste)
        disks_str = ", ".join([f"{d.path} ({d.usage_percent:.0f}%)" for d in data.disks])
        self.lbl_disks_list.setText(disks_str or "Aucun")

        # Capteurs additionnels
        sensors_text = ""
        for i, gpu in enumerate(data.gpus):
            sensors_text += f"🎮 GPU {i} ({gpu.name}) : {gpu.temperature:.1f} °C\n"
        if data.battery["hasBattery"]:
            sensors_text += f"🔋 Batterie : {data.battery['percent']}% {'(Charge)' if data.battery['isCharging'] else '(Décharge)'}\n"
        
        self.lbl_extra_sensors.setText(sensors_text or "Aucun capteur additionnel détecté.")

        # --- 2. Onglet CPU ---
        self.cpu_cores_list.clear()
        for i, load in enumerate(data.cpu.usage_per_core):
            temp_str = f" | Temp: {data.cpu.temperature_per_core[i]:.1f}°C" if i < len(data.cpu.temperature_per_core) else ""
            self.cpu_cores_list.addItem(f"Cœur {i} : Utilisation {load:.1f}%{temp_str}")

        # --- 3. Onglet GPU ---
        self.gpu_info_list.clear()
        for i, gpu in enumerate(data.gpus):
            self.gpu_info_list.addItem(
                f"Modèle : {gpu.name}\n"
                f"Constructeur : {gpu.vendor}\n"
                f"Utilisation GPU : {gpu.usage:.1f} %\n"
                f"Température : {gpu.temperature:.1f} °C\n"
                f"VRAM : {gpu.vram_used:.1f} MB / {gpu.vram_total:.1f} MB ({gpu.vram_percent:.1f} %)\n"
                f"Ventilateur : {gpu.fan_speed if gpu.fan_speed is not None else 'N/A'} RPM\n"
                f"Puissance : {gpu.power_draw if gpu.power_draw is not None else 'N/A'} W"
            )

        # --- 4. Onglet Stockage ---
        self.storage_info_list.clear()
        for d in data.disks:
            self.storage_info_list.addItem(
                f"Partition : {d.path} ({d.name})\n"
                f"Espace total : {d.total:.1f} GB | Utilisé : {d.used:.1f} GB ({d.usage_percent:.1f} %)\n"
                f"Débit Lecture : {d.read_speed:.2f} MB/s | Écriture : {d.write_speed:.2f} MB/s\n"
                f"Température disque : {f'{d.temperature:.1f} °C' if d.temperature is not None else 'N/A'}\n"
                f"Statut de santé S.M.A.R.T. : {d.smart_status}"
            )

        # --- 5. Onglet Alertes ---
        if alerts:
            for alert in alerts:
                self.alerts_list.addItem(f"[{alert.timestamp.strftime('%H:%M:%S')}] {alert.severity} - {alert.message}")

    def format_speed(self, bytes_per_sec: float) -> str:
        kbs = bytes_per_sec / 1024.0
        if kbs < 1024.0:
            return f"{kbs:.1f} KB/s"
        return f"{(kbs / 1024.0):.1f} MB/s"

    def clear_alerts(self):
        self.alerts_list.clear()
        QMessageBox.information(self, "Alertes", "Historique d'affichage des alertes effacé.")

    def save_settings(self):
        set_setting("cpu_temp_warn", str(float(self.slide_cpu_warn.value())))
        set_setting("gpu_temp_warn", str(float(self.slide_gpu_warn.value())))
        set_setting("enable_notifications", "true" if self.chk_notif.isChecked() else "false")
        
        # Mettre à jour l'intervalle dans le scheduler
        intervals = [0.5, 1.0, 2.0, 5.0]
        selected_interval = intervals[self.combo_interval.currentIndex()]
        set_setting("refresh_interval", str(selected_interval))
        self.scheduler.interval = selected_interval
        
        QMessageBox.information(self, "Paramètres", "Paramètres enregistrés avec succès !")

    def apply_premium_stylesheet(self):
        """
        QSS Stylesheet pour habiller toute l'application Qt avec un design de type sombre glassmorphic.
        """
        self.setStyleSheet("""
            QMainWindow {
                background: qradialgradient(cx:0.5, cy:0, radius:1, fx:0.5, fy:0, stop:0 #14142b, stop:1 #080811);
            }
            
            QTabWidget::pane {
                border: 1px solid rgba(255, 255, 255, 0.08);
                background-color: rgba(20, 20, 35, 0.45);
                border-radius: 12px;
                top: -1px;
            }
            
            QTabBar::tab {
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-bottom: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                padding: 10px 18px;
                color: #8a8ab0;
                font-family: 'Outfit';
                font-size: 13px;
                font-weight: bold;
                margin-right: 4px;
            }
            
            QTabBar::tab:selected {
                background: rgba(20, 20, 35, 0.6);
                border-color: rgba(255, 255, 255, 0.12);
                color: #00f0ff;
            }
            
            QTabBar::tab:hover {
                background: rgba(255, 255, 255, 0.08);
                color: #f5f5fa;
            }
            
            QWidget#OverviewGaugesCard, QWidget#ChartCard {
                background-color: rgba(255, 255, 255, 0.02);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 14px;
            }
            
            QGroupBox {
                font-family: 'Outfit';
                font-size: 14px;
                font-weight: bold;
                color: #f5f5fa;
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 14px;
                margin-top: 15px;
                padding-top: 15px;
                background-color: rgba(255, 255, 255, 0.01);
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 10px;
                left: 10px;
            }
            
            QLabel {
                font-family: 'Outfit';
                color: #f5f5fa;
                font-size: 13px;
            }
            
            QLabel[text$=":"] {
                color: #8a8ab0;
                font-weight: bold;
            }
            
            QListWidget {
                background-color: rgba(15, 15, 30, 0.3);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 10px;
                color: #f5f5fa;
                font-family: 'Outfit';
                font-size: 13px;
                padding: 10px;
            }
            
            QListWidget::item {
                border-bottom: 1px solid rgba(255, 255, 255, 0.02);
                padding: 8px;
            }
            
            QListWidget::item:hover {
                background-color: rgba(255, 255, 255, 0.03);
                border-radius: 6px;
            }
            
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #00f0ff, stop:1 #8a2be2);
                border: none;
                border-radius: 8px;
                color: #ffffff;
                font-family: 'Outfit';
                font-size: 13px;
                font-weight: bold;
                padding: 8px 16px;
            }
            
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #33f3ff, stop:1 #a14bf6);
            }
            
            QPushButton:pressed {
                background: #8a2be2;
            }
            
            QTableWidget {
                background-color: rgba(15, 15, 30, 0.2);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 10px;
                color: #f5f5fa;
                font-family: 'Outfit';
                gridline-color: rgba(255, 255, 255, 0.03);
            }
            
            QHeaderView::section {
                background-color: rgba(20, 20, 35, 0.7);
                color: #8a8ab0;
                padding: 8px;
                border: none;
                border-bottom: 1px solid rgba(255, 255, 255, 0.08);
                font-family: 'Outfit';
                font-weight: bold;
            }
            
            QLineEdit {
                background-color: rgba(15, 15, 30, 0.4);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                color: #f5f5fa;
                padding: 8px 12px;
                font-family: 'Outfit';
            }
            
            QLineEdit:focus {
                border-color: #00f0ff;
            }
            
            QComboBox {
                background-color: rgba(15, 15, 30, 0.4);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                color: #f5f5fa;
                padding: 6px 12px;
                font-family: 'Outfit';
            }
        """)
