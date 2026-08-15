# -*- coding: utf-8 -*-
"""
models.py
=========
Einfache Hilfsfunktionen zum Erzeugen neuer Elemente/Verbindungen.
Es werden bewusst reine dict-Strukturen verwendet (kein ORM/Dataclass-
Zwang), damit sie 1:1 als JSON in der Netz-Konfigurationsdatei gespeichert
werden koennen.
"""

import uuid

ELEMENT_WIDTH = 170
ELEMENT_HEIGHT = 80
PIN_SPACING = 26


def new_id(prefix="el"):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def new_element(name="Neues Element", typ="Sonstiges", location="", x=100, y=100):
    return {
        "id": new_id("el"),
        "name": name,
        "type": typ,
        "location": location,
        "x": x,
        "y": y,
        "pins": [],          # Liste von Strings (Anschlussnamen)
        "pin_side": "unten",  # unten/oben/links/rechts
        "pin_mirror": False,
    }


def new_single_connection(from_element, from_pin, to_element, to_pin,
                           color="#3ad6ff", thickness=3, label=""):
    return {
        "id": new_id("conn"),
        "kind": "einzel",
        "from_element": from_element,
        "from_pin": from_pin,   # Pinname (String) oder None
        "to_element": to_element,
        "to_pin": to_pin,
        "color": color,
        "thickness": thickness,
        "label": label,
    }


def new_standard_connection(from_element, to_element, standard_name, wires,
                             label=""):
    """wires: Liste von dicts {signal, farbe, von_anschluss, nach_anschluss}"""
    return {
        "id": new_id("conn"),
        "kind": "standard",
        "standard": standard_name,
        "from_element": from_element,
        "to_element": to_element,
        "label": label or standard_name,
        "expanded": False,
        "wires": wires,
    }
