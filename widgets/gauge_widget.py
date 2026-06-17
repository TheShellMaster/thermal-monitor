# -*- coding: utf-8 -*-
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QBrush
from PyQt6.QtCore import Qt, QRectF

class CircularGaugeWidget(QWidget):
    def __init__(self, label: str = "CPU", unit: str = "%", parent=None):
        super().__init__(parent)
        self.label = label
        self.unit = unit
        self.value = 0.0
        self.max_value = 100.0
        self.sub_text = ""
        self.setMinimumSize(150, 160)

    def set_value(self, val: float):
        # Limiter la valeur entre 0 et max_value
        self.value = max(0.0, min(float(val), self.max_value))
        self.update()  # Force le rafraîchissement graphique

    def set_sub_text(self, text: str):
        self.sub_text = text
        self.update()

    def _get_color(self, val_percent: float) -> QColor:
        # Code couleur dynamique : vert -> jaune -> rouge
        if val_percent < 60:
            return QColor("#00ff88")  # Vert Néon
        elif val_percent < 80:
            return QColor("#ffaa00")  # Orange
        else:
            return QColor("#ff3366")  # Rouge Alerte

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()
        size = min(width, height - 30)
        
        # Coordonnées du cercle de la jauge
        rect = QRectF((width - size) / 2.0, 10, size, size)
        
        # 1. Dessiner le cercle d'arrière-plan (piste grise)
        bg_pen = QPen(QColor(255, 255, 255, 12), 10)
        bg_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(bg_pen)
        # 240 degrés d'angle, centré en bas
        painter.drawArc(rect, -30 * 16, 240 * 16)

        # 2. Dessiner l'arc de progression (couleur dynamique)
        percent = (self.value / self.max_value) * 100
        val_color = self._get_color(percent)
        
        fg_pen = QPen(val_color, 10)
        fg_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(fg_pen)
        
        # L'arc est dessiné proportionnellement à la valeur
        angle = int((self.value / self.max_value) * 240)
        painter.drawArc(rect, (210 - angle) * 16, angle * 16)

        # 3. Dessiner le texte de la valeur numérique au centre
        painter.setPen(QColor("#f5f5fa"))
        val_font = QFont("Outfit", 20, QFont.Weight.Bold)
        painter.setFont(val_font)
        
        val_str = f"{int(self.value)}" if self.unit != "°C" else f"{self.value:.0f}"
        val_rect = QRectF(rect.x(), rect.y() + size/2.0 - 25, size, 30)
        painter.drawText(val_rect, Qt.AlignmentFlag.AlignCenter, val_str)

        # Dessiner l'unité juste à côté ou en dessous
        painter.setPen(QColor("#8a8ab0"))
        unit_font = QFont("Outfit", 10, QFont.Weight.Normal)
        painter.setFont(unit_font)
        unit_rect = QRectF(rect.x(), rect.y() + size/2.0 + 5, size, 20)
        painter.drawText(unit_rect, Qt.AlignmentFlag.AlignCenter, self.unit)

        # 4. Dessiner le label du composant en dessous du cercle
        painter.setPen(QColor("#f5f5fa"))
        lbl_font = QFont("Outfit", 10, QFont.Weight.DemiBold)
        painter.setFont(lbl_font)
        lbl_rect = QRectF(0, rect.bottom() + 5, width, 20)
        painter.drawText(lbl_rect, Qt.AlignmentFlag.AlignCenter, self.label)

        # 5. Dessiner le sous-texte (ex: Max ou Détails)
        if self.sub_text:
            painter.setPen(QColor("#8a8ab0"))
            sub_font = QFont("Outfit", 8, QFont.Weight.Light)
            painter.setFont(sub_font)
            sub_rect = QRectF(0, rect.bottom() + 20, width, 15)
            painter.drawText(sub_rect, Qt.AlignmentFlag.AlignCenter, self.sub_text)

        painter.end()
