"""Starter dashboard for the Flood Alert simulator.

This is a working skeleton, not the final design. It shows every piece of
data the UI needs from FloodController so the frontend can be restyled or
split into widgets without touching the core.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QMainWindow,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..core import FloodController, StepResult
from ..data import list_scenarios, load_scenario

# Colour groups follow the legend of the proposal's state diagram.
STATE_COLOURS = {
    "Normal": "#e9e6df",
    "Prep": "#f6dfb3",
    "PrepClear": "#f6dfb3",
    "Surge": "#f3c4c4",
    "Evac": "#f3c4c4",
    "Forced": "#f3c4c4",
    "Silenced": "#c8e8dc",
    "Recovery": "#c8e8dc",
    "Clearing": "#c8e8dc",
}

DEMO_TIMER_S = 3  # "Fast timer" option, so demos don't wait 30 s


class MainWindow(QMainWindow):
    def __init__(self, controller: FloodController | None = None) -> None:
        super().__init__()
        self.setWindowTitle("Flood Alert Controller (Moore machine simulation)")
        self.resize(1100, 720)

        self.ctl = controller or FloodController.from_config_dir()
        self.scenario_events: list = []
        self.scenario_pos = 0

        self.t_timer = QTimer(self)
        self.t_timer.setSingleShot(True)
        self.t_timer.timeout.connect(self.on_timer_expired)
        self.countdown = QTimer(self)
        self.countdown.setInterval(1000)
        self.countdown.timeout.connect(self.update_countdown)
        self.seconds_left = 0

        self._build()
        self.render(self.ctl.reset())

    # ================================================================ layout
    def _build(self) -> None:
        root = QWidget()
        layout = QHBoxLayout(root)
        layout.addWidget(self._controls(), 1)
        layout.addLayout(self._display(), 3)
        self.setCentralWidget(root)

    def _controls(self) -> QWidget:
        box = QGroupBox("Input")
        v = QVBoxLayout(box)

        v.addWidget(QLabel("Water level h (m), one reading per minute:"))
        self.level_input = QDoubleSpinBox()
        self.level_input.setRange(0.0, 30.0)
        self.level_input.setDecimals(2)
        self.level_input.setSingleStep(0.1)
        self.level_input.setValue(14.2)
        v.addWidget(self.level_input)

        self.next_btn = QPushButton("Next step (submit reading)")
        self.next_btn.clicked.connect(self.on_next_reading)
        v.addWidget(self.next_btn)

        self.fire_t_btn = QPushButton("Fire T now")
        self.fire_t_btn.clicked.connect(self.on_timer_expired)
        v.addWidget(self.fire_t_btn)

        self.fast_timer = QCheckBox(f"Fast timer ({DEMO_TIMER_S} s instead of {self.ctl.timer_s} s)")
        v.addWidget(self.fast_timer)

        self.timer_label = QLabel("Timer: idle")
        v.addWidget(self.timer_label)

        v.addSpacing(16)
        v.addWidget(QLabel("Scenario presets:"))
        self.scenario_box = QComboBox()
        for path in list_scenarios():
            self.scenario_box.addItem(load_scenario(path)["name"], str(path))
        v.addWidget(self.scenario_box)
        load_btn = QPushButton("Load scenario")
        load_btn.clicked.connect(self.on_load_scenario)
        v.addWidget(load_btn)
        self.play_btn = QPushButton("Play next scenario event")
        self.play_btn.clicked.connect(self.on_play_next)
        self.play_btn.setEnabled(False)
        v.addWidget(self.play_btn)
        self.scenario_label = QLabel("")
        self.scenario_label.setWordWrap(True)
        v.addWidget(self.scenario_label)

        v.addSpacing(16)
        reset_btn = QPushButton("Reset to q0 (Normal)")
        reset_btn.clicked.connect(self.on_reset)
        v.addWidget(reset_btn)
        v.addStretch()
        return box

    def _display(self) -> QVBoxLayout:
        v = QVBoxLayout()

        self.banner = QLabel()
        self.banner.setAlignment(Qt.AlignCenter)
        self.banner.setMinimumHeight(90)
        f = QFont()
        f.setPointSize(20)
        f.setBold(True)
        self.banner.setFont(f)
        v.addWidget(self.banner)

        self.detail = QLabel()
        self.detail.setAlignment(Qt.AlignCenter)
        v.addWidget(self.detail)

        mid = QHBoxLayout()
        dev_box = QGroupBox("Simulated devices (λ)")
        dl = QGridLayout(dev_box)
        self.device_labels: dict[str, QLabel] = {}
        for i, name in enumerate(self.ctl.driver.devices):
            dl.addWidget(QLabel(f"<b>{name}</b>"), i, 0)
            lab = QLabel()
            lab.setWordWrap(True)
            dl.addWidget(lab, i, 1)
            self.device_labels[name] = lab
        mid.addWidget(dev_box, 1)

        sms_box = QGroupBox("SMS outbox (sent only when λ changes)")
        sl = QVBoxLayout(sms_box)
        self.sms_list = QListWidget()
        self.sms_list.setWordWrap(True)
        sl.addWidget(self.sms_list)
        mid.addWidget(sms_box, 1)
        v.addLayout(mid)

        log_box = QGroupBox("Event log")
        ll = QVBoxLayout(log_box)
        self.log_table = QTableWidget(0, 6)
        self.log_table.setHorizontalHeaderLabels(["Step", "h (m)", "Δh", "Symbol", "State", "Output"])
        self.log_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.log_table.verticalHeader().setVisible(False)
        self.log_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        ll.addWidget(self.log_table)
        self.strings_label = QLabel()
        self.strings_label.setWordWrap(True)
        self.strings_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        ll.addWidget(self.strings_label)
        v.addWidget(log_box, 1)
        return v

    # ============================================================== actions
    def on_next_reading(self) -> None:
        self.render(self.ctl.feed_reading(self.level_input.value()))

    def on_timer_expired(self) -> None:
        self.render(self.ctl.fire_timer())

    def on_reset(self) -> None:
        self.scenario_events, self.scenario_pos = [], 0
        self.play_btn.setEnabled(False)
        self.scenario_label.setText("")
        self.log_table.setRowCount(0)
        self.sms_list.clear()
        self.render(self.ctl.reset())

    def on_load_scenario(self) -> None:
        sc = load_scenario(self.scenario_box.currentData())
        self.on_reset()
        self.scenario_events = sc["events"]
        self.scenario_label.setText(sc.get("description", ""))
        self.play_btn.setEnabled(True)

    def on_play_next(self) -> None:
        if self.scenario_pos >= len(self.scenario_events):
            self.play_btn.setEnabled(False)
            return
        event = self.scenario_events[self.scenario_pos]
        self.scenario_pos += 1
        self.render(self.ctl.feed_event(event))
        if self.scenario_pos >= len(self.scenario_events):
            self.play_btn.setEnabled(False)

    # ============================================================ rendering
    def render(self, r: StepResult) -> None:
        colour = STATE_COLOURS.get(r.state, "#ffffff")
        self.banner.setStyleSheet(f"background:{colour}; border-radius:8px; color:#222;")
        self.banner.setText(f"{r.state}  →  {r.output}\n{r.devices.settings['display']}")

        h = "--" if r.h is None else f"{r.h:.2f} m"
        dh = "--" if r.dh is None else f"{r.dh:+.2f} m"
        self.detail.setText(f"h = {h}    Δh = {dh}    last symbol = {r.symbol or '--'}")

        for name, lab in self.device_labels.items():
            lab.setText(r.devices.settings[name])

        for m in r.devices.sms_sent:
            self.sms_list.insertItem(0, f"[step {r.step}] {m.channel}: {m.text}")

        row = self.log_table.rowCount()
        self.log_table.insertRow(row)
        for col, val in enumerate([r.step, h, dh, r.symbol or "--", r.state, r.output]):
            item = QTableWidgetItem(str(val))
            if col >= 4:
                item.setBackground(QColor(colour))
            self.log_table.setItem(row, col, item)
        self.log_table.scrollToBottom()

        self.strings_label.setText(
            f"<b>Input string:</b> {' '.join(self.ctl.log.input_string) or '(empty)'}<br>"
            f"<b>Output string:</b> {' '.join(self.ctl.log.output_string)}"
        )
        self._sync_timer(r)

    def _sync_timer(self, r: StepResult) -> None:
        """Start the T countdown when entering Surge/Evac, cancel it on leaving."""
        if r.timer_armed and r.changed:
            self.seconds_left = DEMO_TIMER_S if self.fast_timer.isChecked() else self.ctl.timer_s
            self.t_timer.start(self.seconds_left * 1000)
            self.countdown.start()
        elif not r.timer_armed:
            self.t_timer.stop()
            self.countdown.stop()
        self.fire_t_btn.setEnabled(r.timer_armed)
        self.update_countdown(tick=False)

    def update_countdown(self, tick: bool = True) -> None:
        if tick and self.seconds_left > 0:
            self.seconds_left -= 1
        if self.t_timer.isActive():
            self.timer_label.setText(f"Timer: T fires in {self.seconds_left} s")
        else:
            self.timer_label.setText("Timer: idle")
