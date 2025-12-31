import os
import json
import struct
import threading
import time
import fcntl
from collections import deque
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, Qt
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QPushButton,
    QComboBox,
    QLineEdit,
    QDialogButtonBox,
    QListWidget,
    QListWidgetItem,
    QHBoxLayout,
    QLabel,
)
from PyQt6.QtGui import QKeyEvent
from aqt import mw
from aqt.utils import showInfo, askUser, tooltip

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "controller_config.json")

DEFAULT_MAPPINGS = {
    "A": " ",
    "B": "Return",
    "X": "z",
    "Y": "x",
    "LEFT": "Left",
    "RIGHT": "Right",
    "UP": "Up",
    "DOWN": "Down",
    "LEFT_SHOULDER": "Ctrl+Shift+z",
    "RIGHT_SHOULDER": "Ctrl+z",
    "START": "Return",
    "SELECT": "Backspace",
    "LEFT_TRIGGER": "Ctrl+Shift+z",
    "RIGHT_TRIGGER": "Ctrl+y",
}

JS_EVENT_BUTTON = 0x01
JS_EVENT_AXIS = 0x02
JS_EVENT_INIT = 0x80

JS_NAME_SIZE = 64

CONTROLLER_BUTTONS = {
    0: "A",
    1: "B",
    2: "X",
    3: "Y",
    4: "LEFT_SHOULDER",
    5: "RIGHT_SHOULDER",
    6: "SELECT",
    7: "START",
    8: "LEFT_STICK",
    9: "RIGHT_STICK",
    10: "LEFT_TRIGGER",
    11: "RIGHT_TRIGGER",
}

AXIS_BUTTONS = {"UP": -1, "DOWN": 1, "LEFT": -1, "RIGHT": 1}

EVENT_FORMAT = "@IhBB"
EVENT_SIZE = struct.calcsize(EVENT_FORMAT)


def find_joystick_device():
    """Find the first available joystick device"""
    for i in range(16):
        js_path = f"/dev/input/js{i}"
        if os.path.exists(js_path):
            return js_path
    return None


def is_8bitdo_controller(js_path):
    """Check if the joystick is a 8BitDo controller"""
    try:
        with open(js_path, "rb") as js:
            # Try to get the device name using ioctl
            name_bytes = bytearray(JS_NAME_SIZE)
            try:
                # JSIOCGNAME ioctl
                fcntl.ioctl(js, 0x80006A13, name_bytes)
                name = name_bytes.decode("utf-8", errors="ignore").rstrip("\x00")
                print(f"[Controller] Found joystick: {name}")
            except (OSError, IOError):
                pass
        return True
    except:
        return False


