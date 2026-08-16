#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verkabelungsplan-Server
========================
Startet einen lokalen Webserver, der einen interaktiven, frei platzierbaren
Verkabelungsplan bereitstellt (Elemente wie Stromversorgung, Batterie,
Motor, Antrieb, Platine, Steuergeraet, Klemmleiste, Delay, Raspberry Pi,
Kamera, Router, Relay usw., verbunden durch farbige Leitungen). Erreichbar
unter der IP des Rechners im lokalen Netzwerk.

Konfiguration (Ansicht, Elemente, Verbindungen) wird menschenlesbar in
"config.json" gespeichert, die im selben Verzeichnis wie das Skript / die
exe liegt.

Zusaetzlich stellt der Server zwei Export-Endpunkte bereit:
  - POST /api/export/pdf      -> Verkabelungsplan als PDF (Querformat,
                                  wahlweise dunkler oder heller Hintergrund)
  - POST /api/export/netlist  -> Verbindungsliste ("Netzliste") als CSV
Beide erhalten den aktuellen (ggf. noch nicht gespeicherten) Stand direkt
vom Frontend im Request-Body, damit auch ungesicherte Aenderungen exportiert
werden koennen.
"""

import os
import sys
import io
import csv
import json
import math
import socket
import re
import threading
import webbrowser
import copy
from datetime import datetime

from flask import Flask, request, jsonify, render_template, send_file

try:
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.colors import HexColor
    from reportlab.pdfgen import canvas as rl_canvas
    REPORTLAB_AVAILABLE = True
except ImportError:  # reportlab fehlt -> PDF-Export liefert verstaendliche Fehlermeldung
    REPORTLAB_AVAILABLE = False

try:
    import paho.mqtt.client as mqtt_client
    MQTT_AVAILABLE = True
except ImportError:  # paho-mqtt fehlt -> MQTT-Schaltflaechen liefern verstaendliche Fehlermeldung
    MQTT_AVAILABLE = False

# --------------------------------------------------------------------------
# Pfad-Hilfsfunktionen (wichtig für PyInstaller --onefile)
# --------------------------------------------------------------------------

def get_base_dir():
    """Verzeichnis, in dem die exe (bzw. das Skript) liegt.
    Hier wird die config.json gespeichert -> vom Nutzer editierbar."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def get_resource_dir():
    """Verzeichnis, aus dem gebündelte Ressourcen (templates/static) beim
    Ausführen als exe gelesen werden (PyInstaller entpackt nach _MEIPASS)."""
    if getattr(sys, "frozen", False):
        return sys._MEIPASS  # type: ignore[attr-defined]
    return os.path.dirname(os.path.abspath(__file__))


BASE_DIR = get_base_dir()
RES_DIR = get_resource_dir()
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

# --------------------------------------------------------------------------
# Standardkonfiguration
# --------------------------------------------------------------------------

DEFAULT_CONFIG = {
    "_kommentar": "Diese Datei wird vom Verkabelungsplan-Programm gelesen und "
                  "geschrieben. Manuelle Aenderungen sind moeglich, aber "
                  "bitte gueltiges JSON beibehalten.",
    "server": {
        "host": "0.0.0.0",
        "port": 8080
    },
    "view": {
        "zoom": 1.0,
        "pan_x": 0,
        "pan_y": 0,
        "show_grid": True,
        "snap_to_grid": True,
        "grid_size": 40
    },
    "mode": "edit",
    "elements": [],
    "connections": [],
    "cables": []
}


def load_config():
    if not os.path.exists(CONFIG_PATH):
        save_config(DEFAULT_CONFIG)
        return copy.deepcopy(DEFAULT_CONFIG)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Fehlende Top-Level-Schluessel mit Standardwerten auffuellen
        for key, value in DEFAULT_CONFIG.items():
            if key not in data:
                data[key] = value
        return data
    except Exception as exc:  # noqa: BLE001
        print(f"[WARNUNG] config.json konnte nicht gelesen werden ({exc}). "
              f"Erzeuge neue Standardkonfiguration.")
        save_config(DEFAULT_CONFIG)
        return copy.deepcopy(DEFAULT_CONFIG)


def save_config(data):
    tmp_path = CONFIG_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, CONFIG_PATH)


# --------------------------------------------------------------------------
# Flask-App
# --------------------------------------------------------------------------

app = Flask(
    __name__,
    template_folder=os.path.join(RES_DIR, "templates"),
    static_folder=os.path.join(RES_DIR, "static"),
)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/config", methods=["GET"])
def api_get_config():
    return jsonify(load_config())


@app.route("/api/config", methods=["POST"])
def api_save_config():
    data = request.get_json(force=True, silent=True)
    if not isinstance(data, dict):
        return jsonify({"status": "error", "message": "Ungueltige Daten"}), 400
    save_config(data)
    return jsonify({"status": "ok"})


# --------------------------------------------------------------------------
# Export: gemeinsame Hilfsfunktionen (Datenmodell-Kenntnisse, siehe
# HANDOVER.md Abschnitt 4 - muessen mit static/app.js im Gleichschritt
# gepflegt werden, insbesondere Portlayout und Elementgroesse).
# --------------------------------------------------------------------------

ELEMENT_W = 148
ELEMENT_H = 76

