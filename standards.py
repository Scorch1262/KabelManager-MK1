# -*- coding: utf-8 -*-
"""
standards.py
============
Enthaelt die werkseitigen Vorlagen fuer "Standard-Verkabelungen" (Busse /
Steckverbinder-Standards), die beim allerersten Start in die editierbare
Datei "kabelfarben_config.json" (siehe config_manager.py) geschrieben
werden. Diese Datei kann danach von Hand angepasst werden; Aenderungen
wirken sich nur auf NEU angelegte Kabel dieses Standards aus, bestehende
Verbindungen behalten ihre einmal gewaehlten Farben.
"""

# Jeder Standard besteht aus einer Liste von "Leitungen" (einzelnen Adern),
# jede mit einem Signalnamen und einer vorgeschlagenen Kabelfarbe (Hex).
DEFAULT_STANDARDS = {
    "UART": {
        "beschreibung": "Serielle Schnittstelle (asynchron, 2-4 Adern)",
        "leitungen": [
            {"signal": "TX",  "farbe": "#ff8a3d"},
            {"signal": "RX",  "farbe": "#3ad6ff"},
            {"signal": "VCC", "farbe": "#e74c3c"},
            {"signal": "GND", "farbe": "#2b2b2b"},
        ],
    },
    "I2C": {
        "beschreibung": "Inter-Integrated Circuit Bus",
        "leitungen": [
            {"signal": "SDA", "farbe": "#2ecc71"},
            {"signal": "SCL", "farbe": "#f1c40f"},
            {"signal": "VCC", "farbe": "#e74c3c"},
            {"signal": "GND", "farbe": "#2b2b2b"},
        ],
    },
    "SPI": {
        "beschreibung": "Serial Peripheral Interface",
        "leitungen": [
            {"signal": "MOSI", "farbe": "#9b59b6"},
            {"signal": "MISO", "farbe": "#3498db"},
            {"signal": "SCK",  "farbe": "#f1c40f"},
            {"signal": "CS",   "farbe": "#e67e22"},
            {"signal": "VCC",  "farbe": "#e74c3c"},
            {"signal": "GND",  "farbe": "#2b2b2b"},
        ],
    },
    "LIN": {
        "beschreibung": "Local Interconnect Network",
        "leitungen": [
            {"signal": "LIN",  "farbe": "#8e44ad"},
            {"signal": "VCC",  "farbe": "#e74c3c"},
            {"signal": "GND",  "farbe": "#2b2b2b"},
        ],
    },
    "SENT": {
        "beschreibung": "Single Edge Nibble Transmission",
        "leitungen": [
            {"signal": "SENT", "farbe": "#1abc9c"},
            {"signal": "VCC",  "farbe": "#e74c3c"},
            {"signal": "GND",  "farbe": "#2b2b2b"},
        ],
    },
    "Ethernet (Cat5e/6, T568B)": {
        "beschreibung": "8-adriges Ethernet-Kabel nach T568B-Belegung",
        "leitungen": [
            {"signal": "TX+ (Orange/Weiss)", "farbe": "#f5a623"},
            {"signal": "TX- (Orange)",       "farbe": "#e67e22"},
            {"signal": "RX+ (Gruen/Weiss)",  "farbe": "#7fd97f"},
            {"signal": "Bias+ (Blau)",       "farbe": "#3498db"},
            {"signal": "Bias- (Blau/Weiss)", "farbe": "#aed6f1"},
            {"signal": "RX- (Gruen)",        "farbe": "#2ecc71"},
            {"signal": "Bias2+ (Braun/Weiss)","farbe": "#d2b48c"},
            {"signal": "Bias2- (Braun)",     "farbe": "#8b5a2b"},
        ],
    },
    "Analog Video (FPV)": {
        "beschreibung": "Analoges FPV-Videosignal (z. B. Kamera zu VTX)",
        "leitungen": [
            {"signal": "Video", "farbe": "#f1c40f"},
            {"signal": "VCC",   "farbe": "#e74c3c"},
            {"signal": "GND",   "farbe": "#2b2b2b"},
        ],
    },
    "DJI Air Unit": {
        "beschreibung": "DJI/Caddx Air-Unit-Anschluss (Digitalsystem)",
        "leitungen": [
            {"signal": "VBAT (9-25V)", "farbe": "#e74c3c"},
            {"signal": "GND",          "farbe": "#2b2b2b"},
            {"signal": "UART2 TX (RC)","farbe": "#ff8a3d"},
            {"signal": "UART2 RX (RC)","farbe": "#3ad6ff"},
            {"signal": "Video In",     "farbe": "#f1c40f"},
        ],
    },
    "CAN-Bus": {
        "beschreibung": "Controller Area Network (differentiell)",
        "leitungen": [
            {"signal": "CAN-H", "farbe": "#f1c40f"},
            {"signal": "CAN-L", "farbe": "#3498db"},
            {"signal": "VCC",   "farbe": "#e74c3c"},
            {"signal": "GND",   "farbe": "#2b2b2b"},
        ],
    },
    "PWM": {
        "beschreibung": "Pulsweitenmodulation (z. B. Servo/ESC)",
        "leitungen": [
            {"signal": "Signal", "farbe": "#f1c40f"},
            {"signal": "VCC",    "farbe": "#e74c3c"},
            {"signal": "GND",    "farbe": "#2b2b2b"},
        ],
    },
}

# Farbe, in der gebuendelte Standard-Verbindungen im nicht aufgeklappten
# Zustand angezeigt werden (dicke, einfarbige Sammelleitung).
BUNDLE_LINE_COLOR = "#9aa5b1"

# Reihenfolge fuer neue Elemente vorgeschlagener Elementtypen.
ELEMENT_TYPES = [
    "Steckverbinder",
    "Platine / PCB",
    "Sensor",
    "Aktor",
    "Stromversorgung",
    "Verteiler",
    "Sonstiges",
]