class ControllerRemapper(QObject):
    def __init__(self):
        super().__init__()
        self.mappings = self.load_config()
        self.running = False
        self.thread = None
        self.js_device = None
        self.last_state = {}
        self.event_queue = deque()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    return json.load(f)
            except:
                pass
        return DEFAULT_MAPPINGS.copy()

    def save_config(self):
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.mappings, f, indent=2)

    def parse_key_combination(self, combo):
        parts = combo.split("+")
        modifiers = []
        key = None
        for part in parts:
            part = part.strip().lower()
            if part in ["ctrl", "control"]:
                modifiers.append("ctrl")
            elif part in ["shift"]:
                modifiers.append("shift")
            elif part in ["alt"]:
                modifiers.append("alt")
            else:
                key = part
        return modifiers, key

    def get_key_code(self, key):
        """Convert a key name to Qt key code"""
        from PyQt6.QtCore import Qt

        key_lower = key.lower()

        # Single character keys
        if len(key) == 1:
            return getattr(Qt, f"Key_{key.upper()}", None)

        # Special keys mapping
        special_keys = {
            "space": Qt.Key_Space,
            "return": Qt.Key_Return,
            "enter": Qt.Key_Enter,
            "backspace": Qt.Key_Backspace,
            "delete": Qt.Key_Delete,
            "escape": Qt.Key_Escape,
            "tab": Qt.Key_Tab,
            "up": Qt.Key_Up,
            "down": Qt.Key_Down,
            "left": Qt.Key_Left,
            "right": Qt.Key_Right,
            "home": Qt.Key_Home,
            "end": Qt.Key_End,
            "pageup": Qt.Key_PageUp,
            "pagedown": Qt.Key_PageDown,
            "f1": Qt.Key_F1,
            "f2": Qt.Key_F2,
            "f3": Qt.Key_F3,
            "f4": Qt.Key_F4,
            "f5": Qt.Key_F5,
            "f6": Qt.Key_F6,
            "f7": Qt.Key_F7,
            "f8": Qt.Key_F8,
            "f9": Qt.Key_F9,
            "f10": Qt.Key_F10,
            "f11": Qt.Key_F11,
            "f12": Qt.Key_F12,
        }

        return special_keys.get(key_lower, None)

    def send_key_event(self, key_combo):
        if not key_combo:
            return

        modifiers, key = self.parse_key_combination(key_combo)

        modifier_flags = Qt.KeyboardModifier.NoModifier
        if "ctrl" in modifiers:
            modifier_flags |= Qt.KeyboardModifier.ControlModifier
        if "shift" in modifiers:
            modifier_flags |= Qt.KeyboardModifier.ShiftModifier
        if "alt" in modifiers:
            modifier_flags |= Qt.KeyboardModifier.AltModifier

        if key:
            key_code = self.get_key_code(key)

            if key_code:
                focus_widget = mw.app.focusWidget()
                if focus_widget:
                    press_event = QKeyEvent(
                        QKeyEvent.KeyPress, key_code, modifier_flags, ""
                    )
                    release_event = QKeyEvent(
                        QKeyEvent.KeyRelease, key_code, modifier_flags, ""
                    )
                    mw.app.sendEvent(focus_widget, press_event)
                    time.sleep(0.01)
                    mw.app.sendEvent(focus_widget, release_event)

    def detect_controller(self):
        js_path = find_joystick_device()
        if not js_path:
            print("[Controller] No joystick device found")
            return False

        print(f"[Controller] Checking {js_path}")
        if not is_8bitdo_controller(js_path):
            print("[Controller] Controller check failed")
            return False

        try:
            self.js_device = open(js_path, "rb")
            # Set non-blocking mode
            import os as os_module

            flags = fcntl.fcntl(self.js_device, fcntl.F_GETFL)
            fcntl.fcntl(self.js_device, fcntl.F_SETFL, flags | os_module.O_NONBLOCK)
            print(f"[Controller] Successfully opened {js_path}")
            return True
        except Exception as e:
            print(f"[Controller] Error opening joystick: {e}")
            return False

        if not is_8bitdo_controller(js_path):
            return False

        try:
            self.js_device = open(js_path, "rb")
            # Set non-blocking mode
            import os as os_module

            flags = fcntl.fcntl(self.js_device, fcntl.F_GETFL)
            fcntl.fcntl(self.js_device, fcntl.F_SETFL, flags | os_module.O_NONBLOCK)
            return True
        except:
            return False

    def process_controller_input(self):
        if not self.js_device:
            return

        try:
            while True:
                data = self.js_device.read(EVENT_SIZE)
                if not data:
                    break
                if len(data) < EVENT_SIZE:
                    break

                timestamp, value, event_type, number = struct.unpack(EVENT_FORMAT, data)

                if event_type & JS_EVENT_BUTTON:
                    button_num = number
                    button_state = bool(value)
                    button_name = CONTROLLER_BUTTONS.get(button_num)

                    if button_name and button_state:
                        last_state = self.last_state.get(f"button_{button_num}", False)
                        if not last_state:
                            print(
                                f"[Controller] Button {button_num} ({button_name}) pressed"
                            )
                            key_combo = self.mappings.get(button_name)
                            print(f"[Controller] Mapped to: {key_combo}")
                            if key_combo:
                                self.send_key_event(key_combo)

                    self.last_state[f"button_{button_num}"] = button_state

                elif event_type & JS_EVENT_AXIS:
                    axis_num = number
                    axis_value = value / 32767.0  # Normalize to -1 to 1

                    if axis_num == 0:  # Horizontal axis
                        if axis_value < -0.5:
                            key = "axis_0_LEFT"
                            last_state = self.last_state.get(key, False)
                            if not last_state:
                                print(f"[Controller] Left axis pressed")
                                key_combo = self.mappings.get("LEFT")
                                if key_combo:
                                    self.send_key_event(key_combo)
                            self.last_state[key] = True
                        elif axis_value > 0.5:
                            key = "axis_0_RIGHT"
                            last_state = self.last_state.get(key, False)
                            if not last_state:
                                print(f"[Controller] Right axis pressed")
                                key_combo = self.mappings.get("RIGHT")
                                if key_combo:
                                    self.send_key_event(key_combo)
                            self.last_state[key] = True
                        else:
                            self.last_state.pop("axis_0_LEFT", None)
                            self.last_state.pop("axis_0_RIGHT", None)

                    elif axis_num == 1:  # Vertical axis
                        if axis_value < -0.5:
                            key = "axis_1_UP"
                            last_state = self.last_state.get(key, False)
                            if not last_state:
                                print(f"[Controller] Up axis pressed")
                                key_combo = self.mappings.get("UP")
                                if key_combo:
                                    self.send_key_event(key_combo)
                            self.last_state[key] = True
                        elif axis_value > 0.5:
                            key = "axis_1_DOWN"
                            last_state = self.last_state.get(key, False)
                            if not last_state:
                                print(f"[Controller] Down axis pressed")
                                key_combo = self.mappings.get("DOWN")
                                if key_combo:
                                    self.send_key_event(key_combo)
                            self.last_state[key] = True
                        else:
                            self.last_state.pop("axis_1_UP", None)
                            self.last_state.pop("axis_1_DOWN", None)

        except (OSError, IOError):
            pass

    def run_loop(self):
        print("[Controller] Starting run loop")
        if self.detect_controller():
            print("[Controller] Controller detected, starting input loop")
            while self.running:
                self.process_controller_input()
                time.sleep(0.01)
        else:
            print("[Controller] No controller detected")

        if self.js_device:
            try:
                self.js_device.close()
            except:
                pass
            self.js_device = None
        print("[Controller] Run loop ended")

    def start(self):
        if self.running:
            return True

        self.running = True
        self.thread = threading.Thread(target=self.run_loop, daemon=True)
        self.thread.start()
        return True

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
            self.thread = None