# Menschenlesbare Bezeichnungen je Elementtyp fuer PDF/Netzliste. Enthaelt
# sowohl die aktuellen (v3.1.0) als auch die frueheren (Netzwerkplan-)
# Typen, damit auch alte config.json-Dateien sinnvoll beschriftet werden.
ELEMENT_LABELS = {
    "power_supply": "Stromversorgung",
    "battery": "Batterie",
    "motor": "Motor",
    "actuator": "Antrieb",
    "board": "Platine",
    "controller": "Steuergeraet",
    "terminal_block": "Klemmleiste",
    "delay": "Delay",
    "raspberry_pi": "Raspberry Pi",
    "camera": "Kamera",
    "router": "Router",
    "ethernet_switch": "Ethernet Switch",
    "relay": "Relay",
    "switch_2pos": "Schalter",
    "button": "Taster",
    "potentiometer": "Poti",
    "generic": "Sonstiges",
    # Legacy-Typen aus frueheren Netzwerkplan-Versionen (Abwaertskompatibilitaet):
    "gateway": "Gateway",
    "switch": "Switch",
    "server": "Server",
    "pc": "PC",
    "laptop": "Laptop",
    "lan_socket": "LAN-Dose",
    "patchpanel": "Patchfeld",
}

# Netzwerkgeraete: hier bleibt es bei "Port"/"Ports" statt "Pin"/"Pins" in
# Netzliste/PDF (muss zu isNetworkDevice() in static/app.js passen).
NETWORK_DEVICE_TYPES = {
    "router", "ethernet_switch",
    "switch", "patchpanel", "gateway", "server", "pc", "laptop", "lan_socket",
}


def is_network_device(el_type):
    return el_type in NETWORK_DEVICE_TYPES


def port_word(el_type):
    return "Port" if is_network_device(el_type) else "Pin"

# Elementtypen mit Ports/Pins + deren Standard-/Fallback-Anzahl (muss zu
# DEFAULT_PORTS in static/app.js passen). Bei relay/motor ist dies nur der
# Fallback fuer die jeweilige Standard-Bauart (schliesser/dc_ac) - die
# tatsaechliche Anzahl steht im Element als "ports"-Feld. board/raspberry_pi
# starten standardmaessig ohne Pins (0, optional individuell ergaenzbar).
DEFAULT_PORTS_PY = {
    "controller": 8,
    "terminal_block": 12,
    "router": 4,
    "ethernet_switch": 8,
    "relay": 4,
    "motor": 2,
    "power_supply": 2,
    "battery": 2,
    "switch_2pos": 2,
    "button": 2,
    "potentiometer": 3,
    "board": 0,
    "raspberry_pi": 0,
    # Legacy:
    "switch": 8,
    "patchpanel": 24,
}
DUAL_SIDE_TYPES = {"terminal_block", "patchpanel"}
INDIVIDUAL_PIN_TYPES = {"board", "raspberry_pi"}
OPPOSITE_SIDE = {"bottom": "top", "top": "bottom", "left": "right", "right": "left"}
PORT_SIDES = ("bottom", "left", "top", "right")


def element_label(el_type):
    return ELEMENT_LABELS.get(el_type, ELEMENT_LABELS["generic"])


def has_ports(el_type):
    return el_type in DEFAULT_PORTS_PY


def get_port_count(el):
    if not has_ports(el.get("type")):
        return 0
    try:
        n = int(el.get("ports"))
        if n > 0:
            return n
    except (TypeError, ValueError):
        pass
    return DEFAULT_PORTS_PY.get(el.get("type"), 0)


def get_port_name(el, index):
    names = el.get("port_names")
    if isinstance(names, list) and 0 <= index < len(names):
        name = names[index]
        if isinstance(name, str) and name.strip():
            return name.strip()
    return None


def get_pin_kind(el, index):
    kinds = el.get("pin_kinds")
    if isinstance(kinds, list) and 0 <= index < len(kinds) and kinds[index] in ("pin", "usb", "lan"):
        return kinds[index]
    return "pin"


def port_label(el, port_index):
    if port_index is None:
        return ""
    word = port_word(el.get("type"))
    kind = get_pin_kind(el, int(port_index)) if el.get("type") == "raspberry_pi" else "pin"
    kind_label = {"usb": "USB", "lan": "LAN"}.get(kind)
    label = (kind_label or word) + " " + str(int(port_index) + 1)
    name = get_port_name(el, int(port_index))
    if name:
        label += " (" + name + ")"
    return label


def element_center(el):
    x = el.get("x", 0) or 0
    y = el.get("y", 0) or 0
    return x + ELEMENT_W / 2.0, y + ELEMENT_H / 2.0


def get_pin_side_individual(el, index):
    """Individuelle Seite eines Pins bei Platine/Raspberry Pi (siehe
    getPinSide() in static/app.js) - jeder Pin traegt seine eigene Seite in
    el.pin_sides statt einer gemeinsamen el.port_side."""
    sides = el.get("pin_sides")
    if isinstance(sides, list) and 0 <= index < len(sides) and sides[index] in PORT_SIDES:
        return sides[index]
    return ["bottom", "right", "top", "left"][index % 4]


