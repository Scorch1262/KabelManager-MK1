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
    "connections": []
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
# sowohl die aktuellen (v3.0.0) als auch die frueheren (Netzwerkplan-)
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
    "relay": "Relay",
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

# Elementtypen mit Ports + deren Standard-Portanzahl (muss zu DEFAULT_PORTS
# in static/app.js passen).
DEFAULT_PORTS_PY = {
    "controller": 8,
    "terminal_block": 12,
    "router": 4,
    "relay": 4,
    # Legacy:
    "switch": 8,
    "patchpanel": 24,
}
DUAL_SIDE_TYPES = {"terminal_block", "patchpanel"}
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


def port_label(el, port_index):
    if port_index is None:
        return ""
    label = "Port " + str(int(port_index) + 1)
    name = get_port_name(el, int(port_index))
    if name:
        label += " (" + name + ")"
    return label


def element_center(el):
    x = el.get("x", 0) or 0
    y = el.get("y", 0) or 0
    return x + ELEMENT_W / 2.0, y + ELEMENT_H / 2.0


def port_point(el, port_index, side_key):
    """Approximiert die Andockposition eines Ports fuer den Export, in
    Anlehnung an die Portleisten-Anordnung im Frontend (computePortRelOffsets
    / buildPortsBar in static/app.js). Muss nicht pixelgenau sein, nur
    optisch stimmig fuer PDF/Netzliste."""
    n = get_port_count(el)
    if n <= 0 or port_index is None or not (0 <= port_index < n):
        return element_center(el)

    x = el.get("x", 0) or 0
    y = el.get("y", 0) or 0
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


def safe_hex_color(value, fallback):
    if isinstance(value, str) and re.match(r"^#[0-9a-fA-F]{6}$", value):
        return value
    return fallback


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
        "Farbe", "Staerke", "Bezeichnung",
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
        writer.writerow([
            i,
            f.get("name", "") or "", element_label(f.get("type")), f.get("location", "") or "",
            port_label(f, from_port) if from_port is not None else "",
            t.get("name", "") or "", element_label(t.get("type")), t.get("location", "") or "",
            port_label(t, to_port) if to_port is not None else "",
            conn.get("color", "") or "",
            conn.get("thickness", "") if conn.get("thickness") is not None else "",
            conn.get("label", "") or "",
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

    # Bounding Box aller Elemente (inkl. Wegpunkte, damit Leitungen nicht
    # abgeschnitten werden) ermitteln, um den Plan passend auf die Seite
    # (Querformat) zu skalieren.
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

    bbox_x0, bbox_x1 = min(xs), max(xs)
    bbox_y0, bbox_y1 = min(ys), max(ys)
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
    c.setLineJoin(1)
    c.setLineCap(1)
    for conn in connections:
        f = el_by_id.get(conn.get("from"))
        t = el_by_id.get(conn.get("to"))
        if not f or not t:
            continue
        p1 = connection_endpoint(f, conn.get("from_port"), conn.get("from_port_side"))
        p2 = connection_endpoint(t, conn.get("to_port"), conn.get("to_port_side"))
        waypoints = [wp for wp in (conn.get("waypoints") or [])
                     if isinstance(wp, dict) and "x" in wp and "y" in wp]
        points = [p1] + [(wp["x"], wp["y"]) for wp in waypoints] + [p2]
        page_points = [to_page(px, py) for px, py in points]

        color = safe_hex_color(conn.get("color"), "#3ad6ff")
        thickness = conn.get("thickness")
        try:
            thickness = float(thickness)
        except (TypeError, ValueError):
            thickness = 4.0
        thickness = max(0.75, min(thickness, 14)) * scale * 0.85
        thickness = max(thickness, 0.6)

        c.setStrokeColor(HexColor(color))
        c.setLineWidth(thickness)
        path = c.beginPath()
        path.moveTo(*page_points[0])
        for pt in page_points[1:]:
            path.lineTo(*pt)
        c.drawPath(path, stroke=1, fill=0)

        label = (conn.get("label") or "").strip()
        if label:
            mid_i = len(page_points) // 2
            mx, my = page_points[max(0, mid_i - 1)]
            mx2, my2 = page_points[min(len(page_points) - 1, mid_i)]
            lx, ly = (mx + mx2) / 2, (my + my2) / 2 + 6
            c.setFont("Helvetica", 7.5)
            c.setFillColor(HexColor(theme["text_dim"]))
            c.drawCentredString(lx, ly, label)

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

        # Ports als kleine, nummerierte Punkte am Rand des Elements.
        port_count = get_port_count(el)
        if port_count > 0:
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
    print(" Zum Beenden dieses Fenster schliessen oder STRG+C druecken.")
    print("=" * 64)

    open_browser_delayed(f"http://127.0.0.1:{port}")

    app.run(host=host, port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