class ConfigDialog(QDialog):
    def __init__(self, remapper, parent=None):
        super().__init__(parent)
        self.remapper = remapper
        self.setWindowTitle("8BitDo Controller Remapper Settings")
        self.setModal(True)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        self.list_widget = QListWidget()
        for button_name, key_combo in self.remapper.mappings.items():
            item = QListWidgetItem(f"{button_name}: {key_combo}")
            self.list_widget.addItem(item)
        layout.addWidget(self.list_widget)

        form_layout = QFormLayout()

        self.button_combo = QComboBox()
        self.button_combo.addItems(list(CONTROLLER_BUTTONS.values()))
        self.button_combo.addItems(["UP", "DOWN", "LEFT", "RIGHT"])
        form_layout.addRow("Controller Button:", self.button_combo)

        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("e.g., z, Ctrl+z, Ctrl+Shift+z")
        form_layout.addRow("Keyboard Key:", self.key_input)

        layout.addLayout(form_layout)

        button_layout = QHBoxLayout()

        add_button = QPushButton("Add Mapping")
        add_button.clicked.connect(self.add_mapping)
        button_layout.addWidget(add_button)

        update_button = QPushButton("Update Mapping")
        update_button.clicked.connect(self.update_mapping)
        button_layout.addWidget(update_button)

        remove_button = QPushButton("Remove Mapping")
        remove_button.clicked.connect(self.remove_mapping)
        button_layout.addWidget(remove_button)

        layout.addLayout(button_layout)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def add_mapping(self):
        button = self.button_combo.currentText()
        key_combo = self.key_input.text().strip()
        if button and key_combo:
            self.remapper.mappings[button] = key_combo
            self.remapper.save_config()
            self.refresh_list()

    def update_mapping(self):
        button = self.button_combo.currentText()
        key_combo = self.key_input.text().strip()
        if button and key_combo:
            self.remapper.mappings[button] = key_combo
            self.remapper.save_config()
            self.refresh_list()

    def remove_mapping(self):
        button = self.button_combo.currentText()
        if button in self.remapper.mappings:
            del self.remapper.mappings[button]
            self.remapper.save_config()
            self.refresh_list()

    def refresh_list(self):
        self.list_widget.clear()
        for button_name, key_combo in self.remapper.mappings.items():
            item = QListWidgetItem(f"{button_name}: {key_combo}")
            self.list_widget.addItem(item)


remapper = None


def open_config():
    global remapper
    if remapper:
        dialog = ConfigDialog(remapper, mw)
        if dialog.exec():
            tooltip("Settings saved")


def start_remapper():
    global remapper
    if not remapper:
        remapper = ControllerRemapper()

    if remapper.start():
        tooltip("Controller remapper started")
    else:
        tooltip("Failed to start controller remapper")


def stop_remapper():
    global remapper
    if remapper:
        remapper.stop()
        tooltip("Controller remapper stopped")


def setup_menu():
    menu = mw.form.menuTools
    menu.addSeparator()

    start_action = menu.addAction("Start Controller Remapper")
    start_action.triggered.connect(start_remapper)

    stop_action = menu.addAction("Stop Controller Remapper")
    stop_action.triggered.connect(stop_remapper)

    config_action = menu.addAction("Controller Remapper Settings")
    config_action.triggered.connect(open_config)


setup_menu()
start_remapper()
