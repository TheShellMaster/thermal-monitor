# -*- coding: utf-8 -*-
import pyqtgraph as pg
from PyQt6.QtGui import QColor

class ThermalHistoryChart(pg.PlotWidget):
    def __init__(self, parent=None, max_points: int = 120):
        """
        Graphique historique basé sur pyqtgraph.
        max_points: nombre de points affichés sur l'axe des X (ex: 120 points = 2 minutes à 1s de refresh).
        """
        super().__init__(parent)
        self.max_points = max_points
        self.cpu_data = []
        self.gpu_data = []
        
        # Configuration esthétique du graphique
        self.setBackground('transparent')
        self.showGrid(x=True, y=True, alpha=0.15)
        
        # Titre et styles
        self.setTitle("Historique Thermique", color="#f5f5fa", size="10pt")
        self.setLabel('left', 'Température (°C)', color="#8a8ab0")
        self.setLabel('bottom', 'Temps (secondes)', color="#8a8ab0")
        
        # Configuration des axes
        self.getAxis('left').setTextPen("#8a8ab0")
        self.getAxis('bottom').setTextPen("#8a8ab0")
        
        # Définir l'échelle initiale de l'axe Y (de 20°C à 100°C)
        self.setYRange(20, 100)
        self.setXRange(0, self.max_points)

        # Tracé CPU (Rose)
        cpu_pen = pg.mkPen(color=QColor("#ff3366"), width=2.5)
        self.cpu_curve = self.plot(pen=cpu_pen, name="CPU")
        
        # Tracé GPU (Cyan)
        gpu_pen = pg.mkPen(color=QColor("#00f0ff"), width=2.5)
        self.gpu_curve = self.plot(pen=gpu_pen, name="GPU")
        
        # Ajout d'une légende
        self.legend = pg.LegendItem((80, 60), offset=(20, 20))
        self.legend.setParentItem(self.graphicsItem())
        self.legend.addItem(self.cpu_curve, "CPU Temp")
        self.legend.addItem(self.gpu_curve, "GPU Temp")
        self.legend.setLabelTextColor("#f5f5fa")

    def update_history(self, cpu_temp: float, gpu_temp: float):
        """
        Ajoute une nouvelle mesure et fait glisser le graphique.
        """
        # Ajout de la valeur CPU
        self.cpu_data.append(cpu_temp)
        if len(self.cpu_data) > self.max_points:
            self.cpu_data.pop(0)
            
        # Ajout de la valeur GPU
        self.gpu_data.append(gpu_temp)
        if len(self.gpu_data) > self.max_points:
            self.gpu_data.pop(0)

        # Mise à jour des courbes
        self.cpu_curve.setData(self.cpu_data)
        self.gpu_curve.setData(self.gpu_data)
