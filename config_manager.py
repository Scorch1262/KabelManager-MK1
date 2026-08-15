# -*- coding: utf-8 -*-
"""
config_manager.py
==================
Kuemmert sich um die zwei Konfigurationsdateien, die immer im selben
Verzeichnis wie die exe / das Skript liegen:

  - kabelfarben_config.json : Vorschlags-Farben je Standard-Verkabelung
                               (UART, I2C, SPI, ...). Frei editierbar.
                               Aenderungen wirken sich nur auf NEU
                               angelegte Standard-Kabel dieses Typs aus.
  - verkabelung_config.json : Das komplette Verkabelungsnetz (Ansicht,
                               Elemente, Verbindungen).
"""

import os
import sys
import copy
import json

from standards import DEFAULT_STANDARDS

APP_NAME = "Kabelplan"


def get_base_dir():
    """Verzeichnis neben der exe (PyInstaller --onefile) bzw. neben dem
    Skript beim Testen mit 'python app.py'."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


BASE_DIR = get_base_dir()
NETZ_CONFIG_PATH = os.path.join(BASE_DIR, "verkabelung_config.json")
FARBEN_CONFIG_PATH = os.path.join(BASE_DIR, "kabelfarben_config.json")

DEFAULT_NETZ_CONFIG = {
    "_kommentar": "Diese Datei wird vom Kabelplan-Programm gelesen und "
                  "geschrieben. Manuelle Aenderungen sind moeglich, aber "
                  "bitte gueltiges JSON beibehalten.",
    "view": {
        "zoom": 1.0,
        "pan_x": 60,
        "pan_y": 60,
        "show_grid": True,
        "snap_to_grid": True,
        "grid_size": 20,
    },
    "mode": "edit",
    "elements": [],
    "connections": [],
}

DEFAULT_FARBEN_CONFIG_KOMMENTAR = (
    "Diese Datei enthaelt die Vorschlags-Kabelfarben je Standard-"
    "Verkabelung (z. B. I2C: SDA = gruen, SCL = gelb). Sie kann von Hand "
    "angepasst werden (gueltiges JSON beachten). Aenderungen wirken sich "
    "nur auf NEU angelegte Standard-Verbindungen dieses Typs aus - "
    "bestehende Kabel im Plan behalten ihre einmal gewaehlte Farbe."
)


def _default_farben_config():
    return {
        "_kommentar": DEFAULT_FARBEN_CONFIG_KOMMENTAR,
        "standards": copy.deepcopy(DEFAULT_STANDARDS),
    }


def _atomic_write(path, data):
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, path)


def load_netz_config():
    if not os.path.exists(NETZ_CONFIG_PATH):
        save_netz_config(DEFAULT_NETZ_CONFIG)
        return copy.deepcopy(DEFAULT_NETZ_CONFIG)
    try:
        with open(NETZ_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        for key, value in DEFAULT_NETZ_CONFIG.items():
            if key not in data:
                data[key] = copy.deepcopy(value)
        return data
    except Exception as exc:  # noqa: BLE001
        print(f"[WARNUNG] verkabelung_config.json konnte nicht gelesen "
              f"werden ({exc}). Erzeuge neue Standardkonfiguration.")
        save_netz_config(DEFAULT_NETZ_CONFIG)
        return copy.deepcopy(DEFAULT_NETZ_CONFIG)


def save_netz_config(data):
    _atomic_write(NETZ_CONFIG_PATH, data)


def load_farben_config():
    if not os.path.exists(FARBEN_CONFIG_PATH):
        default = _default_farben_config()
        save_farben_config(default)
        return copy.deepcopy(default)
    try:
        with open(FARBEN_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "standards" not in data or not isinstance(data["standards"], dict):
            data["standards"] = copy.deepcopy(DEFAULT_STANDARDS)
        return data
    except Exception as exc:  # noqa: BLE001
        print(f"[WARNUNG] kabelfarben_config.json konnte nicht gelesen "
              f"werden ({exc}). Erzeuge neue Standardkonfiguration.")
        default = _default_farben_config()
        save_farben_config(default)
        return copy.deepcopy(default)


def save_farben_config(data):
    _atomic_write(FARBEN_CONFIG_PATH, data)
