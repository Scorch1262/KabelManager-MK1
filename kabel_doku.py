#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kabel Doku Uebersicht
=====================
Werkzeug zur Planung / Dokumentation von Verkabelungen (Schematic-Editor).
Version: siehe APP_VERSION unten.

Gespeicherte Dateien (liegen im selben Verzeichnis wie die exe / dieses Skript):
    config.json  - allgemeine Programmeinstellungen
    colors.json  - Standard-Kabelfarben je Verkabelungs-Standard (haendisch anpassbar)
    netz.json    - das eigentliche Verkabelungsnetz (Elemente + Kabel)

Start:
    python kabel_doku.py

Build zu exe:
    pyinstaller --noconfirm --onefile --windowed --name KabelDoku kabel_doku.py
"""

import json
import os
import sys
import math
import uuid
import csv
import subprocess
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox, colorchooser, filedialog, simpledialog

APP_VERSION = "2.0.0"
APP_TITLE = f"Kabel Doku Uebersicht v{APP_VERSION}"

# ---------------------------------------------------------------------------
# Pfade (immer neben der exe / dem Skript)
# ---------------------------------------------------------------------------

def base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = base_dir()
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
COLORS_PATH = os.path.join(BASE_DIR, "colors.json")

DEFAULT_CONFIG = {
    "fenster_breite": 1500,
    "fenster_hoehe": 950,
    "raster_groesse": 20,
    "raster_anzeigen": True,
    "am_raster_einrasten": True,
    "letzter_modus": "bearbeiten",
    "letzte_netzdatei": "netz.json",
    "farbdatei": "colors.json",
    "standard_zoom": 1.0,
    "port_abstand_px": 26,
    "element_mindestbreite": 140,
}

DEFAULT_COLORS = {
    "standards": {
        "UART": [
            {"signal": "TX", "color": "#E63946"},
            {"signal": "RX", "color": "#1D8FE1"},
            {"signal": "GND", "color": "#2B2B2B"},
        ],
        "I2C": [
            {"signal": "SDA", "color": "#2E9E4E"},
            {"signal": "SCL", "color": "#F2C500"},
            {"signal": "VCC", "color": "#E63946"},
            {"signal": "GND", "color": "#2B2B2B"},
        ],
        "LIN": [
            {"signal": "LIN", "color": "#8B5A2B"},
            {"signal": "VCC", "color": "#E63946"},
            {"signal": "GND", "color": "#2B2B2B"},
        ],
        "SENT": [
            {"signal": "SENT", "color": "#F28C28"},
            {"signal": "VCC", "color": "#E63946"},
            {"signal": "GND", "color": "#2B2B2B"},
        ],
        "Ethernet": [
            {"signal": "TX+", "color": "#FFFFFF"},
            {"signal": "TX-", "color": "#F2C500"},
            {"signal": "RX+", "color": "#2E9E4E"},
            {"signal": "RX-", "color": "#1D8FE1"},
        ],
        "Analog Video": [
            {"signal": "Video", "color": "#F2C500"},
            {"signal": "GND", "color": "#2B2B2B"},
        ],
        "DJI AirUnit": [
            {"signal": "Video", "color": "#F2C500"},
            {"signal": "GND", "color": "#2B2B2B"},
            {"signal": "VCC", "color": "#E63946"},
            {"signal": "UART_TX", "color": "#2E9E4E"},
            {"signal": "UART_RX", "color": "#1D8FE1"},
        ],
        "SPI": [
            {"signal": "MISO", "color": "#17BEBB"},
            {"signal": "MOSI", "color": "#C13FBF"},
            {"signal": "SCK", "color": "#F2C500"},
            {"signal": "CS", "color": "#FFFFFF"},
            {"signal": "GND", "color": "#2B2B2B"},
        ],
    }
}

def load_json(path, default):
    if not os.path.exists(path):
        save_json(path, default)
        return json.loads(json.dumps(default))
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return json.loads(json.dumps(default))

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ---------------------------------------------------------------------------
# Farb-Theme (angelehnt an Lattice-Software: dunkel, klare Akzentfarben)
# ---------------------------------------------------------------------------

THEME = {
    "bg": "#1b1c22",
    "bg_canvas": "#161014".replace("14", "1a"),  # #16101a-ish fallback safety
    "panel": "#24252c",
    "panel_light": "#2e2f38",
    "border": "#3a3b45",
    "accent": "#4fc3f7",
    "accent2": "#8a6bff",
    "text": "#e6e6ea",
    "text_dim": "#9a9aa5",
    "grid": "#2a2b33",
    "element_fill": "#2a2b33",
    "element_border": "#4fc3f7",
    "element_border_sel": "#ffce54",
    "port": "#8a6bff",
    "port_text": "#c9c9d4",
    "danger": "#e6586b",
    "ok": "#4fd18b",
    "marquee": "#4fc3f7",
}
THEME["bg_canvas"] = "#15161c"

def new_id():
    return uuid.uuid4().hex[:10]

# ---------------------------------------------------------------------------
# Geometrie-Hilfsfunktionen fuer Elemente / Ports
# ---------------------------------------------------------------------------

def new_element(name="Neues Element", typ="Sonstiges", ort=""):
    return {
        "id": new_id(),
        "name": name,
        "typ": typ,
        "ort": ort,
        "x": 200.0,
        "y": 200.0,
        "rotation": 0,       # 0/90/180/270
        "mirrored": False,
        "ist_patchfeld": False,
        "ports": [],         # [{id,name}]
        "buttons": [],       # [{label, art(url/rdp), ziel}]
    }

def new_port(name):
    return {"id": new_id(), "name": name}

def new_button(label="Oeffnen", art="url", ziel="https://"):
    return {"label": label, "art": art, "ziel": ziel}

def new_cable(von_element, von_port, bis_element, bis_port, standard=None, signale=None, label=""):
    if signale is None:
        signale = [{"name": "Signal", "color": "#4fc3f7"}]
    return {
        "id": new_id(),
        "standard": standard,
        "von_element": von_element,
        "von_port": von_port,
        "bis_element": bis_element,
        "bis_port": bis_port,
        "signale": signale,      # [{name, color}]  Reihenfolge = Reihenfolge im Bus
        "expanded": False,
        "wegpunkte": [],          # [[x,y], ...]
        "label": label,
    }

def element_size(el, cfg):
    n = max(1, len(el["ports"]))
    w = max(cfg.get("element_mindestbreite", 140), 140)
    h = 34 + n * cfg.get("port_abstand_px", 26)
    return w, h

def _rotate_point(px, py, cx, cy, angle_deg):
    if angle_deg == 0:
        return px, py
    rad = math.radians(angle_deg)
    dx, dy = px - cx, py - cy
    nx = dx * math.cos(rad) - dy * math.sin(rad)
    ny = dx * math.sin(rad) + dy * math.cos(rad)
    return cx + nx, cy + ny

def element_rect(el, cfg):
    """Liefert (x0,y0,x1,y1) der ungedrehten Box um das Zentrum el.x/el.y."""
    w, h = element_size(el, cfg)
    cx, cy = el["x"], el["y"]
    return cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2

def element_corners(el, cfg):
    """4 Eckpunkte nach Rotation (Weltkoordinaten), fuer Zeichnen als Polygon."""
    x0, y0, x1, y1 = element_rect(el, cfg)
    cx, cy = el["x"], el["y"]
    pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    rot = el.get("rotation", 0)
    return [_rotate_point(px, py, cx, cy, rot) for px, py in pts]

def element_ports_positions(el, cfg):
    """
    Liefert Liste von Eintraegen fuer JEDEN sichtbaren Port-Marker:
        {"port_id", "name", "seite" ("primaer"/"rueck"), "x","y", "label_x","label_y","label_anchor"}
    Normale Elemente: Ports auf einer Seite (rechte Kante vor Rotation).
    Patchfeld-Elemente: Ports auf ZWEI gegenueberliegenden Seiten (links+rechts vor Rotation),
    mit paralleler Nummerierung/Namensgebung (gleicher Port erscheint auf beiden Seiten).
    """
    w, h = element_size(el, cfg)
    cx, cy = el["x"], el["y"]
    x0, y0, x1, y1 = element_rect(el, cfg)
    n = len(el["ports"])
    rot = el.get("rotation", 0)
    mirrored = el.get("mirrored", False)
    is_patch = el.get("ist_patchfeld", False)

    order = list(range(n))
    if mirrored:
        order = list(reversed(order))

    entries = []
    top_margin = 30
    if n > 0:
        step = (h - top_margin - 10) / n
    else:
        step = 0

    for idx, port_index in enumerate(order):
        port = el["ports"][port_index]
        py = y0 + top_margin + step * idx + step / 2

        # primaere Seite: rechte Kante (vor Rotation)
        px_r = x1
        wx, wy = _rotate_point(px_r, py, cx, cy, rot)
        entries.append({
            "port_id": port["id"], "name": port["name"], "seite": "primaer",
            "x": wx, "y": wy, "index": port_index,
        })
        if is_patch:
            px_l = x0
            wx2, wy2 = _rotate_point(px_l, py, cx, cy, rot)
            entries.append({
                "port_id": port["id"], "name": port["name"], "seite": "rueck",
                "x": wx2, "y": wy2, "index": port_index,
            })
    return entries

def find_port_entry(el, cfg, port_id, seite="primaer"):
    for e in element_ports_positions(el, cfg):
        if e["port_id"] == port_id and e["seite"] == seite:
            return e
    for e in element_ports_positions(el, cfg):
        if e["port_id"] == port_id:
            return e
    return None

# ---------------------------------------------------------------------------
# Dialog: Element anlegen / bearbeiten
# (bewusst BREIT gehalten, damit alle Felder inkl. Schaltflaechen passen)
# ---------------------------------------------------------------------------

class ElementDialog(tk.Toplevel):
    def __init__(self, master, element=None, orte_liste=None):
        super().__init__(master)
        self.title("Element bearbeiten" if element else "Neues Element")
        self.configure(bg=THEME["bg"])
        self.geometry("980x560")
        self.minsize(940, 520)
        self.result = None
        self.transient(master)
        self.grab_set()

        self.el = element if element else new_element()
        self.el = json.loads(json.dumps(self.el))  # Kopie
        orte_liste = orte_liste or []

        pad = {"padx": 8, "pady": 6}

        top = tk.Frame(self, bg=THEME["bg"])
        top.pack(fill="x", **pad)

        tk.Label(top, text="Name:", bg=THEME["bg"], fg=THEME["text"]).grid(row=0, column=0, sticky="w")
        self.var_name = tk.StringVar(value=self.el["name"])
        tk.Entry(top, textvariable=self.var_name, width=30).grid(row=0, column=1, sticky="w", padx=4)

        tk.Label(top, text="Typ:", bg=THEME["bg"], fg=THEME["text"]).grid(row=0, column=2, sticky="w")
        self.var_typ = tk.StringVar(value=self.el.get("typ", ""))
        typen = ["Stromversorgung", "Antrieb", "Motor", "Schaltkasten", "Platine",
                 "Sensor", "Steuergeraet", "Patchfeld", "Sonstiges"]
        ttk.Combobox(top, textvariable=self.var_typ, values=typen, width=20).grid(row=0, column=3, sticky="w", padx=4)

        tk.Label(top, text="Ort:", bg=THEME["bg"], fg=THEME["text"]).grid(row=0, column=4, sticky="w")
        self.var_ort = tk.StringVar(value=self.el.get("ort", ""))
        ttk.Combobox(top, textvariable=self.var_ort, values=orte_liste, width=20).grid(row=0, column=5, sticky="w", padx=4)

        self.var_patch = tk.BooleanVar(value=self.el.get("ist_patchfeld", False))
        tk.Checkbutton(top, text="Patchfeld (Ports auf 2 Seiten, parallele Nummerierung)",
                        variable=self.var_patch, bg=THEME["bg"], fg=THEME["text"],
                        selectcolor=THEME["panel"], activebackground=THEME["bg"]).grid(row=1, column=0, columnspan=4, sticky="w", pady=4)

        # --- Zwei Spalten: Ports  |  Schaltflaechen ---
        cols = tk.Frame(self, bg=THEME["bg"])
        cols.pack(fill="both", expand=True, **pad)
        cols.columnconfigure(0, weight=1)
        cols.columnconfigure(1, weight=1)

        # Ports
        pframe = tk.LabelFrame(cols, text="Anschlusspunkte / Ports", bg=THEME["bg"], fg=THEME["text"])
        pframe.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self.ports_list = tk.Listbox(pframe, height=12, bg=THEME["panel"], fg=THEME["text"],
                                      selectbackground=THEME["accent"], activestyle="none")
        self.ports_list.pack(fill="both", expand=True, padx=6, pady=6)
        for p in self.el["ports"]:
            self.ports_list.insert("end", p["name"])

        prow = tk.Frame(pframe, bg=THEME["bg"])
        prow.pack(fill="x", padx=6, pady=(0, 6))
        self.var_new_port = tk.StringVar()
        tk.Entry(prow, textvariable=self.var_new_port, width=16).pack(side="left")
        tk.Button(prow, text="+ Hinzufuegen", command=self.add_port).pack(side="left", padx=4)
        tk.Button(prow, text="Umbenennen", command=self.rename_port).pack(side="left", padx=4)
        tk.Button(prow, text="Entfernen", command=self.remove_port).pack(side="left", padx=4)

        # Schaltflaechen
        bframe = tk.LabelFrame(cols, text="Schaltflaechen (oeffnen Links / RDP)", bg=THEME["bg"], fg=THEME["text"])
        bframe.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        self.buttons_list = tk.Listbox(bframe, height=12, bg=THEME["panel"], fg=THEME["text"],
                                        selectbackground=THEME["accent"], activestyle="none")
        self.buttons_list.pack(fill="both", expand=True, padx=6, pady=6)
        self.refresh_buttons_list()

        brow1 = tk.Frame(bframe, bg=THEME["bg"])
        brow1.pack(fill="x", padx=6, pady=2)
        tk.Label(brow1, text="Label:", bg=THEME["bg"], fg=THEME["text"]).pack(side="left")
        self.var_btn_label = tk.StringVar(value="Oeffnen")
        tk.Entry(brow1, textvariable=self.var_btn_label, width=14).pack(side="left", padx=4)
        tk.Label(brow1, text="Art:", bg=THEME["bg"], fg=THEME["text"]).pack(side="left")
        self.var_btn_art = tk.StringVar(value="url")
        ttk.Combobox(brow1, textvariable=self.var_btn_art, values=["url", "rdp"], width=6, state="readonly").pack(side="left", padx=4)

        brow2 = tk.Frame(bframe, bg=THEME["bg"])
        brow2.pack(fill="x", padx=6, pady=2)
        tk.Label(brow2, text="Ziel (URL bzw. Host/IP fuer RDP):", bg=THEME["bg"], fg=THEME["text"]).pack(side="left")
        self.var_btn_ziel = tk.StringVar(value="https://")
        tk.Entry(brow2, textvariable=self.var_btn_ziel, width=40).pack(side="left", padx=4, fill="x", expand=True)

        brow3 = tk.Frame(bframe, bg=THEME["bg"])
        brow3.pack(fill="x", padx=6, pady=(2, 6))
        tk.Button(brow3, text="+ Hinzufuegen", command=self.add_button).pack(side="left", padx=2)
        tk.Button(brow3, text="Entfernen", command=self.remove_button).pack(side="left", padx=2)

        # Footer
        footer = tk.Frame(self, bg=THEME["bg"])
        footer.pack(fill="x", **pad)
        tk.Button(footer, text="Speichern", bg=THEME["accent"], command=self.on_save).pack(side="right", padx=4)
        tk.Button(footer, text="Abbrechen", command=self.destroy).pack(side="right", padx=4)
        if element:
            tk.Button(footer, text="Element loeschen", bg=THEME["danger"], fg="white",
                      command=self.on_delete).pack(side="left", padx=4)

    def refresh_buttons_list(self):
        self.buttons_list.delete(0, "end")
        for b in self.el["buttons"]:
            self.buttons_list.insert("end", f"[{b['art']}] {b['label']} -> {b['ziel']}")

    def add_port(self):
        name = self.var_new_port.get().strip()
        if not name:
            name = f"P{len(self.el['ports']) + 1}"
        self.el["ports"].append(new_port(name))
        self.ports_list.insert("end", name)
        self.var_new_port.set("")

    def rename_port(self):
        sel = self.ports_list.curselection()
        if not sel:
            return
        i = sel[0]
        neu = simpledialog.askstring("Port umbenennen", "Neuer Name:",
                                      initialvalue=self.el["ports"][i]["name"], parent=self)
        if neu:
            self.el["ports"][i]["name"] = neu
            self.ports_list.delete(i)
            self.ports_list.insert(i, neu)

    def remove_port(self):
        sel = self.ports_list.curselection()
        if not sel:
            return
        i = sel[0]
        del self.el["ports"][i]
        self.ports_list.delete(i)

    def add_button(self):
        label = self.var_btn_label.get().strip() or "Oeffnen"
        art = self.var_btn_art.get()
        ziel = self.var_btn_ziel.get().strip()
        if not ziel:
            messagebox.showwarning("Fehlt", "Bitte ein Ziel angeben.", parent=self)
            return
        self.el["buttons"].append(new_button(label, art, ziel))
        self.refresh_buttons_list()

    def remove_button(self):
        sel = self.buttons_list.curselection()
        if not sel:
            return
        del self.el["buttons"][sel[0]]
        self.refresh_buttons_list()

    def on_delete(self):
        if messagebox.askyesno("Loeschen", "Dieses Element wirklich loeschen?", parent=self):
            self.result = ("delete", self.el)
            self.destroy()

    def on_save(self):
        self.el["name"] = self.var_name.get().strip() or "Element"
        self.el["typ"] = self.var_typ.get().strip()
        self.el["ort"] = self.var_ort.get().strip()
        self.el["ist_patchfeld"] = self.var_patch.get()
        self.result = ("save", self.el)
        self.destroy()

# ---------------------------------------------------------------------------
# Dialog: Kabel anlegen / bearbeiten
# ---------------------------------------------------------------------------

class CableDialog(tk.Toplevel):
    def __init__(self, master, cable, colors_cfg, von_name, bis_name):
        super().__init__(master)
        self.title("Kabel bearbeiten")
        self.configure(bg=THEME["bg"])
        self.geometry("620x520")
        self.transient(master)
        self.grab_set()
        self.result = None
        self.colors_cfg = colors_cfg
        self.cable = json.loads(json.dumps(cable))

        pad = {"padx": 8, "pady": 6}
        tk.Label(self, text=f"Von: {von_name}   ->   Bis: {bis_name}",
                 bg=THEME["bg"], fg=THEME["text_dim"]).pack(anchor="w", **pad)

        row1 = tk.Frame(self, bg=THEME["bg"])
        row1.pack(fill="x", **pad)
        tk.Label(row1, text="Bezeichnung / Label:", bg=THEME["bg"], fg=THEME["text"]).pack(side="left")
        self.var_label = tk.StringVar(value=self.cable.get("label", ""))
        tk.Entry(row1, textvariable=self.var_label, width=30).pack(side="left", padx=6)

        row2 = tk.Frame(self, bg=THEME["bg"])
        row2.pack(fill="x", **pad)
        tk.Label(row2, text="Standard-Verkabelung:", bg=THEME["bg"], fg=THEME["text"]).pack(side="left")
        standards = ["(Frei / eigene Farbe)"] + sorted(colors_cfg.get("standards", {}).keys())
        self.var_standard = tk.StringVar(value=self.cable.get("standard") or "(Frei / eigene Farbe)")
        cb = ttk.Combobox(row2, textvariable=self.var_standard, values=standards, state="readonly", width=28)
        cb.pack(side="left", padx=6)
        cb.bind("<<ComboboxSelected>>", lambda e: self.apply_standard())

        self.frame_signale = tk.LabelFrame(self, text="Signale / Leitungen in diesem Kabel",
                                            bg=THEME["bg"], fg=THEME["text"])
        self.frame_signale.pack(fill="both", expand=True, **pad)
        self.signal_rows = []
        self.render_signals()

        row3 = tk.Frame(self, bg=THEME["bg"])
        row3.pack(fill="x", **pad)
        tk.Button(row3, text="+ Signal hinzufuegen (frei)", command=self.add_free_signal).pack(side="left")

        footer = tk.Frame(self, bg=THEME["bg"])
        footer.pack(fill="x", **pad)
        tk.Button(footer, text="Speichern", bg=THEME["accent"], command=self.on_save).pack(side="right", padx=4)
        tk.Button(footer, text="Abbrechen", command=self.destroy).pack(side="right", padx=4)
        tk.Button(footer, text="Kabel loeschen", bg=THEME["danger"], fg="white",
                  command=self.on_delete).pack(side="left", padx=4)

    def apply_standard(self):
        std = self.var_standard.get()
        if std == "(Frei / eigene Farbe)":
            self.cable["standard"] = None
        else:
            self.cable["standard"] = std
            defs = self.colors_cfg.get("standards", {}).get(std, [])
            self.cable["signale"] = [{"name": d["signal"], "color": d["color"]} for d in defs]
        self.render_signals()

    def render_signals(self):
        for w in self.frame_signale.winfo_children():
            w.destroy()
        self.signal_rows = []
        for idx, sig in enumerate(self.cable["signale"]):
            r = tk.Frame(self.frame_signale, bg=THEME["bg"])
            r.pack(fill="x", padx=6, pady=3)
            var_name = tk.StringVar(value=sig["name"])
            e = tk.Entry(r, textvariable=var_name, width=18)
            e.pack(side="left")
            swatch = tk.Label(r, text="    ", bg=sig["color"], relief="ridge", bd=1)
            swatch.pack(side="left", padx=6)
            tk.Button(r, text="Farbe...", command=lambda i=idx, sw=swatch: self.pick_color(i, sw)).pack(side="left")
            tk.Button(r, text="Entfernen", command=lambda i=idx: self.remove_signal(i)).pack(side="left", padx=6)
            self.signal_rows.append((var_name, sig))

    def pick_color(self, idx, swatch_widget):
        c = colorchooser.askcolor(color=self.cable["signale"][idx]["color"], parent=self)
        if c and c[1]:
            self.cable["signale"][idx]["color"] = c[1]
            swatch_widget.configure(bg=c[1])

    def remove_signal(self, idx):
        del self.cable["signale"][idx]
        self.render_signals()

    def add_free_signal(self):
        self.cable["signale"].append({"name": f"Signal{len(self.cable['signale']) + 1}", "color": "#4fc3f7"})
        self.render_signals()

    def on_delete(self):
        if messagebox.askyesno("Loeschen", "Dieses Kabel wirklich loeschen?", parent=self):
            self.result = ("delete", self.cable)
            self.destroy()

    def on_save(self):
        # Namen aus den Entry-Feldern uebernehmen
        for var_name, sig in self.signal_rows:
            sig["name"] = var_name.get().strip() or sig["name"]
        self.cable["label"] = self.var_label.get().strip()
        if not self.cable["signale"]:
            self.cable["signale"] = [{"name": "Signal", "color": "#4fc3f7"}]
        self.result = ("save", self.cable)
        self.destroy()

# ---------------------------------------------------------------------------
# Hauptanwendung
# ---------------------------------------------------------------------------

class KabelDokuApp:
    def __init__(self, root):
        self.root = root
        self.cfg = load_json(CONFIG_PATH, DEFAULT_CONFIG)
        self.colors_cfg = load_json(COLORS_PATH, DEFAULT_COLORS)

        self.root.title(APP_TITLE)
        self.root.geometry(f"{self.cfg.get('fenster_breite',1500)}x{self.cfg.get('fenster_hoehe',950)}")
        self.root.configure(bg=THEME["bg"])

        self.netz_path = os.path.join(BASE_DIR, self.cfg.get("letzte_netzdatei", "netz.json"))
        self.netz = load_json(self.netz_path, {"elemente": [], "kabel": []})
        self.netz.setdefault("elemente", [])
        self.netz.setdefault("kabel", [])

        self.mode = self.cfg.get("letzter_modus", "bearbeiten")
        self.zoom = self.cfg.get("standard_zoom", 1.0)
        self.offset_x = 0.0
        self.offset_y = 0.0

        self.selected_elements = set()
        self.selected_cables = set()
        self.expanded_cables = set(c["id"] for c in self.netz["kabel"] if c.get("expanded"))
        self.highlight_ort = None
        self.highlight_cable = None

        self._consumed = False
        self._drag_info = None   # dict describing current drag operation
        self._marquee_start = None
        self._marquee_item = None
        self._pending_cable_start = None  # (element_id, port_id, seite)
        self._temp_line = None

        self.build_ui()
        self.redraw()

    # ---------------- UI Aufbau ----------------

    def build_ui(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TCombobox", fieldbackground=THEME["panel"], background=THEME["panel"],
                         foreground=THEME["text"])

        self.toolbar = tk.Frame(self.root, bg=THEME["panel"], height=44)
        self.toolbar.pack(fill="x", side="top")

        self.btn_mode = tk.Button(self.toolbar, text="", command=self.toggle_mode,
                                   bg=THEME["accent"], fg="#101010", font=("Segoe UI", 10, "bold"),
                                   relief="flat", padx=12, pady=6)
        self.btn_mode.pack(side="left", padx=8, pady=6)

        self.edit_buttons = []

        def add_tool(text, cmd):
            b = tk.Button(self.toolbar, text=text, command=cmd, bg=THEME["panel_light"], fg=THEME["text"],
                          relief="flat", padx=10, pady=6)
            b.pack(side="left", padx=3, pady=6)
            self.edit_buttons.append(b)
            return b

        add_tool("+ Element", self.action_new_element)
        add_tool("Speichern", self.save_netz)
        add_tool("PDF Export", self.export_pdf)
        add_tool("Netzliste (CSV)", self.export_netzliste_csv)
        add_tool("Netzliste (XLSX)", self.export_netzliste_xlsx)
        add_tool("Raster an/aus", self.toggle_grid)
        add_tool("Farbdatei neu laden", self.reload_colors)

        tk.Label(self.toolbar, text="  Highlight Ort:", bg=THEME["panel"], fg=THEME["text_dim"]).pack(side="left", padx=(20, 4))
        self.var_highlight_ort = tk.StringVar(value="(kein)")
        self.combo_ort = ttk.Combobox(self.toolbar, textvariable=self.var_highlight_ort, width=18, state="readonly")
        self.combo_ort.pack(side="left")
        self.combo_ort.bind("<<ComboboxSelected>>", self.on_highlight_ort_change)

        tk.Button(self.toolbar, text="Zoom Reset", command=self.reset_view,
                  bg=THEME["panel_light"], fg=THEME["text"], relief="flat", padx=10, pady=6).pack(side="right", padx=8)

        # Canvas
        self.canvas = tk.Canvas(self.root, bg=THEME["bg_canvas"], highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.canvas.bind("<ButtonPress-1>", self.on_canvas_press)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas.bind("<Double-Button-1>", self.on_canvas_double)
        self.canvas.bind("<ButtonPress-3>", self.on_canvas_right)
        self.canvas.bind("<ButtonPress-2>", self.on_pan_start)
        self.canvas.bind("<B2-Motion>", self.on_pan_move)
        self.canvas.bind("<MouseWheel>", self.on_zoom)
        self.canvas.bind("<Button-4>", lambda e: self.on_zoom(e, delta=120))
        self.canvas.bind("<Button-5>", lambda e: self.on_zoom(e, delta=-120))
        self.root.bind("<Delete>", self.on_delete_key)
        self.root.bind("<Escape>", lambda e: self.cancel_pending())

        self.status = tk.Label(self.root, text="", bg=THEME["panel"], fg=THEME["text_dim"], anchor="w")
        self.status.pack(fill="x", side="bottom")

        self.update_mode_ui()
        self.refresh_ort_list()

    def refresh_ort_list(self):
        orte = sorted(set(e.get("ort", "") for e in self.netz["elemente"] if e.get("ort")))
        self.combo_ort["values"] = ["(kein)"] + orte

    # ---------------- Modus ----------------

    def toggle_mode(self):
        self.mode = "nutzung" if self.mode == "bearbeiten" else "bearbeiten"
        self.cfg["letzter_modus"] = self.mode
        save_json(CONFIG_PATH, self.cfg)
        self.update_mode_ui()
        self.redraw()

    def update_mode_ui(self):
        if self.mode == "bearbeiten":
            self.btn_mode.configure(text="Modus: BEARBEITEN  (klicken fuer Nutzung)")
            for b in self.edit_buttons:
                b.pack(side="left", padx=3, pady=6)
        else:
            self.btn_mode.configure(text="Modus: NUTZUNG  (klicken fuer Bearbeiten)")
            for b in self.edit_buttons:
                b.pack_forget()

    def toggle_grid(self):
        self.cfg["raster_anzeigen"] = not self.cfg.get("raster_anzeigen", True)
        self.redraw()

    def reload_colors(self):
        self.colors_cfg = load_json(COLORS_PATH, DEFAULT_COLORS)
        messagebox.showinfo("Farbdatei", "colors.json neu geladen.")

    def reset_view(self):
        self.zoom = 1.0
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.redraw()

    def on_highlight_ort_change(self, event=None):
        v = self.var_highlight_ort.get()
        self.highlight_ort = None if v == "(kein)" else v
        self.redraw()

    def cancel_pending(self):
        self._pending_cable_start = None
        self._drag_info = None
        if self._temp_line:
            self.canvas.delete(self._temp_line)
            self._temp_line = None
        self.redraw()

    # ---------------- Koordinaten-Transformation ----------------

    def w2s(self, x, y):
        return x * self.zoom + self.offset_x, y * self.zoom + self.offset_y

    def s2w(self, x, y):
        return (x - self.offset_x) / self.zoom, (y - self.offset_y) / self.zoom

    def find_element(self, eid):
        for e in self.netz["elemente"]:
            if e["id"] == eid:
                return e
        return None

    def find_cable(self, cid):
        for c in self.netz["kabel"]:
            if c["id"] == cid:
                return c
        return None

    def port_world_pos(self, element_id, port_id, seite="primaer"):
        el = self.find_element(element_id)
        if not el:
            return None
        entry = find_port_entry(el, self.cfg, port_id, seite)
        if not entry:
            return None
        return entry["x"], entry["y"]

    # ---------------- Zeichnen ----------------

    def redraw(self):
        c = self.canvas
        c.delete("all")
        w = c.winfo_width() or 1400
        h = c.winfo_height() or 800

        if self.cfg.get("raster_anzeigen", True):
            self.draw_grid(w, h)

        # Kabel zuerst (liegen hinter Elementen)
        for cable in self.netz["kabel"]:
            self.draw_cable(cable)

        # temporaere Ziehlinie beim Kabel-Anlegen
        if self._pending_cable_start:
            eid, pid, seite = self._pending_cable_start
            pos = self.port_world_pos(eid, pid, seite)
            if pos:
                sx, sy = self.w2s(*pos)
                self._temp_line = c.create_line(sx, sy, sx, sy, fill=THEME["accent"], width=3, dash=(4, 2), tags=("templine",))

        for el in self.netz["elemente"]:
            self.draw_element(el)

        self.update_status()

    def draw_grid(self, w, h):
        c = self.canvas
        g = max(4, int(self.cfg.get("raster_groesse", 20) * self.zoom))
        ox = self.offset_x % g
        oy = self.offset_y % g
        x = ox
        while x < w:
            c.create_line(x, 0, x, h, fill=THEME["grid"], tags=("grid",))
            x += g
        y = oy
        while y < h:
            c.create_line(0, y, w, y, fill=THEME["grid"], tags=("grid",))
            y += g

    def draw_element(self, el):
        c = self.canvas
        cfg = self.cfg
        corners = element_corners(el, cfg)
        pts = []
        for wx, wy in corners:
            sx, sy = self.w2s(wx, wy)
            pts.extend([sx, sy])

        selected = el["id"] in self.selected_elements
        dim = False
        if self.highlight_ort:
            dim = el.get("ort", "") != self.highlight_ort

        fill = THEME["element_fill"]
        border = THEME["element_border_sel"] if selected else THEME["element_border"]
        if dim:
            fill = THEME["panel"]
            border = THEME["border"]

        tag_body = f"el_body_{el['id']}"
        poly = c.create_polygon(*pts, fill=fill, outline=border, width=3 if selected else 2,
                                 tags=("element", tag_body, f"eid_{el['id']}"))

        # Titel (immer aufrecht, unabhaengig von Rotation, damit lesbar)
        cx, cy = self.w2s(el["x"], el["y"])
        title_color = THEME["text_dim"] if dim else THEME["text"]
        c.create_text(cx, cy - (element_size(el, cfg)[1] * self.zoom) / 2 - 12,
                       text=f"{el['name']}", fill=title_color, font=("Segoe UI", max(8, int(10 * self.zoom)), "bold"),
                       tags=("element_title", tag_body))
        sub = el.get("typ", "")
        if el.get("ort"):
            sub = f"{sub}  |  Ort: {el['ort']}" if sub else f"Ort: {el['ort']}"
        if sub:
            c.create_text(cx, cy - (element_size(el, cfg)[1] * self.zoom) / 2 - 12 + 13 * max(0.7, self.zoom),
                           text=sub, fill=THEME["text_dim"], font=("Segoe UI", max(7, int(8 * self.zoom))),
                           tags=("element_sub", tag_body))

        # Bindings auf Koerper
        c.tag_bind(tag_body, "<ButtonPress-1>", lambda e, eid=el["id"]: self.on_element_press(e, eid))
        c.tag_bind(tag_body, "<B1-Motion>", lambda e, eid=el["id"]: self.on_element_motion(e, eid))
        c.tag_bind(tag_body, "<ButtonRelease-1>", lambda e, eid=el["id"]: self.on_element_release(e, eid))
        c.tag_bind(tag_body, "<Double-Button-1>", lambda e, eid=el["id"]: self.on_element_double(e, eid))
        c.tag_bind(tag_body, "<ButtonPress-3>", lambda e, eid=el["id"]: self.show_element_context_menu(e, eid))

        # Ports
        for entry in element_ports_positions(el, cfg):
            sx, sy = self.w2s(entry["x"], entry["y"])
            r = max(4, 5 * self.zoom)
            port_tag = f"port_{el['id']}_{entry['port_id']}_{entry['seite']}"
            pc = THEME["port"] if not dim else THEME["border"]
            c.create_oval(sx - r, sy - r, sx + r, sy + r, fill=pc, outline="", tags=("port", port_tag))
            label_off = 12 * max(0.7, self.zoom)
            anchor = "w" if entry["seite"] == "primaer" else "e"
            lx = sx + label_off if entry["seite"] == "primaer" else sx - label_off
            c.create_text(lx, sy, text=f"{entry['index']+1}. {entry['name']}", fill=THEME["port_text"] if not dim else THEME["text_dim"],
                           anchor=anchor, font=("Segoe UI", max(7, int(8 * self.zoom))), tags=("port_label", port_tag))
            if self.mode == "bearbeiten":
                c.tag_bind(port_tag, "<ButtonPress-1>", lambda e, eid=el["id"], pid=entry["port_id"], s=entry["seite"]: self.on_port_click(e, eid, pid, s))

        # Schaltflaechen (im Nutzungsmodus UND im Bearbeitungsmodus sichtbar/klickbar, damit man sie testen kann)
        by = cy + (element_size(el, cfg)[1] * self.zoom) / 2 + 4
        bx = cx - (element_size(el, cfg)[0] * self.zoom) / 2
        for i, btn in enumerate(el.get("buttons", [])):
            bw = 70 * max(0.7, self.zoom)
            bx_i = bx + i * (bw + 4)
            btag = f"btn_{el['id']}_{i}"
            rect = c.create_rectangle(bx_i, by, bx_i + bw, by + 18 * max(0.7, self.zoom),
                                       fill=THEME["accent2"], outline="", tags=("elbtn", btag))
            c.create_text(bx_i + bw / 2, by + 9 * max(0.7, self.zoom), text=btn["label"][:12],
                           fill="#ffffff", font=("Segoe UI", max(6, int(7 * self.zoom))), tags=("elbtn_txt", btag))
            c.tag_bind(btag, "<ButtonPress-1>", lambda e, b=btn: self.open_button(b))

    def draw_cable(self, cable):
        c = self.canvas
        von = self.port_world_pos(cable["von_element"], cable["von_port"], "primaer") or \
              self.port_world_pos(cable["von_element"], cable["von_port"], "rueck")
        bis = self.port_world_pos(cable["bis_element"], cable["bis_port"], "primaer") or \
              self.port_world_pos(cable["bis_element"], cable["bis_port"], "rueck")
        if not von or not bis:
            return

        pts_world = [von] + [tuple(p) for p in cable.get("wegpunkte", [])] + [bis]
        pts_screen = []
        for wx, wy in pts_world:
            pts_screen.extend(self.w2s(wx, wy))

        selected = cable["id"] in self.selected_cables
        is_bus = cable.get("standard") and len(cable.get("signale", [])) > 1
        expanded = cable["id"] in self.expanded_cables

        tag_cable = f"cable_{cable['id']}"

        if is_bus and not expanded:
            color = cable["signale"][0]["color"] if cable["signale"] else THEME["accent"]
            width = 7 if selected else 5
            c.create_line(*pts_screen, fill=color, width=width, capstyle="round", joinstyle="round",
                           smooth=True, tags=("cable", tag_cable))
            if selected:
                c.create_line(*pts_screen, fill=THEME["element_border_sel"], width=width + 3, capstyle="round",
                               smooth=True, tags=("cable_glow", tag_cable))
                c.tag_lower("cable_glow", tag_cable)
        else:
            n = max(1, len(cable.get("signale", [])))
            spread = 3.5 * max(0.6, self.zoom)
            for idx, sig in enumerate(cable.get("signale", [{"name": "Signal", "color": "#4fc3f7"}])):
                offset = (idx - (n - 1) / 2) * spread
                shifted = self._offset_polyline(pts_screen, offset)
                width = 4 if selected else 3
                c.create_line(*shifted, fill=sig["color"], width=width, capstyle="round", joinstyle="round",
                               smooth=True, tags=("cable", tag_cable))

        # Label
        if cable.get("label") or is_bus:
            mid_idx = len(pts_world) // 2
            mx, my = self.w2s(*pts_world[mid_idx]) if len(pts_world) % 2 == 1 else (
                (pts_screen[2 * mid_idx - 2] + pts_screen[2 * mid_idx]) / 2,
                (pts_screen[2 * mid_idx - 1] + pts_screen[2 * mid_idx + 1]) / 2)
            txt = cable.get("label") or cable.get("standard") or ""
            if txt:
                c.create_text(mx, my - 10, text=txt, fill=THEME["text"], font=("Segoe UI", max(7, int(8 * self.zoom)), "bold"),
                               tags=("cable_label", tag_cable))

        # Wegpunkt-Handles (nur im Bearbeitungsmodus + wenn selektiert)
        if self.mode == "bearbeiten" and selected:
            for wi, (wx, wy) in enumerate(cable.get("wegpunkte", [])):
                sx, sy = self.w2s(wx, wy)
                r = 5
                htag = f"wp_{cable['id']}_{wi}"
                c.create_oval(sx - r, sy - r, sx + r, sy + r, fill=THEME["marquee"], outline="white",
                               tags=("waypoint", htag))
                c.tag_bind(htag, "<ButtonPress-1>", lambda e, cid=cable["id"], i=wi: self.on_waypoint_press(e, cid, i))
                c.tag_bind(htag, "<B1-Motion>", lambda e, cid=cable["id"], i=wi: self.on_waypoint_motion(e, cid, i))
                c.tag_bind(htag, "<ButtonRelease-1>", lambda e: self.redraw())
                c.tag_bind(htag, "<ButtonPress-3>", lambda e, cid=cable["id"], i=wi: self.remove_waypoint(cid, i))

        c.tag_bind(tag_cable, "<ButtonPress-1>", lambda e, cid=cable["id"]: self.on_cable_click(e, cid))
        c.tag_bind(tag_cable, "<Double-Button-1>", lambda e, cid=cable["id"]: self.on_cable_double(e, cid))
        c.tag_bind(tag_cable, "<ButtonPress-3>", lambda e, cid=cable["id"]: self.on_cable_right(e, cid))

    def _offset_polyline(self, pts_screen, offset):
        """Verschiebt eine Polylinie senkrecht zur jeweiligen Segmentrichtung um offset px."""
        if offset == 0 or len(pts_screen) < 4:
            return pts_screen
        pts = [(pts_screen[i], pts_screen[i + 1]) for i in range(0, len(pts_screen), 2)]
        out = []
        for i, (x, y) in enumerate(pts):
            if i == 0:
                dx, dy = pts[1][0] - x, pts[1][1] - y
            elif i == len(pts) - 1:
                dx, dy = x - pts[i - 1][0], y - pts[i - 1][1]
            else:
                dx = pts[i + 1][0] - pts[i - 1][0]
                dy = pts[i + 1][1] - pts[i - 1][1]
            length = math.hypot(dx, dy) or 1
            nx, ny = -dy / length, dx / length
            out.extend([x + nx * offset, y + ny * offset])
        return out

    def update_status(self):
        m = "BEARBEITEN" if self.mode == "bearbeiten" else "NUTZUNG"
        self.status.configure(text=f"  Modus: {m}   |   Elemente: {len(self.netz['elemente'])}   |   "
                                    f"Kabel: {len(self.netz['kabel'])}   |   Zoom: {self.zoom:.2f}x   |   "
                                    f"Datei: {os.path.basename(self.netz_path)}")

    # ---------------- Element Interaktion ----------------

    def on_element_press(self, event, eid):
        self._consumed = True
        if self.mode != "bearbeiten":
            return
        shift = bool(event.state & 0x0001)
        if not shift and eid not in self.selected_elements:
            self.selected_elements = {eid}
            self.selected_cables = set()
        elif shift:
            if eid in self.selected_elements:
                self.selected_elements.discard(eid)
            else:
                self.selected_elements.add(eid)
        wx, wy = self.s2w(event.x, event.y)
        orig = {e: (self.find_element(e)["x"], self.find_element(e)["y"]) for e in self.selected_elements}
        orig_wp = {}
        for cable in self.netz["kabel"]:
            if cable["von_element"] in self.selected_elements or cable["bis_element"] in self.selected_elements \
               or cable["id"] in self.selected_cables:
                orig_wp[cable["id"]] = [list(p) for p in cable.get("wegpunkte", [])]
        self._drag_info = {"type": "element", "start": (wx, wy), "orig": orig, "orig_wp": orig_wp}
        self.redraw()

    def on_element_motion(self, event, eid):
        if self.mode != "bearbeiten" or not self._drag_info:
            return
        wx, wy = self.s2w(event.x, event.y)
        sx0, sy0 = self._drag_info["start"]
        dx, dy = wx - sx0, wy - sy0
        g = self.cfg.get("raster_groesse", 20)
        snap = self.cfg.get("am_raster_einrasten", True)
        for e, (ox, oy) in self._drag_info["orig"].items():
            el = self.find_element(e)
            nx, ny = ox + dx, oy + dy
            if snap:
                nx = round(nx / g) * g
                ny = round(ny / g) * g
            el["x"], el["y"] = nx, ny
        # Wegpunkte von Kabeln, deren BEIDE Enden an bewegten Elementen haengen (oder die selbst
        # selektiert sind), mitverschieben
        for cid, wps in self._drag_info["orig_wp"].items():
            cable = self.find_cable(cid)
            if not cable:
                continue
            both_ends_moving = (cable["von_element"] in self._drag_info["orig"] and
                                 cable["bis_element"] in self._drag_info["orig"]) or cid in self.selected_cables
            if both_ends_moving:
                new_wp = []
                for (owx, owy) in wps:
                    new_wp.append([owx + dx, owy + dy])
                cable["wegpunkte"] = new_wp
        self.redraw()

    def on_element_release(self, event, eid):
        self._drag_info = None
        self.redraw()

    def on_element_double(self, event, eid):
        if self.mode != "bearbeiten":
            return
        el = self.find_element(eid)
        orte = sorted(set(e.get("ort", "") for e in self.netz["elemente"] if e.get("ort")))
        dlg = ElementDialog(self.root, element=el, orte_liste=orte)
        self.root.wait_window(dlg)
        if dlg.result:
            action, data = dlg.result
            if action == "delete":
                self.netz["elemente"] = [e for e in self.netz["elemente"] if e["id"] != eid]
                self.netz["kabel"] = [c for c in self.netz["kabel"]
                                       if c["von_element"] != eid and c["bis_element"] != eid]
            else:
                idx = next(i for i, e in enumerate(self.netz["elemente"]) if e["id"] == eid)
                self.netz["elemente"][idx] = data
            self.refresh_ort_list()
            self.redraw()

    # ---------------- Rotation / Spiegelung (Kontextmenue) ----------------

    def on_canvas_right(self, event):
        self._consumed = True

    def show_element_context_menu(self, event, eid):
        if self.mode != "bearbeiten":
            return
        el = self.find_element(eid)
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Um 90 Grad drehen", command=lambda: self.rotate_element(eid))
        menu.add_command(label="Spiegeln", command=lambda: self.mirror_element(eid))
        menu.add_command(label="Bearbeiten...", command=lambda: self.on_element_double(event, eid))
        menu.add_separator()
        menu.add_command(label="Loeschen", command=lambda: self.delete_element(eid))
        menu.tk_popup(event.x_root, event.y_root)

    def rotate_element(self, eid):
        el = self.find_element(eid)
        el["rotation"] = (el.get("rotation", 0) + 90) % 360
        self.redraw()

    def mirror_element(self, eid):
        el = self.find_element(eid)
        el["mirrored"] = not el.get("mirrored", False)
        self.redraw()

    def delete_element(self, eid):
        if not messagebox.askyesno("Loeschen", "Element wirklich loeschen?"):
            return
        self.netz["elemente"] = [e for e in self.netz["elemente"] if e["id"] != eid]
        self.netz["kabel"] = [c for c in self.netz["kabel"] if c["von_element"] != eid and c["bis_element"] != eid]
        self.redraw()

    # ---------------- Port / Kabel anlegen ----------------

    def on_port_click(self, event, eid, pid, seite):
        self._consumed = True
        if self.mode != "bearbeiten":
            return
        if not self._pending_cable_start:
            self._pending_cable_start = (eid, pid, seite)
            self.redraw()
        else:
            veid, vpid, vseite = self._pending_cable_start
            if veid == eid and vpid == pid:
                self._pending_cable_start = None
                self.redraw()
                return
            von_el = self.find_element(veid)
            bis_el = self.find_element(eid)
            von_port = next((p for p in von_el["ports"] if p["id"] == vpid), None)
            bis_port = next((p for p in bis_el["ports"] if p["id"] == pid), None)
            cable = new_cable(veid, vpid, eid, pid)
            dlg = CableDialog(self.root, cable, self.colors_cfg,
                               f"{von_el['name']} / {von_port['name'] if von_port else '?'}",
                               f"{bis_el['name']} / {bis_port['name'] if bis_port else '?'}")
            self.root.wait_window(dlg)
            self._pending_cable_start = None
            if dlg.result and dlg.result[0] == "save":
                self.netz["kabel"].append(dlg.result[1])
            self.redraw()

    def on_cable_click(self, event, cid):
        self._consumed = True
        shift = bool(event.state & 0x0001)
        if not shift:
            self.selected_cables = {cid}
            self.selected_elements = set()
        else:
            if cid in self.selected_cables:
                self.selected_cables.discard(cid)
            else:
                self.selected_cables.add(cid)
        cable = self.find_cable(cid)
        if cable.get("standard") and len(cable.get("signale", [])) > 1:
            if cid in self.expanded_cables:
                self.expanded_cables.discard(cid)
            else:
                self.expanded_cables.add(cid)
            cable["expanded"] = cid in self.expanded_cables
        self.redraw()

    def on_cable_double(self, event, cid):
        self._consumed = True
        if self.mode != "bearbeiten":
            return
        cable = self.find_cable(cid)
        von_el = self.find_element(cable["von_element"])
        bis_el = self.find_element(cable["bis_element"])
        wx, wy = self.s2w(event.x, event.y)
        # Wegpunkt einfuegen an der geklickten Position (nahe der Linie)
        cable.setdefault("wegpunkte", []).append([wx, wy])
        self.redraw()

    def on_cable_right(self, event, cid):
        self._consumed = True
        if self.mode != "bearbeiten":
            menu = tk.Menu(self.root, tearoff=0)
            cable = self.find_cable(cid)
            von_el = self.find_element(cable["von_element"])
            bis_el = self.find_element(cable["bis_element"])
            menu.add_command(label=f"{von_el['name']} -> {bis_el['name']}", state="disabled")
            menu.tk_popup(event.x_root, event.y_root)
            return
        cable = self.find_cable(cid)
        von_el = self.find_element(cable["von_element"])
        bis_el = self.find_element(cable["bis_element"])
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Bearbeiten (Farbe/Standard/Label)...", command=lambda: self.edit_cable(cid))
        menu.add_command(label="Loeschen", command=lambda: self.delete_cable(cid))
        menu.tk_popup(event.x_root, event.y_root)

    def edit_cable(self, cid):
        cable = self.find_cable(cid)
        von_el = self.find_element(cable["von_element"])
        bis_el = self.find_element(cable["bis_element"])
        von_port = next((p for p in von_el["ports"] if p["id"] == cable["von_port"]), None)
        bis_port = next((p for p in bis_el["ports"] if p["id"] == cable["bis_port"]), None)
        dlg = CableDialog(self.root, cable, self.colors_cfg,
                           f"{von_el['name']} / {von_port['name'] if von_port else '?'}",
                           f"{bis_el['name']} / {bis_port['name'] if bis_port else '?'}")
        self.root.wait_window(dlg)
        if dlg.result:
            action, data = dlg.result
            if action == "delete":
                self.delete_cable(cid)
            else:
                idx = next(i for i, c in enumerate(self.netz["kabel"]) if c["id"] == cid)
                self.netz["kabel"][idx] = data
        self.redraw()

    def delete_cable(self, cid):
        self.netz["kabel"] = [c for c in self.netz["kabel"] if c["id"] != cid]
        self.selected_cables.discard(cid)
        self.redraw()

    # ---------------- Wegpunkte ----------------

    def on_waypoint_press(self, event, cid, idx):
        self._consumed = True
        self._drag_info = {"type": "waypoint", "cable": cid, "index": idx}

    def on_waypoint_motion(self, event, cid, idx):
        if not self._drag_info or self._drag_info.get("type") != "waypoint":
            return
        wx, wy = self.s2w(event.x, event.y)
        cable = self.find_cable(cid)
        cable["wegpunkte"][idx] = [wx, wy]
        self.redraw()

    def remove_waypoint(self, cid, idx):
        cable = self.find_cable(cid)
        if cable and 0 <= idx < len(cable.get("wegpunkte", [])):
            del cable["wegpunkte"][idx]
            self.redraw()

    # ---------------- Leere Flaeche: Marquee / Pan ----------------

    def on_canvas_press(self, event):
        if self._consumed:
            self._consumed = False
            return
        if self.mode != "bearbeiten":
            self.selected_cables = set()
            self.selected_elements = set()
            self.redraw()
            return
        shift = bool(event.state & 0x0001)
        if not shift:
            self.selected_elements = set()
            self.selected_cables = set()
        self._marquee_start = (event.x, event.y)
        self._marquee_item = self.canvas.create_rectangle(event.x, event.y, event.x, event.y,
                                                            outline=THEME["marquee"], dash=(3, 2), tags=("marquee",))
        self.redraw_keep_marquee()

    def redraw_keep_marquee(self):
        pass  # marquee rect bleibt on top, kein voller redraw noetig waehrend Ziehen

    def on_canvas_drag(self, event):
        if self._pending_cable_start and self._temp_line:
            self.canvas.coords(self._temp_line,
                                *self.canvas.coords(self._temp_line)[:2], event.x, event.y)
            return
        if self._marquee_start and self._marquee_item:
            x0, y0 = self._marquee_start
            self.canvas.coords(self._marquee_item, x0, y0, event.x, event.y)

    def on_canvas_release(self, event):
        if self._marquee_start and self._marquee_item:
            x0, y0 = self._marquee_start
            x1, y1 = event.x, event.y
            xa, xb = sorted((x0, x1))
            ya, yb = sorted((y0, y1))
            wxa, wya = self.s2w(xa, ya)
            wxb, wyb = self.s2w(xb, yb)
            for el in self.netz["elemente"]:
                if wxa <= el["x"] <= wxb and wya <= el["y"] <= wyb:
                    self.selected_elements.add(el["id"])
            for cable in self.netz["kabel"]:
                von = self.port_world_pos(cable["von_element"], cable["von_port"])
                bis = self.port_world_pos(cable["bis_element"], cable["bis_port"])
                pts = [von, bis] + [tuple(p) for p in cable.get("wegpunkte", [])]
                if pts and all(wxa <= p[0] <= wxb and wya <= p[1] <= wyb for p in pts if p):
                    self.selected_cables.add(cable["id"])
            self.canvas.delete(self._marquee_item)
            self._marquee_item = None
            self._marquee_start = None
        self.redraw()

    def on_canvas_double(self, event):
        if self.mode != "bearbeiten":
            return
        wx, wy = self.s2w(event.x, event.y)
        el = new_element()
        el["x"], el["y"] = wx, wy
        orte = sorted(set(e.get("ort", "") for e in self.netz["elemente"] if e.get("ort")))
        dlg = ElementDialog(self.root, element=el, orte_liste=orte)
        self.root.wait_window(dlg)
        if dlg.result and dlg.result[0] == "save":
            self.netz["elemente"].append(dlg.result[1])
            self.refresh_ort_list()
        self.redraw()

    def on_pan_start(self, event):
        self._pan_start = (event.x, event.y, self.offset_x, self.offset_y)

    def on_pan_move(self, event):
        if not hasattr(self, "_pan_start"):
            return
        sx, sy, ox, oy = self._pan_start
        self.offset_x = ox + (event.x - sx)
        self.offset_y = oy + (event.y - sy)
        self.redraw()

    def on_zoom(self, event, delta=None):
        d = delta if delta is not None else event.delta
        factor = 1.1 if d > 0 else (1 / 1.1)
        wx, wy = self.s2w(event.x, event.y)
        self.zoom = max(0.2, min(4.0, self.zoom * factor))
        self.offset_x = event.x - wx * self.zoom
        self.offset_y = event.y - wy * self.zoom
        self.redraw()

    def on_delete_key(self, event):
        if self.mode != "bearbeiten":
            return
        for eid in list(self.selected_elements):
            self.netz["elemente"] = [e for e in self.netz["elemente"] if e["id"] != eid]
            self.netz["kabel"] = [c for c in self.netz["kabel"] if c["von_element"] != eid and c["bis_element"] != eid]
        for cid in list(self.selected_cables):
            self.netz["kabel"] = [c for c in self.netz["kabel"] if c["id"] != cid]
        self.selected_elements = set()
        self.selected_cables = set()
        self.redraw()

    # ---------------- Aktionen ----------------

    def action_new_element(self):
        wx, wy = self.s2w(self.canvas.winfo_width() / 2, self.canvas.winfo_height() / 2)
        el = new_element()
        el["x"], el["y"] = wx, wy
        orte = sorted(set(e.get("ort", "") for e in self.netz["elemente"] if e.get("ort")))
        dlg = ElementDialog(self.root, element=el, orte_liste=orte)
        self.root.wait_window(dlg)
        if dlg.result and dlg.result[0] == "save":
            self.netz["elemente"].append(dlg.result[1])
            self.refresh_ort_list()
        self.redraw()

    def open_button(self, btn):
        art = btn.get("art", "url")
        ziel = btn.get("ziel", "")
        if not ziel:
            return
        try:
            if art == "rdp":
                if sys.platform.startswith("win"):
                    subprocess.Popen(["mstsc", f"/v:{ziel}"])
                else:
                    tmp = os.path.join(BASE_DIR, "_temp.rdp")
                    with open(tmp, "w", encoding="utf-8") as f:
                        f.write(f"full address:s:{ziel}\n")
                    webbrowser.open(tmp)
            else:
                webbrowser.open_new_tab(ziel)
        except Exception as ex:
            messagebox.showerror("Fehler", f"Konnte Ziel nicht oeffnen:\n{ex}")

    def save_netz(self):
        save_json(self.netz_path, self.netz)
        save_json(CONFIG_PATH, self.cfg)
        messagebox.showinfo("Gespeichert", f"Netz gespeichert unter:\n{self.netz_path}")

    def save_netz_as(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", initialdir=BASE_DIR,
                                             filetypes=[("JSON", "*.json")])
        if path:
            self.netz_path = path
            self.cfg["letzte_netzdatei"] = os.path.basename(path)
            self.save_netz()

    def open_netz(self):
        path = filedialog.askopenfilename(initialdir=BASE_DIR, filetypes=[("JSON", "*.json")])
        if path:
            self.netz_path = path
            self.netz = load_json(path, {"elemente": [], "kabel": []})
            self.cfg["letzte_netzdatei"] = os.path.basename(path)
            self.refresh_ort_list()
            self.redraw()

    def new_netz(self):
        if messagebox.askyesno("Neu", "Neues, leeres Netz anlegen? Ungespeicherte Aenderungen gehen verloren."):
            self.netz = {"elemente": [], "kabel": []}
            self.selected_elements = set()
            self.selected_cables = set()
            self.refresh_ort_list()
            self.redraw()

    # ---------------- Export: Netzliste ----------------

    def _netzliste_rows(self):
        rows = []
        for cable in self.netz["kabel"]:
            von_el = self.find_element(cable["von_element"])
            bis_el = self.find_element(cable["bis_element"])
            von_port = next((p for p in von_el["ports"] if p["id"] == cable["von_port"]), None) if von_el else None
            bis_port = next((p for p in bis_el["ports"] if p["id"] == cable["bis_port"]), None) if bis_el else None
            for sig in cable.get("signale", []):
                rows.append([
                    von_el["name"] if von_el else "?",
                    von_el.get("ort", "") if von_el else "",
                    von_port["name"] if von_port else "?",
                    bis_el["name"] if bis_el else "?",
                    bis_el.get("ort", "") if bis_el else "",
                    bis_port["name"] if bis_port else "?",
                    cable.get("standard") or "Frei",
                    sig.get("name", ""),
                    sig.get("color", ""),
                    cable.get("label", ""),
                ])
        return rows

    HEADER = ["Element A", "Ort A", "Port A", "Element B", "Ort B", "Port B",
              "Standard", "Signal", "Kabelfarbe", "Label"]

    def export_netzliste_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", initialdir=BASE_DIR,
                                             initialfile="netzliste.csv", filetypes=[("CSV", "*.csv")])
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(self.HEADER)
            w.writerows(self._netzliste_rows())
        messagebox.showinfo("Export", f"Netzliste gespeichert:\n{path}")

    def export_netzliste_xlsx(self):
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, PatternFill
        except ImportError:
            messagebox.showerror("Fehlt", "Das Paket 'openpyxl' ist nicht installiert.\npip install openpyxl")
            return
        path = filedialog.asksaveasfilename(defaultextension=".xlsx", initialdir=BASE_DIR,
                                             initialfile="netzliste.xlsx", filetypes=[("Excel", "*.xlsx")])
        if not path:
            return
        wb = Workbook()
        ws = wb.active
        ws.title = "Netzliste"
        ws.append(self.HEADER)
        for cell in ws[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="24252C")
        for row in self._netzliste_rows():
            ws.append(row)
            farbe = row[8]
            if isinstance(farbe, str) and farbe.startswith("#") and len(farbe) == 7:
                ws.cell(row=ws.max_row, column=9).fill = PatternFill("solid", fgColor=farbe[1:])
        for col in ws.columns:
            maxlen = max((len(str(c.value)) for c in col if c.value is not None), default=10)
            ws.column_dimensions[col[0].column_letter].width = min(40, maxlen + 3)
        wb.save(path)
        messagebox.showinfo("Export", f"Netzliste (Excel) gespeichert:\n{path}")

    # ---------------- Export: PDF (Querformat) ----------------

    def export_pdf(self):
        try:
            from reportlab.lib.pagesizes import A3, landscape
            from reportlab.pdfgen import canvas as pdfcanvas
            from reportlab.lib.units import mm
        except ImportError:
            messagebox.showerror("Fehlt", "Das Paket 'reportlab' ist nicht installiert.\npip install reportlab")
            return
        path = filedialog.asksaveasfilename(defaultextension=".pdf", initialdir=BASE_DIR,
                                             initialfile="verkabelungsplan.pdf", filetypes=[("PDF", "*.pdf")])
        if not path:
            return

        if not self.netz["elemente"]:
            messagebox.showwarning("Leer", "Es sind keine Elemente vorhanden.")
            return

        xs = [el["x"] for el in self.netz["elemente"]]
        ys = [el["y"] for el in self.netz["elemente"]]
        for c in self.netz["kabel"]:
            for wp in c.get("wegpunkte", []):
                xs.append(wp[0]); ys.append(wp[1])
        min_x, max_x = min(xs) - 150, max(xs) + 150
        min_y, max_y = min(ys) - 150, max(ys) + 150
        content_w = max(1, max_x - min_x)
        content_h = max(1, max_y - min_y)

        page_w, page_h = landscape(A3)
        margin = 20 * mm
        avail_w = page_w - 2 * margin
        avail_h = page_h - 2 * margin
        scale = min(avail_w / content_w, avail_h / content_h)

        def px(x, y):
            return margin + (x - min_x) * scale, page_h - margin - (y - min_y) * scale

        cv = pdfcanvas.Canvas(path, pagesize=landscape(A3))
        cv.setTitle("Verkabelungsplan")
        cv.setFont("Helvetica-Bold", 16)
        cv.drawString(margin, page_h - margin + 6, "Verkabelungsplan")
        cv.setFont("Helvetica", 9)
        cv.drawString(margin, page_h - margin - 8, f"Erstellt mit Kabel Doku Uebersicht v{APP_VERSION}")

        # Kabel
        for cable in self.netz["kabel"]:
            von = self.port_world_pos(cable["von_element"], cable["von_port"])
            bis = self.port_world_pos(cable["bis_element"], cable["bis_port"])
            if not von or not bis:
                continue
            pts = [von] + [tuple(p) for p in cable.get("wegpunkte", [])] + [bis]
            signale = cable.get("signale", [{"name": "", "color": "#4fc3f7"}])
            n = len(signale)
            for idx, sig in enumerate(signale):
                offset = (idx - (n - 1) / 2) * 2.2
                cv.setStrokeColor(sig["color"])
                cv.setLineWidth(2.2)
                path_pts = []
                for i, (wx, wy) in enumerate(pts):
                    sx, sy = px(wx, wy)
                    path_pts.append((sx, sy))
                p = cv.beginPath()
                for i, (sx, sy) in enumerate(path_pts):
                    if i == 0:
                        p.moveTo(sx, sy + offset)
                    else:
                        p.lineTo(sx, sy + offset)
                cv.drawPath(p, stroke=1, fill=0)
            if cable.get("label") or cable.get("standard"):
                mx, my = px(*pts[len(pts) // 2])
                cv.setFillColor("#222222")
                cv.setFont("Helvetica", 7)
                cv.drawString(mx + 3, my + 4, cable.get("label") or cable.get("standard") or "")

        # Elemente
        for el in self.netz["elemente"]:
            corners = element_corners(el, self.cfg)
            spts = [px(wx, wy) for wx, wy in corners]
            cv.setStrokeColor("#4fc3f7")
            cv.setFillColor("#eef6fb")
            cv.setLineWidth(1.2)
            p = cv.beginPath()
            p.moveTo(*spts[0])
            for pt in spts[1:]:
                p.lineTo(*pt)
            p.close()
            cv.drawPath(p, stroke=1, fill=1)

            cx, cy = px(el["x"], el["y"])
            w, h = element_size(el, self.cfg)
            cv.setFillColor("#111111")
            cv.setFont("Helvetica-Bold", 8)
            cv.drawCentredString(cx, cy + (h * scale) / 2 + 8, el["name"])
            cv.setFont("Helvetica", 6.5)
            sub = el.get("typ", "")
            if el.get("ort"):
                sub = f"{sub} | Ort: {el['ort']}"
            if sub:
                cv.drawCentredString(cx, cy + (h * scale) / 2 - 2, sub)

            for entry in element_ports_positions(el, self.cfg):
                px_, py_ = px(entry["x"], entry["y"])
                cv.setFillColor("#8a6bff")
                cv.circle(px_, py_, 2, stroke=0, fill=1)
                cv.setFillColor("#333333")
                cv.setFont("Helvetica", 6)
                anchor = 4 if entry["seite"] == "primaer" else -4
                if entry["seite"] == "primaer":
                    cv.drawString(px_ + 5, py_ - 2, f"{entry['index']+1}. {entry['name']}")
                else:
                    cv.drawRightString(px_ - 5, py_ - 2, f"{entry['index']+1}. {entry['name']}")

        cv.save()
        messagebox.showinfo("Export", f"PDF gespeichert:\n{path}")


def main():
    root = tk.Tk()
    app = KabelDokuApp(root)

    menubar = tk.Menu(root)
    m_datei = tk.Menu(menubar, tearoff=0)
    m_datei.add_command(label="Neu", command=app.new_netz)
    m_datei.add_command(label="Oeffnen...", command=app.open_netz)
    m_datei.add_command(label="Speichern", command=app.save_netz)
    m_datei.add_command(label="Speichern unter...", command=app.save_netz_as)
    m_datei.add_separator()
    m_datei.add_command(label="PDF Export...", command=app.export_pdf)
    m_datei.add_command(label="Netzliste CSV Export...", command=app.export_netzliste_csv)
    m_datei.add_command(label="Netzliste Excel Export...", command=app.export_netzliste_xlsx)
    m_datei.add_separator()
    m_datei.add_command(label="Beenden", command=root.quit)
    menubar.add_cascade(label="Datei", menu=m_datei)

    m_ansicht = tk.Menu(menubar, tearoff=0)
    m_ansicht.add_command(label="Modus umschalten", command=app.toggle_mode)
    m_ansicht.add_command(label="Raster ein/aus", command=app.toggle_grid)
    m_ansicht.add_command(label="Zoom zuruecksetzen", command=app.reset_view)
    menubar.add_cascade(label="Ansicht", menu=m_ansicht)

    m_hilfe = tk.Menu(menubar, tearoff=0)
    m_hilfe.add_command(label="Info", command=lambda: messagebox.showinfo(
        "Info", f"{APP_TITLE}\n\nBearbeitungsmodus: Elemente per Doppelklick auf leere Flaeche anlegen, "
                "Ports anklicken um Kabel zu ziehen, Rechtsklick auf Element fuer Drehen/Spiegeln, "
                "Rechtsklick auf Kabel zum Bearbeiten/Loeschen, Doppelklick auf Kabel fuegt Wegpunkt ein.\n\n"
                "Nutzungsmodus: nur Schaltflaechen und Kabel-Hervorhebung aktiv, keine Aenderungen moeglich."))
    menubar.add_cascade(label="Hilfe", menu=m_hilfe)

    root.config(menu=menubar)

    def on_close():
        app.cfg["fenster_breite"] = root.winfo_width()
        app.cfg["fenster_hoehe"] = root.winfo_height()
        save_json(CONFIG_PATH, app.cfg)
        save_json(app.netz_path, app.netz)
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    app.canvas.bind("<Configure>", lambda e: app.redraw())
    root.mainloop()


if __name__ == "__main__":
    main()