def port_point(el, port_index, side_key):
    """Approximiert die Andockposition eines Ports/Pins fuer den Export, in
    Anlehnung an die Portleisten-Anordnung im Frontend (computePortRelOffsets
    / buildPortsBar / buildIndividualPinsLayer in static/app.js). Muss nicht
    pixelgenau sein, nur optisch stimmig fuer PDF/Netzliste."""
    n = get_port_count(el)
    if n <= 0 or port_index is None or not (0 <= port_index < n):
        return element_center(el)

    x = el.get("x", 0) or 0
    y = el.get("y", 0) or 0
    el_type = el.get("type")

    if el_type in INDIVIDUAL_PIN_TYPES:
        # Platine/Raspberry Pi: jeder Pin hat seine eigene Seite; innerhalb
        # einer Seite werden die zugehoerigen Pins gleichmaessig verteilt,
        # in der Reihenfolge ihres Pin-Index (wie buildIndividualPinsLayer).
        side = get_pin_side_individual(el, port_index)
        same_side_indices = [i for i in range(n) if get_pin_side_individual(el, i) == side]
        pos_in_side = same_side_indices.index(port_index)
        count_on_side = len(same_side_indices)
        frac = (pos_in_side + 0.5) / count_on_side
    else:
        primary_side = el.get("port_side")
        if primary_side not in PORT_SIDES:
            primary_side = "bottom"
        side = OPPOSITE_SIDE[primary_side] if side_key == "b" else primary_side
        idx = port_index
        if el.get("port_mirror"):
            idx = n - 1 - idx
        frac = (idx + 0.5) / n

    margin = 12.0
    if side in ("bottom", "top"):
        px = x + margin + frac * max(ELEMENT_W - 2 * margin, 1)
        py = y + ELEMENT_H if side == "bottom" else y
    else:
        py = y + margin + frac * max(ELEMENT_H - 2 * margin, 1)
        px = x + ELEMENT_W if side == "right" else x
    return px, py


def connection_endpoint(el, port_index, port_side):
    if port_index is not None and has_ports(el.get("type")):
        return port_point(el, port_index, "b" if port_side == "b" else "a")
    return element_center(el)


def connection_direction(el, port_index, port_side):
    """Austrittsrichtung an einem Port/Pin (siehe connectionDirection() in
    static/app.js) - noetig, damit die PDF-Kurve exakt wie in der
    Webansicht senkrecht von der Anschlussseite abgeht."""
    if port_index is None or not has_ports(el.get("type")):
        return None
    el_type = el.get("type")
    if el_type in INDIVIDUAL_PIN_TYPES:
        side = get_pin_side_individual(el, port_index)
    else:
        primary_side = el.get("port_side")
        if primary_side not in PORT_SIDES:
            primary_side = "bottom"
        side = OPPOSITE_SIDE[primary_side] if port_side == "b" else primary_side
    return {"bottom": (0, 1), "top": (0, -1), "left": (-1, 0), "right": (1, 0)}.get(side)


def safe_hex_color(value, fallback):
    if isinstance(value, str) and re.match(r"^#[0-9a-fA-F]{6}$", value):
        return value
    return fallback


def get_cable(cfg, cable_id):
    if not cable_id:
        return None
    for cab in cfg.get("cables", []) or []:
        if isinstance(cab, dict) and cab.get("id") == cable_id:
            return cab
    return None


# --------------------------------------------------------------------------
# Export: Netzliste (CSV)
# --------------------------------------------------------------------------

@app.route("/api/export/netlist", methods=["POST"])
def api_export_netlist():
    payload = request.get_json(force=True, silent=True) or {}
    cfg = payload.get("config")
    if not isinstance(cfg, dict):
        cfg = load_config()
    elements = {el.get("id"): el for el in cfg.get("elements", []) if isinstance(el, dict)}

    buf = io.StringIO()
    buf.write("\ufeff")  # BOM, damit Excel Umlaute korrekt anzeigt
    writer = csv.writer(buf, delimiter=";")
    writer.writerow([
        "Nr", "Von", "Von-Typ", "Von-Ort", "Von-Anschluss",
        "Nach", "Nach-Typ", "Nach-Ort", "Nach-Anschluss",
        "Farbe", "Staerke", "Bezeichnung", "Kabel",
    ])

    for i, conn in enumerate(cfg.get("connections", []), start=1):
        if not isinstance(conn, dict):
            continue
        f = elements.get(conn.get("from"))
        t = elements.get(conn.get("to"))
        if not f or not t:
            continue
        from_port = conn.get("from_port")
        to_port = conn.get("to_port")
        cable = get_cable(cfg, conn.get("cable_id"))
        writer.writerow([
            i,
            f.get("name", "") or "", element_label(f.get("type")), f.get("location", "") or "",
            port_label(f, from_port) if from_port is not None else "",
            t.get("name", "") or "", element_label(t.get("type")), t.get("location", "") or "",
            port_label(t, to_port) if to_port is not None else "",
            conn.get("color", "") or "",
            conn.get("thickness", "") if conn.get("thickness") is not None else "",
            conn.get("label", "") or "",
            (cable.get("name", "") if cable else "") or "",
        ])

    mem = io.BytesIO(buf.getvalue().encode("utf-8"))
    mem.seek(0)
    filename = "Netzliste_" + datetime.now().strftime("%Y-%m-%d_%H%M") + ".csv"
    return send_file(mem, mimetype="text/csv; charset=utf-8",
                      as_attachment=True, download_name=filename)


# --------------------------------------------------------------------------
# Export: PDF (Querformat, dunkler oder heller Hintergrund)
# --------------------------------------------------------------------------

