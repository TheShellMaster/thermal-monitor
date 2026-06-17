# -*- coding: utf-8 -*-
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QLineEdit, QPushButton, QHeaderView, 
                             QMessageBox, QMenu)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QColor

from process_manager import get_active_processes, kill_process_by_pid, change_process_priority

class ProcessTableWidget(QWidget):
    # Signal émis après l'arrêt d'un processus pour demander un rafraîchissement global
    process_killed_signal = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.sort_by = "cpu"
        self.search_query = ""
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 1. Barre de recherche et bouton d'action
        top_layout = QHBoxLayout()
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Rechercher un processus (Nom, PID, utilisateur)...")
        self.search_bar.textChanged.connect(self.on_search_changed)
        top_layout.addWidget(self.search_bar)

        self.refresh_btn = QPushButton("Rafraîchir les Processus")
        self.refresh_btn.clicked.connect(self.refresh_list)
        top_layout.addWidget(self.refresh_btn)

        layout.addLayout(top_layout)

        # 2. Tableau des processus
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["PID", "Nom (Utilisateur)", "CPU %", "Mémoire", "Statut", "Actions"])
        
        # Styles d'en-tête
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)

        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        
        # Activer le tri en cliquant sur les en-têtes
        header.sectionClicked.connect(self.on_header_clicked)

        layout.addWidget(self.table)
        self.refresh_list()

    def on_search_changed(self, text):
        self.search_query = text
        self.refresh_list()

    def on_header_clicked(self, logical_index):
        # Assigner le critère de tri en fonction de la colonne cliquée
        columns = {0: "pid", 1: "name", 2: "cpu", 3: "mem"}
        if logical_index in columns:
            self.sort_by = columns[logical_index]
            self.refresh_list()

    def refresh_list(self):
        try:
            self.refresh_btn.setEnabled(False)
            self.refresh_btn.setText("Chargement...")
            
            # Récupérer les processus triés et filtrés
            processes = get_active_processes(sort_by=self.sort_by, search_query=self.search_query, limit=20)
            
            self.table.setRowCount(0)
            for i, p in enumerate(processes):
                self.table.insertRow(i)
                
                # PID
                pid_item = QTableWidgetItem(str(p.pid))
                pid_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                pid_item.setData(Qt.ItemDataRole.UserRole, p.pid)  # Sauvegarde du PID numérique
                self.table.setItem(i, 0, pid_item)
                
                # Nom (User)
                name_item = QTableWidgetItem(f"{p.name} ({p.user})")
                self.table.setItem(i, 1, name_item)
                
                # CPU %
                cpu_item = QTableWidgetItem(f"{p.cpu_percent:.1f} %")
                cpu_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                # Appliquer une couleur d'avertissement si CPU élevé
                if p.cpu_percent > 50.0:
                    cpu_item.setForeground(QColor("#ff3366"))
                self.table.setItem(i, 2, cpu_item)
                
                # RAM (MB)
                mem_item = QTableWidgetItem(f"{p.memory_mb:.1f} MB")
                mem_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if p.memory_mb > 500.0:
                    mem_item.setForeground(QColor("#ffaa00"))
                self.table.setItem(i, 3, mem_item)
                
                # Statut
                status_item = QTableWidgetItem(p.status)
                status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(i, 4, status_item)
                
                # Action Button (Tuer)
                kill_btn = QPushButton("Tuer")
                kill_btn.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(255, 51, 102, 0.15);
                        color: #ff3366;
                        border: 1px solid rgba(255, 51, 102, 0.3);
                        border-radius: 4px;
                        padding: 2px 8px;
                    }
                    QPushButton:hover {
                        background-color: #ff3366;
                        color: #ffffff;
                    }
                """)
                # Lier le bouton d'arrêt pour ce PID spécifique
                kill_btn.clicked.connect(lambda checked, pid=p.pid, name=p.name: self.confirm_kill(pid, name))
                self.table.setCellWidget(i, 5, kill_btn)
                
        finally:
            self.refresh_btn.setEnabled(True)
            self.refresh_btn.setText("Rafraîchir les Processus")

    def confirm_kill(self, pid: int, name: str):
        reply = QMessageBox.question(
            self, 
            "Confirmer l'arrêt", 
            f"Voulez-vous vraiment tuer le processus '{name}' (PID: {pid}) ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            success, msg = kill_process_by_pid(pid, force=False)
            if success:
                QMessageBox.information(self, "Succès", msg)
                self.process_killed_signal.emit(pid)
                self.refresh_list()
            else:
                # Si échec (ex: droits), proposer de forcer
                reply_force = QMessageBox.question(
                    self, 
                    "Erreur - Forcer ?", 
                    f"{msg}\nVoulez-vous tenter de FORCER l'arrêt (SIGKILL) ?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply_force == QMessageBox.StandardButton.Yes:
                    success, msg_force = kill_process_by_pid(pid, force=True)
                    if success:
                        QMessageBox.information(self, "Succès", msg_force)
                        self.process_killed_signal.emit(pid)
                        self.refresh_list()
                    else:
                        QMessageBox.critical(self, "Échec", msg_force)

    def show_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if not item:
            return
            
        row = item.row()
        pid_item = self.table.item(row, 0)
        pid = pid_item.data(Qt.ItemDataRole.UserRole)
        name_item = self.table.item(row, 1)
        name = name_item.text().split(" (")[0]

        menu = QMenu(self)
        
        kill_action = QAction(f"🛑 Arrêter '{name}'", self)
        kill_action.triggered.connect(lambda: self.confirm_kill(pid, name))
        menu.addAction(kill_action)
        
        menu.addSeparator()
        
        # Sous-menu priorités
        prio_menu = menu.addMenu("⚡ Changer Priorité")
        
        prio_high = QAction("Haute", self)
        prio_high.triggered.connect(lambda: self.change_prio(pid, -10))
        prio_menu.addAction(prio_high)
        
        prio_normal = QAction("Normale", self)
        prio_normal.triggered.connect(lambda: self.change_prio(pid, 0))
        prio_menu.addAction(prio_normal)
        
        prio_low = QAction("Basse (Économie CPU)", self)
        prio_low.triggered.connect(lambda: self.change_prio(pid, 10))
        prio_menu.addAction(prio_low)

        menu.exec(self.table.viewport().mapToGlobal(pos))

    def change_prio(self, pid: int, nice_val: int):
        success, msg = change_process_priority(pid, nice_val)
        if success:
            QMessageBox.information(self, "Priorité", msg)
            self.refresh_list()
        else:
            QMessageBox.critical(self, "Erreur", msg)
