from __future__ import annotations

from PySide6.QtCore import QLocale, Qt
from PySide6.QtGui import (
    QDoubleValidator,
    QGuiApplication,
    QIntValidator,
    QKeySequence,
    QShortcut,
)
from PySide6.QtWidgets import (
    QApplication,
    QBoxLayout,
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from desktop_app.styles import apply_app_style, create_card
from shared.calculator import (
    DEFAULT_PROCEDURE,
    FLAP_THICKNESS_UM,
    PROCEDURE_CHOICES,
    WARN_PAQUI_HIGH,
    WARN_PAQUI_LOW,
    EyeInput,
    compute_result,
    procedure_has_flap,
)
from shared.teneo import DEFAULT_OPTICAL_ZONE_MM, OPTICAL_ZONES_MM, LaserAblation


def _format_number(value: float) -> str:
    return f"{value:g}".replace(".", ",")


def _format_d(value: float) -> str:
    return f"{value:+g}".replace(".", ",").replace("-", "−")


class MetricChip(QFrame):
    def __init__(self, label: str) -> None:
        super().__init__()
        self.setObjectName("chip")
        self.setProperty("state", "neutral")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        self.label = QLabel(label)
        self.label.setObjectName("chipLabel")
        self.value = QLabel("–")
        self.value.setObjectName("chipValue")

        layout.addWidget(self.label)
        layout.addWidget(self.value)

    def set_value(self, value: str) -> None:
        self.value.setText(value)

    def set_state(self, state: str) -> None:
        self.setProperty("state", state)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()


class RuleRow(QWidget):
    def __init__(self, text: str) -> None:
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(10)

        self.icon = QLabel("✓")
        self.icon.setFixedSize(20, 20)
        self.icon.setAlignment(Qt.AlignCenter)
        self._set_icon_style("pass")

        text_block = QVBoxLayout()
        text_block.setSpacing(1)
        self.text = QLabel(text)
        self.text.setStyleSheet("font-size: 12px; color: #111827;")
        self.threshold = QLabel("")
        self.threshold.setObjectName("ruleThreshold")
        text_block.addWidget(self.text)
        text_block.addWidget(self.threshold)

        self.value = QLabel("–")
        self.value.setObjectName("ruleValue")
        self.value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        layout.addWidget(self.icon)
        layout.addLayout(text_block)
        layout.addStretch()
        layout.addWidget(self.value)

    def update_row(self, status: str, value: str, threshold: str) -> None:
        icon = (
            "✓"
            if status == "pass"
            else "!"
            if status == "warn"
            else "✕"
            if status == "fail"
            else "–"
        )
        self.icon.setText(icon)
        self._set_icon_style(status)
        self.value.setText(value)
        self.threshold.setText(threshold)

    def _set_icon_style(self, status: str) -> None:
        if status == "pass":
            self.icon.setStyleSheet(
                "background: rgba(34,197,94,0.16); color: #16A34A; border-radius: 10px;"
            )
        elif status == "warn":
            self.icon.setStyleSheet(
                "background: rgba(251,191,36,0.2); color: #CA8A04; border-radius: 10px;"
            )
        elif status == "fail":
            self.icon.setStyleSheet(
                "background: rgba(239,68,68,0.16); color: #DC2626; border-radius: 10px;"
            )
        else:
            self.icon.setStyleSheet(
                "background: rgba(148,163,184,0.16); color: #64748B; border-radius: 10px;"
            )


class SegmentedBar(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("segmented")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.seg_flap = QFrame()
        self.seg_ablation = QFrame()
        self.seg_residual = QFrame()

        self.seg_flap.setStyleSheet("background: #CBD5E1;")
        self.seg_ablation.setStyleSheet("background: #FBBF24;")
        self.seg_residual.setStyleSheet("background: #34D399;")

        for seg in (self.seg_flap, self.seg_ablation, self.seg_residual):
            seg.setMinimumHeight(6)

        layout.addWidget(self.seg_flap)
        layout.addWidget(self.seg_ablation)
        layout.addWidget(self.seg_residual)

    def update_segments(self, flap: int, ablation: int, residual: int) -> None:
        total = flap + ablation + residual
        layout = self.layout()
        if total == 0:
            layout.setStretch(0, 1)
            layout.setStretch(1, 1)
            layout.setStretch(2, 1)
            return
        layout.setStretch(0, max(0, flap))
        layout.setStretch(1, max(0, ablation))
        layout.setStretch(2, max(0, residual))


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Ablación corneal")

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(28, 24, 28, 28)
        container_layout.setSpacing(18)
        self.setCentralWidget(container)

        header = QVBoxLayout()
        header.setSpacing(6)

        title = QLabel("Ablación corneal")
        title.setObjectName("title")
        subtitle = QLabel("Calculadora de seguridad (apoyo clínico)")
        subtitle.setObjectName("subtitle")

        self.status_badge = QLabel("")
        self.status_badge.setObjectName("badgeLarge")
        self.status_badge.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.status_badge.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.set_status_badge("invalid")

        header.addWidget(title)
        header.addWidget(subtitle)
        header.addWidget(self.status_badge)
        container_layout.addLayout(header)

        self.settings_card = self._build_settings_card()
        container_layout.addWidget(self.settings_card)

        self.input_card = self._build_input_card()
        container_layout.addWidget(self.input_card)

        self.metrics_card = self._build_metrics_card()
        container_layout.addWidget(self.metrics_card)

        self.decision_card = self._build_decision_card()
        container_layout.addWidget(self.decision_card)

        self._sync_configuration_ui()
        self.update_results()
        self._setup_shortcuts()

    def _build_settings_card(self) -> QFrame:
        card = create_card(self)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        title = QLabel("Configuración")
        title.setObjectName("cardTitle")
        layout.addWidget(title)

        self.settings_row_layout = QBoxLayout(QBoxLayout.LeftToRight)
        self.settings_row_layout.setSpacing(14)

        technique_block, self.technique_combo, _ = self._combo_block(
            "Técnica",
            list(PROCEDURE_CHOICES),
        )
        self.settings_row_layout.addWidget(technique_block)

        mode_block, self.mode_combo, _ = self._combo_block(
            "Entrada",
            [("refraction", "Por graduación"), ("direct", "Ablación directa")],
        )
        self.settings_row_layout.addWidget(mode_block)
        self.technique_combo.setCurrentIndex(
            max(0, self.technique_combo.findData(DEFAULT_PROCEDURE))
        )
        layout.addLayout(self.settings_row_layout)

        self.settings_hint_label = QLabel("")
        self.settings_hint_label.setObjectName("hint")
        layout.addWidget(self.settings_hint_label)

        self.technique_combo.currentIndexChanged.connect(self._on_configuration_changed)
        self.mode_combo.currentIndexChanged.connect(self._on_configuration_changed)

        return card

    def _build_input_card(self) -> QFrame:
        card = create_card(self)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        title = QLabel("Entrada")
        title.setObjectName("cardTitle")
        layout.addWidget(title)

        self.input_row_layout = QBoxLayout(QBoxLayout.LeftToRight)
        self.input_row_layout.setSpacing(14)

        paqui_block, self.paqui_edit, _ = self._field_block("Paquimetría preop (µm)", "500")
        self.paqui_edit.setValidator(QIntValidator(0, 2000, self))
        self.input_row_layout.addWidget(paqui_block)

        self.zone_block, self.zone_combo, _ = self._combo_block(
            "Zona óptica (mm)",
            [(zone, _format_number(zone)) for zone in OPTICAL_ZONES_MM],
        )
        self.zone_combo.setCurrentIndex(
            max(0, self.zone_combo.findData(DEFAULT_OPTICAL_ZONE_MM))
        )
        self.input_row_layout.addWidget(self.zone_block)

        self.sphere_block, self.sphere_edit, _ = self._field_block("Esfera (D)", "-3.00")
        self.sphere_edit.setValidator(self._diopter_validator(-10.0, 10.0))
        self.input_row_layout.addWidget(self.sphere_block)

        self.cylinder_block, self.cylinder_edit, _ = self._field_block(
            "Cilindro (D) · opcional", "0.00"
        )
        self.cylinder_edit.setValidator(self._diopter_validator(-15.0, 15.0))
        self.input_row_layout.addWidget(self.cylinder_block)

        self.ablation_block, self.ablation_edit, _ = self._field_block(
            "Ablación planificada (µm)",
            "90",
        )
        self.ablation_edit.setValidator(QIntValidator(0, 2000, self))
        self.input_row_layout.addWidget(self.ablation_block)

        layout.addLayout(self.input_row_layout)

        self.suspicious_toggle = QCheckBox("Córnea sospechosa")
        layout.addWidget(self.suspicious_toggle)

        self.laser_label = QLabel("")
        self.laser_label.setObjectName("hint")
        self.laser_label.setWordWrap(True)
        layout.addWidget(self.laser_label)

        self.hint_label = QLabel("")
        self.hint_label.setObjectName("hint")
        layout.addWidget(self.hint_label)

        self.error_label = QLabel("")
        self.error_label.setObjectName("error")
        layout.addWidget(self.error_label)

        self.sphere_edit.textChanged.connect(self.update_results)
        self.cylinder_edit.textChanged.connect(self.update_results)
        self.zone_combo.currentIndexChanged.connect(self.update_results)
        self.paqui_edit.textChanged.connect(self.update_results)
        self.ablation_edit.textChanged.connect(self.update_results)
        self.suspicious_toggle.stateChanged.connect(self.update_results)

        return card

    def _build_metrics_card(self) -> QFrame:
        card = create_card(self)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        title = QLabel("Resultados clave")
        title.setObjectName("cardTitle")
        layout.addWidget(title)

        self.chips_layout = QGridLayout()
        self.chips_layout.setHorizontalSpacing(12)
        self.chips_layout.setVerticalSpacing(12)

        self.chip_ablation_pct = MetricChip("Ablación %")
        self.chip_ler_um = MetricChip("LER (µm)")
        self.chip_ler_pct = MetricChip("LER %")
        self.chip_postop = MetricChip("Post-op (µm)")

        self.chips = [
            self.chip_ablation_pct,
            self.chip_ler_um,
            self.chip_ler_pct,
            self.chip_postop,
        ]

        layout.addLayout(self.chips_layout)
        self._update_chip_grid(columns=4)
        return card

    def _build_decision_card(self) -> QFrame:
        card = create_card(self)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Decisión")
        title.setObjectName("cardTitle")
        self.decision_toggle = QToolButton()
        self.decision_toggle.setCheckable(True)
        self.decision_toggle.setChecked(True)
        self.decision_toggle.setArrowType(Qt.DownArrow)
        self.decision_toggle.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.decision_toggle.setObjectName("toggle")
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.decision_toggle)
        layout.addLayout(header)

        self.decision_body = QWidget()
        body_layout = QVBoxLayout(self.decision_body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(10)

        self.max_safe_label = QLabel("Máx ablación segura: –")
        self.max_safe_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #0F172A;")
        self.margin_label = QLabel("Margen: –")
        self.margin_label.setStyleSheet("font-size: 13px; color: #111827;")
        self.limit_label = QLabel("Limita: –")
        self.limit_label.setStyleSheet("font-size: 12px; color: #6B7280;")

        body_layout.addWidget(self.max_safe_label)
        body_layout.addWidget(self.margin_label)
        body_layout.addWidget(self.limit_label)

        self.segmented_bar = SegmentedBar()
        body_layout.addWidget(self.segmented_bar)

        self.seg_labels = QLabel("Flap 120 µm · Ablación 0 µm · Residual 0 µm")
        self.seg_labels.setObjectName("hint")
        body_layout.addWidget(self.seg_labels)

        self.ler_formula_label = QLabel("LER = paquimetría − flap (120 µm en LASIK) − ablación")
        self.ler_formula_label.setObjectName("hint")
        body_layout.addWidget(self.ler_formula_label)

        actions = QHBoxLayout()
        actions.addStretch()
        self.reset_button = QPushButton("Reset")
        self.copy_button = QPushButton("📋 Copiar resumen")
        self.copy_button.setObjectName("primary")
        actions.addWidget(self.reset_button)
        actions.addWidget(self.copy_button)
        body_layout.addLayout(actions)

        self.details_button = QToolButton()
        self.details_button.setText("Detalles")
        self.details_button.setCheckable(True)
        body_layout.addWidget(self.details_button, alignment=Qt.AlignLeft)

        self.rules_container = QWidget()
        rules_layout = QVBoxLayout(self.rules_container)
        rules_layout.setContentsMargins(0, 4, 0, 0)
        rules_layout.setSpacing(6)
        self.rule_ablation = RuleRow("Ablación ≤ 20%")
        self.rule_ler_um = RuleRow("LER ≥ 300 µm")
        self.rule_ler_pct = RuleRow("LER %")
        self.rule_postop = RuleRow("Post-op ≥ 400 µm")
        rules_layout.addWidget(self.rule_ablation)
        rules_layout.addWidget(self.rule_ler_um)
        rules_layout.addWidget(self.rule_ler_pct)
        rules_layout.addWidget(self.rule_postop)
        self.rule_paqui_prk = RuleRow("PRK: paqui preop ≥ 450-460 µm")
        self.rule_paqui_prk.setVisible(False)
        rules_layout.addWidget(self.rule_paqui_prk)
        self.rules_container.setVisible(False)
        body_layout.addWidget(self.rules_container)

        layout.addWidget(self.decision_body)

        self.reset_button.clicked.connect(self.reset_inputs)
        self.copy_button.clicked.connect(self.copy_summary)
        self.details_button.toggled.connect(self.rules_container.setVisible)
        self.decision_toggle.toggled.connect(self._toggle_decision)
        return card

    def _field_block(self, label_text: str, placeholder: str) -> tuple[QWidget, QLineEdit, QLabel]:
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        label = QLabel(label_text)
        label.setObjectName("fieldLabel")

        line = QLineEdit()
        line.setPlaceholderText(placeholder)
        line.setAlignment(Qt.AlignLeft)

        layout.addWidget(label)
        layout.addWidget(line)
        return wrapper, line, label

    def _combo_block(
        self,
        label_text: str,
        items: list[tuple[str, str]],
    ) -> tuple[QWidget, QComboBox, QLabel]:
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        label = QLabel(label_text)
        label.setObjectName("fieldLabel")

        combo = QComboBox()
        for value, text in items:
            combo.addItem(text, value)

        layout.addWidget(label)
        layout.addWidget(combo)
        return wrapper, combo, label

    @staticmethod
    def _diopter_validator(minimum: float, maximum: float) -> QDoubleValidator:
        validator = QDoubleValidator(minimum, maximum, 2)
        validator.setNotation(QDoubleValidator.StandardNotation)
        validator.setLocale(QLocale.c())
        return validator

    def _current_procedure(self) -> str:
        return str(self.technique_combo.currentData())

    def _current_mode(self) -> str:
        return str(self.mode_combo.currentData())

    def _on_configuration_changed(self, *_args) -> None:
        self._sync_configuration_ui()
        self.update_results()

    def _sync_configuration_ui(self) -> None:
        refraction = self._current_mode() == "refraction"
        for block in (self.zone_block, self.sphere_block, self.cylinder_block):
            block.setVisible(refraction)
        self.ablation_block.setVisible(not refraction)

        if procedure_has_flap(self._current_procedure()):
            self.settings_hint_label.setText(
                f"LASIK: se resta el flap de {FLAP_THICKNESS_UM} µm del lecho residual."
            )
        else:
            self.settings_hint_label.setText("PRK: no hay flap, no se resta nada. Paquimetría preop de al menos 450-460 µm y final de 400 µm.")

    @staticmethod
    def _to_float(text: str) -> float | None:
        try:
            return float(text.strip().replace(",", "."))
        except ValueError:
            return None

    def _build_eye_input(self) -> tuple[EyeInput | None, str]:
        paqui_text = self.paqui_edit.text().strip()
        if not paqui_text:
            return None, "Introduce paquimetría preop."

        base = {
            "paqui_preop_um": int(paqui_text),
            "suspicious": self.suspicious_toggle.isChecked(),
            "procedure": self._current_procedure(),
        }
        if self._current_mode() == "refraction":
            sphere = self._to_float(self.sphere_edit.text())
            if sphere is None:
                return None, "Introduce la esfera."
            return (
                EyeInput(
                    **base,
                    sphere_d=sphere,
                    cylinder_d=self._to_float(self.cylinder_edit.text()) or 0.0,
                    optical_zone_mm=float(self.zone_combo.currentData()),
                ),
                "",
            )

        ablation_text = self.ablation_edit.text().strip()
        if not ablation_text:
            return None, "Introduce la ablación."
        return EyeInput(**base, ablation_um=int(ablation_text)), ""

    @staticmethod
    def _describe_refraction(laser: LaserAblation) -> str:
        if not laser.cylinder_d:
            return f"{_format_d(laser.sphere_d)} D"
        return (
            f"{_format_d(laser.sphere_d)} / {_format_d(laser.cylinder_d)} "
            f"(esfera equivalente {_format_d(laser.equivalent_d)} D)"
        )

    def _laser_summary(self, laser: LaserAblation | None) -> str:
        if laser is None or not laser.found:
            return ""
        details = (
            "interpolado entre dos filas de la tabla"
            if laser.interpolated
            else f"zona {laser.zone_mm.replace('.', ',')} mm · {laser.time_s} s"
        )
        return (
            f"Teneo · ZO {_format_number(laser.optical_zone_mm)} mm · "
            f"{self._describe_refraction(laser)} → ablación {laser.ablation_um} µm ({details})."
        )

    @staticmethod
    def _segment_text(flap: int, ablation: int, residual: int) -> str:
        flap_text = f"Flap {flap} µm · " if flap > 0 else ""
        return f"{flap_text}Ablación {ablation} µm · Residual {residual} µm"

    def _setup_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+L"), self, activated=self.ablation_edit.setFocus)
        QShortcut(QKeySequence("Meta+L"), self, activated=self.ablation_edit.setFocus)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        width = self.width()
        if width < 720:
            self.settings_row_layout.setDirection(QBoxLayout.TopToBottom)
            self.input_row_layout.setDirection(QBoxLayout.TopToBottom)
            self._update_chip_grid(columns=2)
        else:
            self.settings_row_layout.setDirection(QBoxLayout.LeftToRight)
            self.input_row_layout.setDirection(QBoxLayout.LeftToRight)
            self._update_chip_grid(columns=4)

    def _update_chip_grid(self, columns: int) -> None:
        for index, chip in enumerate(self.chips):
            row = index // columns
            col = index % columns
            self.chips_layout.addWidget(chip, row, col)

    def update_results(self) -> None:
        eye_input, message = self._build_eye_input()
        if eye_input is None:
            self.set_status_badge("invalid")
            self.error_label.setText(message)
            self.hint_label.setText("")
            self.laser_label.setText("")
            self._set_placeholders()
            return

        paqui = eye_input.paqui_preop_um
        result = compute_result(eye_input)

        if not result.valid:
            self.set_status_badge("invalid")
            self.error_label.setText(result.errors[0] if result.errors else "Entradas inconsistentes.")
            self.hint_label.setText("")
            self.laser_label.setText("")
            self._set_placeholders()
            return

        self.laser_label.setText(self._laser_summary(result.laser))
        self.error_label.setText("")
        self.set_status_badge(result.overall_status)

        if paqui < WARN_PAQUI_LOW or paqui > WARN_PAQUI_HIGH:
            self.hint_label.setText(
                f"ℹ︎ Paquimetría fuera del rango de referencia ({WARN_PAQUI_LOW}–{WARN_PAQUI_HIGH} µm)."
            )
        else:
            self.hint_label.setText("")

        self.chip_ablation_pct.set_value(f"{result.ablation_pct:.1f}")
        self.chip_ablation_pct.set_state(result.rule_ablation_status)
        self.chip_ler_um.set_value(f"{result.ler_um}")
        self.chip_ler_um.set_state(result.rule_ler_um_status)
        self.chip_ler_pct.set_value(f"{result.ler_pct:.1f}")
        self.chip_ler_pct.set_state(result.rule_ler_pct_status)
        self.chip_postop.set_value(f"{result.postop_paqui_um}")
        self.chip_postop.set_state(result.rule_postop_status)

        self.max_safe_label.setText(f"Máx ablación segura: {result.ablation_max_safe_um} µm")
        self.margin_label.setText(f"Margen: {result.margin_um:+d} µm")
        self.limit_label.setText(f"Limita: {result.limit_factor}")

        self.segmented_bar.update_segments(result.subtract_um, result.ablation_um, result.ler_um)
        self.seg_labels.setText(
            self._segment_text(result.subtract_um, result.ablation_um, result.ler_um)
        )
        paqui = result.ler_um + result.subtract_um + result.ablation_um
        if result.subtract_um > 0:
            self.ler_formula_label.setText(
                f"LER = {paqui} (paqui) − {result.subtract_um} (flap) − "
                f"{result.ablation_um} (ablación) = {result.ler_um} µm"
            )
        else:
            self.ler_formula_label.setText(
                f"LER = {paqui} (paqui) − {result.ablation_um} (ablación) = "
                f"{result.ler_um} µm · PRK: sin flap"
            )

        self.rule_ablation.update_row(
            result.rule_ablation_status,
            f"{result.ablation_pct:.1f} %",
            f"<= {result.ablation_pct_threshold:.1f} %",
        )
        self.rule_ler_um.update_row(
            result.rule_ler_um_status,
            f"{result.ler_um} µm",
            f">= {result.ler_um_threshold} µm",
        )
        self.rule_ler_pct.update_row(
            result.rule_ler_pct_status,
            f"{result.ler_pct:.1f} %",
            f">= {result.ler_pct_threshold:.1f} %",
        )
        self.rule_postop.update_row(
            result.rule_postop_status,
            f"{result.postop_paqui_um} µm",
            f">= {result.postop_um_threshold} µm",
        )
        prk_status = result.rule_paqui_prk_status
        self.rule_paqui_prk.setVisible(prk_status is not None)
        if prk_status is not None:
            self.rule_paqui_prk.update_row(
                prk_status,
                f"{result.postop_paqui_um + result.ablation_um} µm",
                f">= {result.paqui_prk_ok_um} µm (mínimo {result.paqui_prk_min_um} µm)",
            )

    def _set_placeholders(self) -> None:
        for chip in self.chips:
            chip.set_value("–")
            chip.set_state("neutral")
        self.max_safe_label.setText("Máx ablación segura: –")
        self.margin_label.setText("Margen: –")
        self.limit_label.setText("Limita: –")
        self.segmented_bar.update_segments(0, 0, 0)
        flap = FLAP_THICKNESS_UM if procedure_has_flap(self._current_procedure()) else 0
        self.seg_labels.setText(self._segment_text(flap, 0, 0))
        self.ler_formula_label.setText("LER = paquimetría − flap (120 µm en LASIK) − ablación")
        self.rule_ablation.update_row("neutral", "–", "")
        self.rule_ler_um.update_row("neutral", "–", "")
        self.rule_ler_pct.update_row("neutral", "–", "")
        self.rule_postop.update_row("neutral", "–", "")
        self.rule_paqui_prk.setVisible(False)

    def _toggle_decision(self, checked: bool) -> None:
        self.decision_body.setVisible(checked)
        self.decision_toggle.setArrowType(Qt.DownArrow if checked else Qt.RightArrow)

    def set_status_badge(self, status: str) -> None:
        if status == "ok":
            text = "Cumple"
            style = "background: #ECFDF3; color: #16A34A;"
        elif status == "warning":
            text = "Cerca"
            style = "background: #FFFBEB; color: #CA8A04;"
        elif status == "fail":
            text = "No cumple"
            style = "background: #FEF2F2; color: #DC2626;"
        else:
            text = "No válido"
            style = "background: #F1F5F9; color: #64748B;"
        self.status_badge.setText(text)
        self.status_badge.setStyleSheet(style)

    def reset_inputs(self) -> None:
        self.paqui_edit.setText("")
        self.ablation_edit.setText("")
        self.sphere_edit.setText("")
        self.cylinder_edit.setText("")
        self.suspicious_toggle.setChecked(False)
        self.update_results()

    def copy_summary(self) -> None:
        eye_input, _message = self._build_eye_input()
        if eye_input is None:
            return
        result = compute_result(eye_input)
        if not result.valid:
            return

        status_label = (
            "Cumple"
            if result.overall_status == "ok"
            else "Cerca"
            if result.overall_status == "warning"
            else "No cumple"
        )
        laser_text = ""
        if result.laser is not None:
            interpolated = ", interpolado" if result.laser.interpolated else ""
            laser_text = (
                f"graduación {self._describe_refraction(result.laser)}, "
                f"ZO {_format_number(result.laser.optical_zone_mm)} mm (Teneo{interpolated}), "
            )
        flap_text = f"flap {result.subtract_um} µm" if result.subtract_um else "sin flap"
        summary = (
            f"{result.procedure_label}, {laser_text}paqui preop {eye_input.paqui_preop_um} µm, "
            f"ablación {result.ablation_um} µm ({result.ablation_pct:.1f}%), "
            f"LER {result.ler_um} µm ({result.ler_pct:.1f}%), "
            f"post-op {result.postop_paqui_um} µm, {flap_text}, "
            f"estado {status_label}, limita {result.limit_factor}, "
            f"máx segura {result.ablation_max_safe_um} µm, margen {result.margin_um:+d} µm."
        )
        QGuiApplication.clipboard().setText(summary)


def main() -> None:
    app = QApplication([])
    apply_app_style(app)
    window = MainWindow()
    window.resize(860, 760)
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