PDF_THEMES = {
    "dark": {
        "bg": "#05070a",
        "el_fill": "#10151d",
        "el_border": "#3ad6ff",
        "text": "#e8edf4",
        "text_dim": "#9aa7b8",
        "port_fill": "#161c26",
    },
    "light": {
        "bg": "#ffffff",
        "el_fill": "#f4f6f9",
        "el_border": "#2a3b55",
        "text": "#12161d",
        "text_dim": "#4a5568",
        "port_fill": "#e8edf4",
    },
}


def _normalize(vx, vy):
    length = math.hypot(vx, vy) or 1.0
    return vx / length, vy / length


CONN_STUB = 26.0     # px, Laenge der senkrechten Stichleitung am Port/Pin
CONN_CORNER_R = 10.0  # px, Eckenradius an Knickpunkten


def _points_equal(a, b):
    return abs(a[0] - b[0]) < 0.01 and abs(a[1] - b[1]) < 0.01


def _path_midpoint_normal(a, b):
    """Python-Aequivalent zu pathMidpointNormal() in static/app.js: Einheits-
    vektor senkrecht zur lokalen Segmentrichtung, damit Bezeichnungen auch
    bei rein senkrechten Leitungssegmenten (durch die orthogonale
    Routenfuehrung haeufig) seitlich NEBEN statt AUF der Linie sitzen."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy) or 1.0
    return (dy / length, -dx / length)


def build_routed_points(points, dir1, dir2):
    """Python-Nachbildung von buildRoutedPoints() in static/app.js - MUSS
    mit dessen Geometrie exakt uebereinstimmen, damit die PDF-Leitungen an
    exakt derselben Stelle und mit derselben Form verlaufen wie die
    Webansicht (gerade Streckenabschnitte, senkrechte Stichleitung an
    Ports/Pins, automatischer rechtwinkliger Verlauf dazwischen). points =
    [p1, ...wegpunkte, p2] (Tupel (x,y)). Gibt eine Liste von (x,y)-
    Eckpunkten zurueck (noch ohne Eckenrundung).
    Bekannte Einschraenkung (siehe ausfuehrlicher Kommentar bei
    buildRoutedPoints() in static/app.js): keine automatische Hindernis-
    Umgehung anderer Elemente."""
    p1, p2 = points[0], points[-1]
    has_waypoints = len(points) > 2
    direct_dist = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
    stub_len = max(4.0, min(CONN_STUB, (direct_dist / 3.0) if direct_dist else CONN_STUB))

    stub1 = (p1[0] + dir1[0] * stub_len, p1[1] + dir1[1] * stub_len) if dir1 else None
    stub2 = (p2[0] + dir2[0] * stub_len, p2[1] + dir2[1] * stub_len) if dir2 else None

    if has_waypoints:
        routed = [p1]
        if stub1:
            routed.append(stub1)
        routed.extend(points[1:-1])
        if stub2:
            routed.append(stub2)
        routed.append(p2)
    elif stub1 and stub2:
        axis1 = "h" if abs(dir1[0]) > abs(dir1[1]) else "v"
        axis2 = "h" if abs(dir2[0]) > abs(dir2[1]) else "v"
        if axis1 != axis2:
            # Siehe ausfuehrliche Begruendung bei buildRoutedPoints() in
            # static/app.js: Knick behaelt stub1s Koordinate auf der
            # dir1-Achse bei, springt nur auf der SENKRECHTEN Achse zu
            # stub2 - sonst drohte ein Reversal/Zacken direkt am Anschluss.
            bend = (stub1[0], stub2[1]) if axis1 == "h" else (stub2[0], stub1[1])
            routed = [p1, stub1, bend, stub2, p2]
        elif dir1[0] * dir2[0] + dir1[1] * dir2[1] < 0:
            # Gegenueberliegende Richtungen (Ports zeigen aufeinander zu) -> Knick auf halber Strecke.
            if axis1 == "h":
                mid_x = (stub1[0] + stub2[0]) / 2
                routed = [p1, stub1, (mid_x, stub1[1]), (mid_x, stub2[1]), stub2, p2]
            else:
                mid_y = (stub1[1] + stub2[1]) / 2
                routed = [p1, stub1, (stub1[0], mid_y), (stub2[0], mid_y), stub2, p2]
        else:
            # Gleiche Richtung auf derselben Achse -> Knick beim weiter aussen
            # liegenden Stub (nicht der Mitte), sonst degeneriertes 180°-Reversal.
            if axis1 == "h":
                jog_x = max(stub1[0], stub2[0]) if dir1[0] > 0 else min(stub1[0], stub2[0])
                routed = [p1, stub1, (jog_x, stub1[1]), (jog_x, stub2[1]), stub2, p2]
            else:
                jog_y = max(stub1[1], stub2[1]) if dir1[1] > 0 else min(stub1[1], stub2[1])
                routed = [p1, stub1, (stub1[0], jog_y), (stub2[0], jog_y), stub2, p2]
    elif stub1:
        # Siehe buildRoutedPoints() in static/app.js: Knick behaelt stub1s
        # Koordinate auf der dir1-Achse bei, springt nur senkrecht zu p2.
        axis1 = "h" if abs(dir1[0]) > abs(dir1[1]) else "v"
        bend = (stub1[0], p2[1]) if axis1 == "h" else (p2[0], stub1[1])
        routed = [p1, stub1, bend, p2]
    elif stub2:
        axis2 = "h" if abs(dir2[0]) > abs(dir2[1]) else "v"
        bend = (stub2[0], p1[1]) if axis2 == "h" else (p1[0], stub2[1])
        routed = [p1, bend, stub2, p2]
    else:
        routed = [p1, p2]

    deduped = [routed[0]]
    for pt in routed[1:]:
        if not _points_equal(pt, deduped[-1]):
            deduped.append(pt)
    return deduped


def build_connector_path_segments(points, dir1, dir2):
    """Python-Nachbildung von routedPointsToPath() - wandelt die Eckpunkte
    aus build_routed_points() in Zeichensegmente um (gerade Strecken,
    leicht abgerundete Ecken), im selben Format wie zuvor
    build_smooth_path_segments(): [("line",p0,p1)] fuer eine einzelne
    Gerade, sonst eine Liste aus ("line", p0, p1) und ("curve", p0, cpA,
    cpB, p1) Segmenten (Rundungen als quadratische, zu kubischen Bezier
    konvertierte Kurven – reportlab kennt kein natives "Q")."""
    routed = build_routed_points(points, dir1, dir2)
    if len(routed) < 2:
        return []
    if len(routed) == 2:
        return [("line", routed[0], routed[1])]

    segments = []
    cursor = routed[0]
    for i in range(1, len(routed) - 1):
        a, b, c = routed[i - 1], routed[i], routed[i + 1]
        in_len = math.hypot(b[0] - a[0], b[1] - a[1])
        out_len = math.hypot(c[0] - b[0], c[1] - b[1])
        r = min(CONN_CORNER_R, in_len / 2.0, out_len / 2.0)
        in_dx, in_dy = _normalize(b[0] - a[0], b[1] - a[1])
        out_dx, out_dy = _normalize(c[0] - b[0], c[1] - b[1])
        p_in = (b[0] - in_dx * r, b[1] - in_dy * r)
        p_out = (b[0] + out_dx * r, b[1] + out_dy * r)
        if not _points_equal(cursor, p_in):
            segments.append(("line", cursor, p_in))
        # Quadratische Bezier (SVG "Q", Kontrollpunkt b) als kubische Bezier
        # fuer reportlab: cp1 = p_in + 2/3*(b-p_in), cp2 = p_out + 2/3*(b-p_out).
        cp1 = (p_in[0] + 2.0 / 3.0 * (b[0] - p_in[0]), p_in[1] + 2.0 / 3.0 * (b[1] - p_in[1]))
        cp2 = (p_out[0] + 2.0 / 3.0 * (b[0] - p_out[0]), p_out[1] + 2.0 / 3.0 * (b[1] - p_out[1]))
        segments.append(("curve", p_in, cp1, cp2, p_out))
        cursor = p_out
    last = routed[-1]
    if not _points_equal(cursor, last):
        segments.append(("line", cursor, last))
    return segments


def build_pdf(cfg, theme_name):
    theme = PDF_THEMES.get(theme_name, PDF_THEMES["dark"])
    elements = [el for el in cfg.get("elements", []) if isinstance(el, dict)]
    connections = [c for c in cfg.get("connections", []) if isinstance(c, dict)]
    el_by_id = {el.get("id"): el for el in elements}

    page_w, page_h = landscape(A4)
    margin = 28
    title_h = 34
    avail_x0, avail_y0 = margin, margin
    avail_x1, avail_y1 = page_w - margin, page_h - margin - title_h

    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=(page_w, page_h))

    # Hintergrund
    c.setFillColor(HexColor(theme["bg"]))
    c.rect(0, 0, page_w, page_h, stroke=0, fill=1)

    # Titelzeile
    c.setFillColor(HexColor(theme["text"]))
    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin, page_h - margin - 14, "VERKABELUNGSPLAN")
    c.setFont("Helvetica", 9)
    c.setFillColor(HexColor(theme["text_dim"]))
    c.drawRightString(page_w - margin, page_h - margin - 12,
                       "Erstellt " + datetime.now().strftime("%d.%m.%Y %H:%M"))
    c.setStrokeColor(HexColor(theme["el_border"]))
    c.setLineWidth(0.75)
    c.line(margin, page_h - margin - title_h + 8, page_w - margin, page_h - margin - title_h + 8)

    if not elements:
        c.setFont("Helvetica", 12)
        c.setFillColor(HexColor(theme["text_dim"]))
        c.drawCentredString(page_w / 2, page_h / 2, "Keine Elemente vorhanden.")
        c.showPage()
        c.save()
        return buf.getvalue()

    # Bounding Box aller Elemente UND der tatsaechlich gerouteten
    # Verbindungspunkte (inkl. Stichleitungen/automatischer Knickpunkte,
    # nicht nur der rohen Element-/Wegpunkt-Koordinaten!) ermitteln, um den
    # Plan passend auf die Seite (Querformat) zu skalieren. Ohne die
    # gerouteten Punkte koennen Stichleitungen/Knicke, die ueber die reinen
    # Element-/Wegpunkt-Positionen hinausragen, am Seitenrand abgeschnitten
    # werden (z. B. wenn eine Leitung seitlich neben allen Elementen einen
    # Bogen macht).
    xs, ys = [], []
    for el in elements:
        x = el.get("x", 0) or 0
        y = el.get("y", 0) or 0
        xs += [x, x + ELEMENT_W]
        ys += [y, y + ELEMENT_H]
    for conn in connections:
        for wp in conn.get("waypoints") or []:
            if isinstance(wp, dict) and "x" in wp and "y" in wp:
                xs.append(wp["x"])
                ys.append(wp["y"])
        f = el_by_id.get(conn.get("from"))
        t = el_by_id.get(conn.get("to"))
        if not f or not t:
            continue
        p1 = connection_endpoint(f, conn.get("from_port"), conn.get("from_port_side"))
        p2 = connection_endpoint(t, conn.get("to_port"), conn.get("to_port_side"))
        dir1 = connection_direction(f, conn.get("from_port"), conn.get("from_port_side"))
        dir2 = connection_direction(t, conn.get("to_port"), conn.get("to_port_side"))
        waypoints = [(wp["x"], wp["y"]) for wp in (conn.get("waypoints") or [])
                     if isinstance(wp, dict) and "x" in wp and "y" in wp]
        for rx, ry in build_routed_points([p1] + waypoints + [p2], dir1, dir2):
            xs.append(rx)
            ys.append(ry)

    bbox_x0, bbox_x1 = min(xs), max(xs)
    bbox_y0, bbox_y1 = min(ys), max(ys)
    # Kleiner Sicherheitsabstand rundum, damit Leitungsbezeichnungen an den
    # aeussersten Punkten (die per drawCentredString auch nach links/oben
    # ueber ihren Ankerpunkt hinausragen koennen) nicht am Seitenrand
    # abgeschnitten werden.
    label_margin = 34
    bbox_x0 -= label_margin
    bbox_x1 += label_margin
    bbox_y0 -= label_margin
    bbox_y1 += label_margin
    bbox_w = max(bbox_x1 - bbox_x0, 1)
    bbox_h = max(bbox_y1 - bbox_y0, 1)

    avail_w = avail_x1 - avail_x0
    avail_h = avail_y1 - avail_y0
    scale = min(avail_w / bbox_w, avail_h / bbox_h, 1.6)
    off_x = avail_x0 + (avail_w - bbox_w * scale) / 2
    off_y = avail_y0 + (avail_h - bbox_h * scale) / 2

    def to_page(px, py):
        # Canvas-Y waechst nach unten, PDF-Y nach oben -> spiegeln.
        return (off_x + (px - bbox_x0) * scale,
                off_y + (bbox_y1 - py) * scale)

    # --- Verbindungen zeichnen (unter den Elementen) ---
    # Jede Leitung folgt exakt derselben Geometrie wie die Webansicht
    # (siehe build_routed_points()/buildRoutedPoints in static/app.js):
    # gerade Streckenabschnitte mit senkrechter Stichleitung an Ports/Pins
    # und automatischem rechtwinkligem Verlauf dazwischen.
    c.setLineJoin(1)
    c.setLineCap(1)

    # Kabel-Buendel: Verbindungen mit gleicher cable_id bekommen zusaetzlich
    # eine gemeinsame "Kabelmantel"-Linie in der Kabelfarbe UNTER den
    # einzelnen Adern, gezeichnet entlang der Route der ersten Verbindung
    # im Buendel (siehe renderConnections()/cable-sleeve in static/app.js).
    cables_by_id = {}
    for conn in connections:
        cable_id = conn.get("cable_id")
        if not cable_id:
            continue
        cables_by_id.setdefault(cable_id, []).append(conn)

    def conn_canvas_path(conn):
        f = el_by_id.get(conn.get("from"))
        t = el_by_id.get(conn.get("to"))
        if not f or not t:
            return None
        p1 = connection_endpoint(f, conn.get("from_port"), conn.get("from_port_side"))
        p2 = connection_endpoint(t, conn.get("to_port"), conn.get("to_port_side"))
        dir1 = connection_direction(f, conn.get("from_port"), conn.get("from_port_side"))
        dir2 = connection_direction(t, conn.get("to_port"), conn.get("to_port_side"))
        waypoints = [(wp["x"], wp["y"]) for wp in (conn.get("waypoints") or [])
                     if isinstance(wp, dict) and "x" in wp and "y" in wp]
        points = [p1] + waypoints + [p2]
        return build_connector_path_segments(points, dir1, dir2)

    def draw_canvas_path(segments, color_hex, width_pt):
        if not segments:
            return
        first_point = segments[0][1]
        path = c.beginPath()
        path.moveTo(*to_page(*first_point))
        for seg in segments:
            if seg[0] == "line":
                _, _p0, p1 = seg
                path.lineTo(*to_page(*p1))
            else:
                _, _p0, cp_a, cp_b, p1 = seg
                path.curveTo(*to_page(*cp_a), *to_page(*cp_b), *to_page(*p1))
        c.setStrokeColor(HexColor(color_hex))
        c.setLineWidth(width_pt)
        c.drawPath(path, stroke=1, fill=0)

    drawn_sleeve_cables = set()
    for conn in connections:
        segments = conn_canvas_path(conn)
        if not segments:
            continue

        cable_id = conn.get("cable_id")
        if cable_id and cable_id not in drawn_sleeve_cables:
            drawn_sleeve_cables.add(cable_id)
            cable = get_cable(cfg, cable_id)
            sleeve_color = safe_hex_color(cable.get("color") if cable else None, "#5c6b7f")
            # Dickste Ader im Buendel bestimmt die Mantelstaerke.
            max_thickness = 4.0
            for member in cables_by_id.get(cable_id, []):
                try:
                    max_thickness = max(max_thickness, float(member.get("thickness") or 4))
                except (TypeError, ValueError):
                    pass
            sleeve_width = max(1.0, min(max_thickness, 14)) * scale * 0.85 + 4.5 * scale
            draw_canvas_path(segments, sleeve_color, max(sleeve_width, 2.0))

        color = safe_hex_color(conn.get("color"), "#3ad6ff")
        thickness = conn.get("thickness")
        try:
            thickness = float(thickness)
        except (TypeError, ValueError):
            thickness = 4.0
        thickness = max(0.75, min(thickness, 14)) * scale * 0.85
        thickness = max(thickness, 0.6)
        draw_canvas_path(segments, color, thickness)

        label = (conn.get("label") or "").strip()
        if label:
            canvas_points = [seg[1] for seg in segments] + [segments[-1][-1]]
            label_at = conn.get("label_at")
            if isinstance(label_at, dict) and "x" in label_at and "y" in label_at:
                label_point = (label_at["x"], label_at["y"])
            else:
                mid_i = (len(canvas_points) - 1) // 2
                a = canvas_points[mid_i]
                b = canvas_points[min(mid_i + 1, len(canvas_points) - 1)]
                nx, ny = _path_midpoint_normal(a, b)
                label_point = ((a[0] + b[0]) / 2 + nx * 8, (a[1] + b[1]) / 2 + ny * 8)
            lx, ly = to_page(*label_point)
            c.setFont("Helvetica", 7.5)
            c.setFillColor(HexColor(theme["text_dim"]))
            c.drawCentredString(lx, ly, label)

    # Kabel-Buendel-Namen mittig auf dem Kabelmantel anzeigen.
    for cable_id, members in cables_by_id.items():
        cable = get_cable(cfg, cable_id)
        cable_name = (cable.get("name") if cable else "") or ""
        if not cable_name:
            continue
        segments = conn_canvas_path(members[0])
        if not segments:
            continue
        canvas_points = [seg[1] for seg in segments] + [segments[-1][-1]]
        mid_i = (len(canvas_points) - 1) // 2
        a = canvas_points[mid_i]
        b = canvas_points[min(mid_i + 1, len(canvas_points) - 1)]
        nx, ny = _path_midpoint_normal(a, b)
        mid = ((a[0] + b[0]) / 2 + nx * 18, (a[1] + b[1]) / 2 + ny * 18)
        lx, ly = to_page(*mid)
        c.setFont("Helvetica-Bold", 7.5)
        c.setFillColor(HexColor(theme["text"]))
        c.drawCentredString(lx, ly - 9, "Kabel: " + cable_name)

    # --- Elemente zeichnen ---
    for el in elements:
        x0, y0 = el.get("x", 0) or 0, el.get("y", 0) or 0
        x1, y1 = x0 + ELEMENT_W, y0 + ELEMENT_H
        # Canvas-Koordinaten wachsen nach unten (y0 = oben, y1 = unten);
        # to_page() spiegelt nach PDF-Koordinaten (y waechst nach oben).
        ptl_x, ptl_y = to_page(x0, y0)  # obere linke Ecke der Box
        pbr_x, pbr_y = to_page(x1, y1)  # untere rechte Ecke der Box
        rx, ry = ptl_x, pbr_y            # reportlab-Rect-Ursprung = unten links
        rw, rh = pbr_x - ptl_x, ptl_y - pbr_y

        c.setFillColor(HexColor(theme["el_fill"]))
        c.setStrokeColor(HexColor(theme["el_border"]))
        c.setLineWidth(max(0.6, 1.1 * scale))
        c.roundRect(rx, ry, rw, rh, 3 * scale, stroke=1, fill=1)

        name = (el.get("name") or "(ohne Namen)").strip()
        type_label = element_label(el.get("type"))
        location = (el.get("location") or "").strip()

        font_size = max(6.5, min(9.5, 9.5 * scale + 3))
        c.setFillColor(HexColor(theme["text"]))
        c.setFont("Helvetica-Bold", font_size)
        text_x = rx + 4 * scale
        text_y = ry + rh - font_size - 3 * scale
        c.drawString(text_x, max(text_y, ry + rh - font_size - 2), truncate_to_width(
            c, name, "Helvetica-Bold", font_size, rw - 8 * scale))

        c.setFont("Helvetica", max(5.5, font_size - 2))
        c.setFillColor(HexColor(theme["text_dim"]))
        sub = type_label + (" - " + location if location else "")
        c.drawString(text_x, max(ry + 3, text_y - (font_size - 1)), truncate_to_width(
            c, sub, "Helvetica", max(5.5, font_size - 2), rw - 8 * scale))

        # Ports/Pins als kleine, nummerierte Punkte am Rand des Elements.
        port_count = get_port_count(el)
        if port_count > 0:
            if el.get("type") in INDIVIDUAL_PIN_TYPES:
                # Platine/Raspberry Pi: jeder Pin einzeln (eigene Seite je Index).
                for i in range(port_count):
                    ppx, ppy = port_point(el, i, "a")
                    dx, dy = to_page(ppx, ppy)
                    r = max(1.6, 2.4 * scale)
                    c.setFillColor(HexColor(theme["port_fill"]))
                    c.setStrokeColor(HexColor(theme["el_border"]))
                    c.setLineWidth(0.5)
                    c.circle(dx, dy, r, stroke=1, fill=1)
            else:
                sides = {"a"}
                if el.get("type") in DUAL_SIDE_TYPES:
                    sides.add("b")
                for side_key in sides:
                    for i in range(port_count):
                        ppx, ppy = port_point(el, i, side_key)
                        dx, dy = to_page(ppx, ppy)
                        r = max(1.6, 2.4 * scale)
                        c.setFillColor(HexColor(theme["port_fill"]))
                        c.setStrokeColor(HexColor(theme["el_border"]))
                        c.setLineWidth(0.5)
                        c.circle(dx, dy, r, stroke=1, fill=1)

    c.showPage()
    c.save()
    return buf.getvalue()


def truncate_to_width(c, text, font_name, font_size, max_width):
    if max_width <= 0:
        return ""
    if c.stringWidth(text, font_name, font_size) <= max_width:
        return text
    ellipsis = "…"
    while text and c.stringWidth(text + ellipsis, font_name, font_size) > max_width:
        text = text[:-1]
    return (text + ellipsis) if text else ""


@app.route("/api/export/pdf", methods=["POST"])
def api_export_pdf():
    if not REPORTLAB_AVAILABLE:
        return jsonify({
            "status": "error",
            "message": "PDF-Export nicht verfuegbar: Das Python-Paket "
                       "'reportlab' ist auf diesem Server nicht installiert."
        }), 500

    payload = request.get_json(force=True, silent=True) or {}
    cfg = payload.get("config")
    if not isinstance(cfg, dict):
        cfg = load_config()
    theme = payload.get("theme")
    if theme not in PDF_THEMES:
        theme = "dark"

    pdf_bytes = build_pdf(cfg, theme)
    mem = io.BytesIO(pdf_bytes)
    mem.seek(0)
    filename = "Verkabelungsplan_" + theme + "_" + datetime.now().strftime("%Y-%m-%d_%H%M") + ".pdf"
    return send_file(mem, mimetype="application/pdf",
                      as_attachment=True, download_name=filename)


# --------------------------------------------------------------------------
# MQTT: Nachricht ueber eine Element-Schaltflaeche versenden
# --------------------------------------------------------------------------
# Ein Link mit Schema "mqtt://" an einem Element sendet beim Klick (statt
# eine Webseite zu oeffnen) eine MQTT-Nachricht. Der Versand laeuft ueber
# den Server (nicht den Browser), da Browser aus Sicherheitsgruenden keine
# rohen TCP-Verbindungen zu einem MQTT-Broker aufbauen koennen.

@app.route("/api/mqtt/publish", methods=["POST"])
def api_mqtt_publish():
    if not MQTT_AVAILABLE:
        return jsonify({
            "status": "error",
            "message": "MQTT-Versand nicht verfuegbar: Das Python-Paket "
                       "'paho-mqtt' ist auf diesem Server nicht installiert."
        }), 500

    payload = request.get_json(force=True, silent=True) or {}
    host = (payload.get("host") or "").strip()
    topic = (payload.get("topic") or "").strip()
    message = payload.get("payload")
    message = "" if message is None else str(message)
    try:
        port = int(payload.get("port") or 1883)
    except (TypeError, ValueError):
        port = 1883
    username = (payload.get("username") or "").strip() or None
    password = payload.get("password") or None
    qos = payload.get("qos")
    try:
        qos = int(qos) if qos is not None else 0
        qos = qos if qos in (0, 1, 2) else 0
    except (TypeError, ValueError):
        qos = 0

    if not host or not topic:
        return jsonify({"status": "error", "message": "Broker-Host und Topic sind erforderlich."}), 400

    try:
        client = mqtt_client.Client()
        if username:
            client.username_pw_set(username, password)
        client.connect(host, port, keepalive=5)
        client.loop_start()
        info = client.publish(topic, payload=message, qos=qos)
        info.wait_for_publish(timeout=5)
        client.loop_stop()
        client.disconnect()
        if not info.is_published():
            raise RuntimeError("Nachricht konnte nicht zugestellt werden (kein PUBACK erhalten).")
    except Exception as exc:  # noqa: BLE001
        return jsonify({
            "status": "error",
            "message": f"Verbindung zu {host}:{port} fehlgeschlagen: {exc}"
        }), 502

    return jsonify({"status": "ok", "topic": topic})


# --------------------------------------------------------------------------
# Netzwerk-Helfer
# --------------------------------------------------------------------------

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def open_browser_delayed(url, delay=1.0):
    threading.Timer(delay, lambda: webbrowser.open(url)).start()


# --------------------------------------------------------------------------
# Start
# --------------------------------------------------------------------------

def main():
    cfg = load_config()
    host = cfg.get("server", {}).get("host", "0.0.0.0")
    port = int(cfg.get("server", {}).get("port", 8080))
    local_ip = get_local_ip()

    print("=" * 64)
    print(" VERKABELUNGSPLAN-SERVER")
    print("=" * 64)
    print(f" Lokal:          http://127.0.0.1:{port}")
    print(f" Im Netzwerk:    http://{local_ip}:{port}")
    print(f" Konfiguration:  {CONFIG_PATH}")
    if not REPORTLAB_AVAILABLE:
        print(" [HINWEIS] Paket 'reportlab' fehlt -> PDF-Export ist deaktiviert.")
    if not MQTT_AVAILABLE:
        print(" [HINWEIS] Paket 'paho-mqtt' fehlt -> MQTT-Schaltflaechen sind deaktiviert.")
    print(" Zum Beenden dieses Fenster schliessen oder STRG+C druecken.")
    print("=" * 64)

    open_browser_delayed(f"http://127.0.0.1:{port}")

    app.run(host=host, port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
