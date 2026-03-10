from __future__ import annotations

import sys
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QFrame, QGraphicsDropShadowEffect, QWidget


APP_STYLE = """
QMainWindow {
    background: #F6F7FB;
}

QLabel#title {
    font-size: 22px;
    font-weight: 600;
    color: #0F172A;
}

QLabel#subtitle {
    font-size: 12px;
    color: #6B7280;
}

QLabel#badge {
    font-size: 12px;
    font-weight: 600;
    padding: 4px 12px;
    border-radius: 999px;
}

QLabel#badgeLarge {
    font-size: 17px;
    font-weight: 600;
    padding: 10px 18px;
    border-radius: 999px;
}

QLabel#fieldLabel {
    font-size: 11px;
    color: #6B7280;
}

QLabel#cardTitle {
    font-size: 11px;
    color: #6B7280;
}

QLineEdit {
    background: #F1F3F7;
    border: 1px solid #E5E7EF;
    border-radius: 12px;
    padding: 10px 12px;
    font-size: 14px;
    color: #0F172A;
}

QLineEdit:focus {
    border: 1px solid #94A3B8;
    background: #EEF1F6;
}

QComboBox {
    background: #F1F3F7;
    border: 1px solid #E5E7EF;
    border-radius: 12px;
    padding: 10px 12px;
    font-size: 14px;
    color: #0F172A;
}

QComboBox:focus {
    border: 1px solid #94A3B8;
    background: #EEF1F6;
}

QComboBox::drop-down {
    border: none;
    width: 28px;
}

QComboBox QAbstractItemView {
    background: #FFFFFF;
    border: 1px solid #E5E7EF;
    selection-background-color: #E2E8F0;
    selection-color: #0F172A;
}

QCheckBox {
    font-size: 13px;
    color: #111827;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 36px;
    height: 20px;
    border-radius: 10px;
    background: #E5E7EB;
    border: 1px solid #CBD5E1;
}

QCheckBox::indicator:checked {
    background: #34D399;
    border: 1px solid #10B981;
}

QFrame#card {
    background: #FFFFFF;
    border-radius: 20px;
    border: 1px solid #EEF2F7;
}

QLabel#chipLabel {
    font-size: 10px;
    color: #6B7280;
    letter-spacing: 0.6px;
    text-transform: uppercase;
}

QLabel#chipValue {
    font-size: 18px;
    font-weight: 600;
    color: #0F172A;
}

QLabel#hint {
    font-size: 11px;
    color: #6B7280;
}

QLabel#error {
    font-size: 11px;
    color: #DC2626;
}

QFrame#chip {
    background: #F1F3F7;
    border-radius: 16px;
    border: 1px solid #EEF2F7;
}

QFrame#chip[state="neutral"] {
    background: #F1F3F7;
    border: 1px solid #EEF2F7;
}

QFrame#chip[state="pass"] {
    background: #BBF7D0;
    border: 1px solid #22C55E;
}

QFrame#chip[state="warn"] {
    background: #FFFBEB;
    border: 1px solid #FEF3C7;
}

QFrame#chip[state="fail"] {
    background: #FECACA;
    border: 1px solid #EF4444;
}

QFrame#chip[state="pass"] QLabel#chipValue {
    color: #16A34A;
}

QFrame#chip[state="warn"] QLabel#chipValue {
    color: #CA8A04;
}

QFrame#chip[state="fail"] QLabel#chipValue {
    color: #DC2626;
}

QFrame#segmented {
    background: #E9EDF5;
    border-radius: 999px;
    border: 1px solid #EEF2F7;
}

QLabel#ruleThreshold {
    font-size: 10px;
    color: #94A3B8;
}

QLabel#ruleValue {
    font-size: 12px;
    color: #0F172A;
}

QPushButton {
    border-radius: 10px;
    padding: 6px 12px;
    border: 1px solid #E2E8F0;
    background: #FFFFFF;
    color: #0F172A;
}

QPushButton#primary {
    background: #111827;
    color: #FFFFFF;
    border: none;
}

QToolButton {
    border: none;
    color: #64748B;
    font-size: 12px;
}

QToolButton#toggle {
    background: #F1F5F9;
    border-radius: 10px;
    padding: 2px 6px;
}
"""


def apply_app_style(app) -> None:
    app.setStyleSheet(APP_STYLE)
    app.setFont(_system_font())


def create_card(widget: QWidget) -> QFrame:
    frame = QFrame(widget)
    frame.setObjectName("card")
    add_shadow(frame)
    return frame


def add_shadow(widget: QWidget, blur: int = 24, y_offset: int = 8, alpha: int = 28) -> None:
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(blur)
    shadow.setOffset(0, y_offset)
    shadow.setColor(QColor(15, 23, 42, alpha))
    widget.setGraphicsEffect(shadow)


def _system_font() -> QFont:
    if sys.platform == "darwin":
        return QFont("SF Pro Text", 10)
    if sys.platform.startswith("win"):
        return QFont("Segoe UI", 10)
    return QFont("Helvetica", 10)
