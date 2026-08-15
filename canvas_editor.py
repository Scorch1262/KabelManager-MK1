# -*- coding: utf-8 -*-
"""
canvas_editor.py
================
Der eigentliche Editor: Zeichenbereich (Tkinter Canvas) mit Werkzeugleiste,
Elementpalette, Zoom/Pan, Drag&Drop und Verbindungen.

Das Anlegen von Verbindungen/Kabeln funktioniert wie im Netzwerkplan-
Vorbild: Über den Button "Verbindung" wird der Verbindungsmodus
aktiviert, danach werden Start- und Zielpunkt (Element oder ein
bestimmter Anschluss) direkt im Plan angeklickt. Anschliessend oeffnet
sich der Dialog zur Auswahl von Einzelkabel/Standard-Verkabelung.

Jedes Element zeigt im Bearbeitungsmodus einen eigenen "✎"-Button (wie im
Netzwerkplan) zum direkten Bearbeiten sowie bei Elementen mit Anschluessen
zusaetzlich "⟳" (Anschlussseite drehen) und "⇋" (Reihenfolge spiegeln).
Jede Verbindung hat ebenfalls einen eigenen "✎"-Button. Leitungen werden
als weiche, senkrecht aus der Anschlussseite austretende Kurven
dargestellt (wie im Netzwerkplan-Vorbild / harness.design).
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from collections import defaultdict

from models import (new_element, new_id, ELEMENT_WIDTH, ELEMENT_HEIGHT)
from standards import ELEMENT_TYPES, BUNDLE_LINE_COLOR
from dialogs import ElementDialog, ConnectionDialog, ColorConfigEditor
import config_manager
from pdf_export import export_to_pdf
from netlist_export import export_netlist_xlsx

BG_CANVAS = "#12151b"
BG_GRID = "#1c212a"
COL_ELEMENT_FILL = "#232833"
COL_ELEMENT_OUTLINE = "#5a6473"
COL_ELEMENT_SELECTED = "#ffb454"
COL_ELEMENT_CONNECT_START = "#35d68f"
COL_TEXT_MAIN = "#f2f5f9"
COL_TEXT_SUB = "#9aa5b1"
COL_PIN = "#3ad6ff"
COL_BTN_BG = "#2c3341"
COL_BTN_FG = "#e7ebf1"

PIN_SIDE_ORDER = ["unten", "links", "oben", "rechts"]


class CanvasEditor(ttk.Frame):
    def __init__(self, master, netz_config, farben_config, status_callback=None):
        super().__init__(master)
        self.netz = netz_config
        self.farben = farben_config
        self.mode = self.netz.get("mode", "edit")
        self.selected = None  # ("element", id) | ("connection", id) | None
        self._press_start = None
        self._press_item = None
        self._press_world_orig = None
        self._pan_orig = None
        self._moved = False
        self._status_callback = status_callback
        self._status_override = None

        # Verbindungsmodus (klick-basiertes Anlegen von Kabeln, wie im
        # Netzwerkplan-Vorbild)
        self.connect_mode = False
        self.connect_start = None  # (element_id, pin_name_or_None)

        self._build_ui()
        self.canvas.bind("<Configure>", lambda e: self.render())
        self.after(50, self.render)

    # ------------------------------------------------------------------
    # UI-Aufbau
    # ------------------------------------------------------------------

    def _build_ui(self):
        toolbar = ttk.Frame(self, padding=(6, 6))
        toolbar.pack(side="top", fill="x")

        self.mode_btn = ttk.Button(toolbar, text="", command=self.toggle_mode)
        self.mode_btn.pack(side="left", padx=3)

        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=6)

        self.connect_btn = ttk.Button(toolbar, text="Verbindung", command=self.start_connect_mode)
        self.connect_btn.pack(side="left", padx=3)
        ttk.Button(toolbar, text="Bearbeiten", command=self.edit_selected).pack(side="left", padx=3)
        ttk.Button(toolbar, text="Loeschen", command=self.delete_selected).pack(side="left", padx=3)

        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=6)

        ttk.Button(toolbar, text="−", width=3, command=lambda: self._zoom_button(1 / 1.2)).pack(side="left")
        ttk.Button(toolbar, text="Zoom 100%", command=self._zoom_reset).pack(side="left", padx=3)
        ttk.Button(toolbar, text="+", width=3, command=lambda: self._zoom_button(1.2)).pack(side="left")

        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=6)

        self.grid_var = tk.BooleanVar(value=self.netz["view"].get("show_grid", True))
        ttk.Checkbutton(toolbar, text="Raster", variable=self.grid_var,
                         command=self._toggle_grid).pack(side="left", padx=3)
        self.snap_var = tk.BooleanVar(value=self.netz["view"].get("snap_to_grid", True))
        ttk.Checkbutton(toolbar, text="Einrasten", variable=self.snap_var,
                         command=self._toggle_snap).pack(side="left", padx=3)

        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=6)
        ttk.Button(toolbar, text="Speichern", command=self.save).pack(side="left", padx=3)

        body = ttk.Frame(self)
        body.pack(side="top", fill="both", expand=True)

        palette = ttk.Frame(body, padding=6, width=190)
        palette.pack(side="left", fill="y")
        ttk.Label(palette, text="Element hinzufuegen:", font=("Segoe UI", 9, "bold")).pack(
            anchor="w", pady=(0, 4))
        for typ in ELEMENT_TYPES:
            ttk.Button(palette, text=f"+ {typ}", command=lambda t=typ: self.add_element(t)).pack(
                fill="x", pady=2)

        ttk.Separator(palette, orient="horizontal").pack(fill="x", pady=10)
        ttk.Label(palette, text="Hinweise:", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        hinweis = ("Element ziehen: verschieben.\n"
                   "✎ am Element/Kabel: bearbeiten.\n"
                   "⟳ dreht die Anschlussseite,\n"
                   "⇋ spiegelt die Reihenfolge.\n"
                   "\"Verbindung\": Start- und\n"
                   "Zielpunkt anklicken, danach\n"
                   "Kabelart waehlen.\n"
                   "Klick auf Buendel-Leitung:\n"
                   "auf-/zuklappen.\n"
                   "Mausrad: zoomen.\n"
                   "Ziehen auf leerer Flaeche:\n"
                   "verschieben (pan).\n"
                   "Escape: Verbindung/Auswahl\n"
                   "abbrechen.")
        ttk.Label(palette, text=hinweis, foreground="#8a93a3", justify="left",
                  wraplength=170).pack(anchor="w", pady=(2, 0))

        canvas_frame = ttk.Frame(body)
        canvas_frame.pack(side="left", fill="both", expand=True)
        self.canvas = tk.Canvas(canvas_frame, bg=BG_CANVAS, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_motion)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Double-Button-1>", self._on_double_click)
        self.canvas.bind("<Motion>", self._on_hover)
        self.canvas.bind("<MouseWheel>", self._on_wheel)       # Windows / Mac
        self.canvas.bind("<Button-4>", lambda e: self._zoom_at(e.x, e.y, 1.1))   # Linux
        self.canvas.bind("<Button-5>", lambda e: self._zoom_at(e.x, e.y, 1 / 1.1))
        self.canvas.bind("<Delete>", lambda e: self.delete_selected())
        self.canvas.bind("<BackSpace>", lambda e: self.delete_selected())
        self.canvas.bind("<Escape>", lambda e: self._cancel_connect_mode())

        self._update_mode_button()

    # ------------------------------------------------------------------
    # Modus
    # ------------------------------------------------------------------

    def toggle_mode(self):
        self._cancel_connect_mode()
        self.mode = "nutzung" if self.mode == "edit" else "edit"
        self.netz["mode"] = self.mode
        self._update_mode_button()
        self.render()
        self.save()

    def _update_mode_button(self):
        if self.mode == "edit":
            self.mode_btn.configure(text="Modus: Bearbeiten (zu Nutzung wechseln)")
        else:
            self.mode_btn.configure(text="Modus: Nutzung (zu Bearbeiten wechseln)")

    # ------------------------------------------------------------------
    # Element-/Verbindungs-Zugriff
    # ------------------------------------------------------------------

    def get_element(self, el_id):
        for el in self.netz["elements"]:
            if el["id"] == el_id:
                return el
        return None

    def get_connection(self, conn_id):
        for c in self.netz["connections"]:
            if c["id"] == conn_id:
                return c
        return None

    # ------------------------------------------------------------------
    # Elemente hinzufuegen / bearbeiten / loeschen / drehen / spiegeln
    # ------------------------------------------------------------------

    def add_element(self, typ):
        view = self.netz["view"]
        w = max(self.canvas.winfo_width(), 400)
        h = max(self.canvas.winfo_height(), 300)
        cx = (w / 2 - view["pan_x"]) / view["zoom"]
        cy = (h / 2 - view["pan_y"]) / view["zoom"]
        el = new_element(name=typ, typ=typ, x=cx - ELEMENT_WIDTH / 2, y=cy - ELEMENT_HEIGHT / 2)
        self.netz["elements"].append(el)
        self.render()
        self.edit_element(el["id"])

    def edit_element(self, el_id):
        el = self.get_element(el_id)
        if not el:
            return
        dlg = ElementDialog(self, el)
        self.wait_window(dlg)
        if dlg.result:
            el.update(dlg.result)
            self.render()
            self.save()

    def rotate_element_side(self, el_id):
        el = self.get_element(el_id)
        if not el:
            return
        current = el.get("pin_side", "unten")
        idx = PIN_SIDE_ORDER.index(current) if current in PIN_SIDE_ORDER else 0
        el["pin_side"] = PIN_SIDE_ORDER[(idx + 1) % len(PIN_SIDE_ORDER)]
        self.render()
        self.save()

    def mirror_element_pins(self, el_id):
        el = self.get_element(el_id)
        if not el:
            return
        el["pin_mirror"] = not el.get("pin_mirror", False)
        self.render()
        self.save()

    def _delete_element(self, el_id):
        self.netz["elements"] = [e for e in self.netz["elements"] if e["id"] != el_id]
        self.netz["connections"] = [c for c in self.netz["connections"]
                                     if c["from_element"] != el_id and c["to_element"] != el_id]

    # ------------------------------------------------------------------
    # Verbindungen: klick-basierter Verbindungsmodus (wie im Netzwerkplan)
    # ------------------------------------------------------------------

    def start_connect_mode(self):
        if len(self.netz["elements"]) < 2:
            messagebox.showinfo("Hinweis", "Es werden mindestens zwei Elemente benoetigt, "
                                            "um eine Verbindung anzulegen.", parent=self)
            return
        if self.mode != "edit":
            messagebox.showinfo("Hinweis", "Verbindungen koennen nur im Bearbeitungsmodus "
                                            "angelegt werden.", parent=self)
            return
        self.connect_mode = True
        self.connect_start = None
        self.selected = None
        self.canvas.configure(cursor="crosshair")
        self.connect_btn.configure(text="Verbindung: Startpunkt waehlen")
        self._status_override = ("Verbindungsmodus: Startelement bzw. -anschluss anklicken "
                                  "(Escape zum Abbrechen)")
        self.render()

    def _cancel_connect_mode(self):
        if not self.connect_mode:
            return
        self.connect_mode = False
        self.connect_start = None
        self.canvas.configure(cursor="")
        self.connect_btn.configure(text="Verbindung")
        self._status_override = None
        self.render()

    def _handle_connect_click(self, sx, sy):
        target = self._connect_target_at(sx, sy)
        if self.connect_start is None:
            if target is None:
                self._cancel_connect_mode()
                return
            self.connect_start = target
            self.connect_btn.configure(text="Verbindung: Zielpunkt waehlen")
            self._status_override = ("Verbindungsmodus: Ziel-Element bzw. -anschluss anklicken "
                                      "(Escape zum Abbrechen)")
            self.render()
        else:
            if target is None or target[0] == self.connect_start[0]:
                self._cancel_connect_mode()
                return
            start_id, start_pin = self.connect_start
            end_id, end_pin = target
            self.connect_mode = False
            self.canvas.configure(cursor="")
            self.connect_btn.configure(text="Verbindung")
            self._status_override = None
            self.connect_start = None
            self.render()
            self._open_new_connection_dialog(start_id, start_pin, end_id, end_pin)

    def _open_new_connection_dialog(self, from_id, from_pin, to_id, to_pin):
        dlg = ConnectionDialog(self, self.netz["elements"], self.farben,
                                preset_from=from_id, preset_to=to_id,
                                preset_from_pin=from_pin, preset_to_pin=to_pin)
        self.wait_window(dlg)
        if dlg.result:
            conn = dlg.result
            conn["id"] = new_id("conn")
            self.netz["connections"].append(conn)
            self.render()
            self.save()

    def add_connection(self):
        """Alternativer Einstieg (z. B. ueber Menue) - startet den
        klick-basierten Verbindungsmodus."""
        self.start_connect_mode()

    def edit_connection(self, conn_id):
        conn = self.get_connection(conn_id)
        if not conn:
            return
        dlg = ConnectionDialog(self, self.netz["elements"], self.farben, connection=conn)
        self.wait_window(dlg)
        if dlg.result == "__DELETE__":
            self.netz["connections"] = [c for c in self.netz["connections"] if c["id"] != conn_id]
            self.selected = None
            self.render()
            self.save()
        elif dlg.result:
            conn.update(dlg.result)
            self.render()
            self.save()

    # ------------------------------------------------------------------
    # Auswahl bearbeiten/loeschen (Toolbar-Buttons)
    # ------------------------------------------------------------------

    def edit_selected(self):
        if not self.selected:
            messagebox.showinfo("Hinweis", "Bitte zuerst ein Element oder eine Verbindung "
                                            "anklicken.", parent=self)
            return
        kind, id_ = self.selected
        if kind == "element":
            self.edit_element(id_)
        else:
            self.edit_connection(id_)

    def delete_selected(self):
        if not self.selected:
            return
        kind, id_ = self.selected
        if kind == "element":
            el = self.get_element(id_)
            if el and messagebox.askyesno(
                    "Element loeschen",
                    f"Element '{el['name']}' inklusive aller angeschlossenen Verbindungen "
                    f"wirklich loeschen?", parent=self):
                self._delete_element(id_)
                self.selected = None
                self.render()
                self.save()
        else:
            if messagebox.askyesno("Verbindung loeschen", "Diese Verbindung wirklich loeschen?",
                                    parent=self):
                self.netz["connections"] = [c for c in self.netz["connections"] if c["id"] != id_]
                self.selected = None
                self.render()
                self.save()

    # ------------------------------------------------------------------
    # Kabelfarben-Konfiguration
    # ------------------------------------------------------------------

    def open_color_config(self):
        dlg = ColorConfigEditor(self, self.farben)
        self.wait_window(dlg)
        if dlg.result:
            self.farben.clear()
            self.farben.update(dlg.result)
            config_manager.save_farben_config(self.farben)
            messagebox.showinfo("Gespeichert", "Die Kabelfarben-Konfiguration wurde gespeichert.\n"
                                                "Sie wirkt sich auf neu angelegte Standard-"
                                                "Verbindungen aus.", parent=self)

    # ------------------------------------------------------------------
    # Speichern
    # ------------------------------------------------------------------

    def save(self):
        self.netz["mode"] = self.mode
        config_manager.save_netz_config(self.netz)
        self._update_status()

    def _update_status(self):
        if not self._status_callback:
            return
        if self._status_override:
            self._status_callback(self._status_override)
            return
        n_el = len(self.netz["elements"])
        n_conn = len(self.netz["connections"])
        n_wires = sum(len(c.get("wires", [])) if c["kind"] == "standard" else 1
                      for c in self.netz["connections"])
        modus = "Bearbeiten" if self.mode == "edit" else "Nutzung"
        self._status_callback(
            f"Modus: {modus}   |   Elemente: {n_el}   |   Verbindungen: {n_conn}   "
            f"|   Adern gesamt: {n_wires}   |   Zoom: {int(self.netz['view']['zoom']*100)}%")

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_pdf(self):
        if not self.netz["elements"]:
            messagebox.showinfo("Hinweis", "Es sind keine Elemente vorhanden.", parent=self)
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf", filetypes=[("PDF-Datei", "*.pdf")],
            initialfile="Verkabelungsplan.pdf", title="Verkabelungsplan als PDF speichern")
        if not path:
            return
        try:
            export_to_pdf(path, self.netz, title="Verkabelungsplan")
            messagebox.showinfo("Erfolg", f"PDF wurde gespeichert:\n{path}", parent=self)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Fehler beim PDF-Export", str(exc), parent=self)

    def export_netlist(self):
        if not self.netz["connections"]:
            messagebox.showinfo("Hinweis", "Es sind keine Verbindungen vorhanden.", parent=self)
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx", filetypes=[("Excel-Datei", "*.xlsx")],
            initialfile="Netzliste.xlsx", title="Netzliste als Excel-Tabelle speichern")
        if not path:
            return
        try:
            export_netlist_xlsx(path, self.netz)
            messagebox.showinfo("Erfolg", f"Netzliste wurde gespeichert:\n{path}", parent=self)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Fehler beim Netzlisten-Export", str(exc), parent=self)

    # ------------------------------------------------------------------
    # Zoom / Pan
    # ------------------------------------------------------------------

    def _toggle_grid(self):
        self.netz["view"]["show_grid"] = self.grid_var.get()
        self.render()
        self.save()

    def _toggle_snap(self):
        self.netz["view"]["snap_to_grid"] = self.snap_var.get()
        self.save()

    def _zoom_button(self, factor):
        self._zoom_at(self.canvas.winfo_width() / 2, self.canvas.winfo_height() / 2, factor)

    def _zoom_reset(self):
        self.netz["view"]["zoom"] = 1.0
        self.render()
        self.save()

    def _zoom_at(self, sx, sy, factor):
        view = self.netz["view"]
        old_zoom = view["zoom"]
        new_zoom = min(4.0, max(0.2, old_zoom * factor))
        wx = (sx - view["pan_x"]) / old_zoom
        wy = (sy - view["pan_y"]) / old_zoom
        view["pan_x"] = sx - wx * new_zoom
        view["pan_y"] = sy - wy * new_zoom
        view["zoom"] = new_zoom
        self.render()

    def _on_wheel(self, event):
        factor = 1.1 if event.delta > 0 else 1 / 1.1
        self._zoom_at(event.x, event.y, factor)

    def world_to_screen(self, x, y):
        view = self.netz["view"]
        return (x * view["zoom"] + view["pan_x"], y * view["zoom"] + view["pan_y"])

    def screen_to_world(self, sx, sy):
        view = self.netz["view"]
        return ((sx - view["pan_x"]) / view["zoom"], (sy - view["pan_y"]) / view["zoom"])

    # ------------------------------------------------------------------
    # Maus-Interaktion
    # ------------------------------------------------------------------

    def _hit_test(self, sx, sy):
        """Liefert das oberste getroffene Canvas-Objekt als (art, id)
        zurueck. 'art' kann sein: edit_element, rotate_element,
        mirror_element, edit_connection, element, connection."""
        items = self.canvas.find_overlapping(sx - 4, sy - 4, sx + 4, sy + 4)
        found = None
        priority = {"edit_element": 4, "rotate_element": 4, "mirror_element": 4,
                    "edit_connection": 3, "element": 2, "connection": 1}
        found_prio = -1
        for item in items:
            tags = self.canvas.gettags(item)
            for t in tags:
                for prefix, art in (("editbtn_elem_", "edit_element"),
                                     ("rotatebtn_elem_", "rotate_element"),
                                     ("mirrorbtn_elem_", "mirror_element"),
                                     ("editbtn_conn_", "edit_connection"),
                                     ("elem_", "element"),
                                     ("conn_", "connection")):
                    if t.startswith(prefix):
                        p = priority[art]
                        if p >= found_prio:
                            found_prio = p
                            found = (art, t[len(prefix):])
                        break
        return found

    def _pin_at_screen(self, sx, sy, threshold=10):
        best = None
        best_dist = threshold
        for el in self.netz["elements"]:
            for name, (px, py) in self._pin_positions(el):
                spx, spy = self.world_to_screen(px, py)
                d = ((spx - sx) ** 2 + (spy - sy) ** 2) ** 0.5
                if d < best_dist:
                    best_dist = d
                    best = (el["id"], name)
        return best

    def _connect_target_at(self, sx, sy):
        """Fuer den Verbindungsmodus: liefert (element_id, pin_name_oder_None)."""
        pin_hit = self._pin_at_screen(sx, sy)
        if pin_hit:
            return pin_hit
        hit = self._hit_test(sx, sy)
        if hit and hit[0] in ("element", "edit_element", "rotate_element", "mirror_element"):
            return (hit[1], None)
        return None

    def _on_press(self, event):
        self.canvas.focus_set()
        self._press_start = (event.x, event.y)
        self._moved = False
        if self.connect_mode:
            self._press_item = None
            return
        hit = self._hit_test(event.x, event.y)
        self._press_item = hit
        if hit and hit[0] == "element":
            el = self.get_element(hit[1])
            if el:
                self._press_world_orig = (el["x"], el["y"])
        self._pan_orig = (self.netz["view"]["pan_x"], self.netz["view"]["pan_y"])

    def _on_motion(self, event):
        if self._press_start is None or self.connect_mode:
            return
        dx = event.x - self._press_start[0]
        dy = event.y - self._press_start[1]
        if abs(dx) > 3 or abs(dy) > 3:
            self._moved = True

        if self._press_item and self._press_item[0] == "element" and self.mode == "edit":
            el = self.get_element(self._press_item[1])
            if el is None:
                return
            zoom = self.netz["view"]["zoom"]
            new_x = self._press_world_orig[0] + dx / zoom
            new_y = self._press_world_orig[1] + dy / zoom
            if self.netz["view"].get("snap_to_grid", True):
                gs = self.netz["view"].get("grid_size", 20)
                new_x = round(new_x / gs) * gs
                new_y = round(new_y / gs) * gs
            el["x"], el["y"] = new_x, new_y
            self.render()
        elif not self._press_item:
            self.netz["view"]["pan_x"] = self._pan_orig[0] + dx
            self.netz["view"]["pan_y"] = self._pan_orig[1] + dy
            self.render()

    def _on_hover(self, event):
        if self.mode != "edit" or self.connect_mode:
            return
        hit = self._hit_test(event.x, event.y)
        cursor = ""
        if hit and hit[0] in ("edit_element", "rotate_element", "mirror_element", "edit_connection"):
            cursor = "hand2"
        elif hit and hit[0] == "element":
            cursor = "fleur"
        self.canvas.configure(cursor=cursor)

    def _on_release(self, event):
        if self.connect_mode:
            if not self._moved:
                self._handle_connect_click(event.x, event.y)
            self._press_start = None
            self._press_item = None
            return

        if not self._moved:
            hit = self._press_item
            if hit is None:
                self.selected = None
            elif hit[0] == "edit_element":
                self.edit_element(hit[1])
            elif hit[0] == "rotate_element":
                self.rotate_element_side(hit[1])
            elif hit[0] == "mirror_element":
                self.mirror_element_pins(hit[1])
            elif hit[0] == "edit_connection":
                self.edit_connection(hit[1])
            elif hit[0] == "element":
                self.selected = ("element", hit[1])
            elif hit[0] == "connection":
                self.selected = ("connection", hit[1])
                conn = self.get_connection(hit[1])
                if conn and conn["kind"] == "standard":
                    conn["expanded"] = not conn.get("expanded", False)
            self.render()
        self.save()
        self._press_start = None
        self._press_item = None

    def _on_double_click(self, event):
        if self.connect_mode:
            return
        hit = self._hit_test(event.x, event.y)
        if not hit:
            return
        if hit[0] in ("element", "edit_element") and self.mode == "edit":
            self.edit_element(hit[1])
        elif hit[0] in ("connection", "edit_connection") and self.mode == "edit":
            self.edit_connection(hit[1])

    # ------------------------------------------------------------------
    # Zeichnen
    # ------------------------------------------------------------------

    def _pin_positions(self, el):
        pins = el.get("pins", [])
        if not pins:
            return []
        side = el.get("pin_side", "unten")
        mirror = el.get("pin_mirror", False)
        n = len(pins)
        order = list(range(n))
        if mirror:
            order = order[::-1]
        result = []
        margin_p = 18
        if side in ("unten", "oben"):
            usable = ELEMENT_WIDTH - 2 * margin_p
            for idx, pin_idx in enumerate(order):
                px = el["x"] + margin_p + (usable * (idx + 0.5) / n if n else usable / 2)
                py = el["y"] + ELEMENT_HEIGHT if side == "unten" else el["y"]
                result.append((pins[pin_idx], (px, py)))
        else:
            usable = ELEMENT_HEIGHT - 2 * margin_p
            for idx, pin_idx in enumerate(order):
                py = el["y"] + margin_p + (usable * (idx + 0.5) / n if n else usable / 2)
                px = el["x"] + ELEMENT_WIDTH if side == "rechts" else el["x"]
                result.append((pins[pin_idx], (px, py)))
        return result

    def _element_center(self, el):
        return (el["x"] + ELEMENT_WIDTH / 2, el["y"] + ELEMENT_HEIGHT / 2)

    def _anchor_point(self, el, pin_name):
        if pin_name:
            for name, pt in self._pin_positions(el):
                if name == pin_name:
                    return pt
        return self._element_center(el)

    def _anchor_side(self, el, pin_name):
        """Austrittsrichtung fuer weiche Kurven: nur wenn ein bestimmter
        Anschluss gewaehlt ist, sonst None (dann verlaeuft die Linie
        direkt zum Ziel)."""
        if pin_name and el.get("pins"):
            return el.get("pin_side", "unten")
        return None

    def _parallel_offset(self, p1, p2, idx, total, spacing):
        if total <= 1:
            return (0, 0)
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        length = (dx ** 2 + dy ** 2) ** 0.5 or 1
        perp = (-dy / length, dx / length)
        f = (idx - (total - 1) / 2) * spacing
        return (perp[0] * f, perp[1] * f)

    @staticmethod
    def _side_vector(side):
        return {"unten": (0, 1), "oben": (0, -1), "links": (-1, 0), "rechts": (1, 0)}.get(
            side, (0, 0))

    def _curve_points_world(self, p1, p2, side1, side2, exit_len=42):
        """Baut eine Punktreihe fuer eine weiche Kurve: die Linie verlaesst
        einen mit Anschlussseite versehenen Endpunkt zunaechst senkrecht zu
        dieser Seite, bevor sie in einer Kurve zum Ziel verlaeuft."""
        pts = [p1]
        if side1:
            v = self._side_vector(side1)
            pts.append((p1[0] + v[0] * exit_len, p1[1] + v[1] * exit_len))
        if side2:
            v = self._side_vector(side2)
            pts.append((p2[0] + v[0] * exit_len, p2[1] + v[1] * exit_len))
        pts.append(p2)
        return pts

    def render(self):
        self.canvas.delete("all")
        view = self.netz["view"]
        zoom = view["zoom"]
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w <= 1 or h <= 1:
            return

        if view.get("show_grid", True):
            self._draw_grid(w, h, view)

        pair_total = defaultdict(int)
        for c in self.netz["connections"]:
            pair_total[frozenset((c["from_element"], c["to_element"]))] += 1
        pair_seen = defaultdict(int)
        for c in self.netz["connections"]:
            self._draw_connection(c, pair_total, pair_seen, zoom)

        for el in self.netz["elements"]:
            self._draw_element(el)

        if self.connect_mode and self.connect_start:
            self._draw_connect_highlight()

        self._update_status()

    def _draw_grid(self, w, h, view):
        gs = view.get("grid_size", 20)
        world_x0, world_y0 = self.screen_to_world(0, 0)
        world_x1, world_y1 = self.screen_to_world(w, h)
        start_x = int(world_x0 // gs) * gs
        start_y = int(world_y0 // gs) * gs
        x = start_x
        while x <= world_x1:
            sx, _ = self.world_to_screen(x, 0)
            self.canvas.create_line(sx, 0, sx, h, fill=BG_GRID, tags="grid")
            x += gs
        y = start_y
        while y <= world_y1:
            _, sy = self.world_to_screen(0, y)
            self.canvas.create_line(0, sy, w, sy, fill=BG_GRID, tags="grid")
            y += gs

    def _rounded_rect(self, x0, y0, x1, y1, radius, tags, **kwargs):
        r = min(radius, (x1 - x0) / 2, (y1 - y0) / 2)
        points = [
            x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r,
            x1, y1 - r, x1, y1, x1 - r, y1, x0 + r, y1,
            x0, y1, x0, y1 - r, x0, y0 + r, x0, y0,
        ]
        return self.canvas.create_polygon(points, smooth=True, tags=tags, **kwargs)

    def _draw_small_button(self, cx, cy, symbol, tags, fg=COL_BTN_FG, radius=9):
        self.canvas.create_oval(cx - radius, cy - radius, cx + radius, cy + radius,
                                 fill=COL_BTN_BG, outline="#4a5468", width=1, tags=tags)
        self.canvas.create_text(cx, cy, text=symbol, fill=fg, font=("Segoe UI", 9), tags=tags)

    def _draw_element(self, el):
        x0, y0 = self.world_to_screen(el["x"], el["y"])
        x1, y1 = self.world_to_screen(el["x"] + ELEMENT_WIDTH, el["y"] + ELEMENT_HEIGHT)
        is_connect_start = (self.connect_mode and self.connect_start
                             and self.connect_start[0] == el["id"] and self.connect_start[1] is None)
        selected = self.selected == ("element", el["id"])
        if is_connect_start:
            outline = COL_ELEMENT_CONNECT_START
        elif selected:
            outline = COL_ELEMENT_SELECTED
        else:
            outline = COL_ELEMENT_OUTLINE
        tags = (f'elem_{el["id"]}', "element")
        self._rounded_rect(x0, y0, x1, y1, 10, tags, fill=COL_ELEMENT_FILL, outline=outline,
                            width=2.5 if (selected or is_connect_start) else 1.5)
        self.canvas.create_text((x0 + x1) / 2, y0 + 16, text=el["name"], fill=COL_TEXT_MAIN,
                                 font=("Segoe UI", 10, "bold"), tags=tags)
        sub = el.get("type", "")
        if el.get("location"):
            sub += "  ·  " + el["location"]
        self.canvas.create_text((x0 + x1) / 2, y0 + 32, text=sub, fill=COL_TEXT_SUB,
                                 font=("Segoe UI", 8), tags=tags)

        for name, (px, py) in self._pin_positions(el):
            sx, sy = self.world_to_screen(px, py)
            is_pin_start = (self.connect_mode and self.connect_start
                             and self.connect_start == (el["id"], name))
            pin_fill = COL_ELEMENT_CONNECT_START if is_pin_start else COL_PIN
            pin_r = 4.5 if is_pin_start else 3
            self.canvas.create_oval(sx - pin_r, sy - pin_r, sx + pin_r, sy + pin_r,
                                     fill=pin_fill, outline="", tags=tags)
            if self.netz["view"]["zoom"] > 0.65:
                side = el.get("pin_side", "unten")
                if side == "unten":
                    self.canvas.create_text(sx, sy + 10, text=name, fill=COL_TEXT_SUB,
                                             font=("Segoe UI", 7), tags=tags)
                elif side == "oben":
                    self.canvas.create_text(sx, sy - 10, text=name, fill=COL_TEXT_SUB,
                                             font=("Segoe UI", 7), tags=tags)
                elif side == "links":
                    self.canvas.create_text(sx - 24, sy, text=name, fill=COL_TEXT_SUB,
                                             font=("Segoe UI", 7), tags=tags)
                else:
                    self.canvas.create_text(sx + 24, sy, text=name, fill=COL_TEXT_SUB,
                                             font=("Segoe UI", 7), tags=tags)

        # On-Canvas-Buttons nur im Bearbeitungsmodus
        if self.mode == "edit":
            edit_tags = (f'editbtn_elem_{el["id"]}', "element")
            self._draw_small_button(x1 - 12, y0 + 12, "✎", edit_tags)
            if el.get("pins"):
                rot_tags = (f'rotatebtn_elem_{el["id"]}', "element")
                mir_tags = (f'mirrorbtn_elem_{el["id"]}', "element")
                self._draw_small_button(x0 + 12, y1 - 12, "⟳", rot_tags)
                self._draw_small_button(x0 + 32, y1 - 12, "⇋", mir_tags)

    def _draw_connect_highlight(self):
        el_id, pin_name = self.connect_start
        el = self.get_element(el_id)
        if not el:
            return
        px, py = self._anchor_point(el, pin_name)
        sx, sy = self.world_to_screen(px, py)
        r = 13
        self.canvas.create_oval(sx - r, sy - r, sx + r, sy + r, outline=COL_ELEMENT_CONNECT_START,
                                 width=2, dash=(3, 2), tags="connect_highlight")

    def _draw_bg_label(self, mx, my, text, tags):
        bbox_pad = 3
        tmp = self.canvas.create_text(mx, my, text=text, fill="#eef1f5", font=("Segoe UI", 7, "bold"),
                                       tags=tags)
        bx0, by0, bx1, by1 = self.canvas.bbox(tmp)
        rect = self.canvas.create_rectangle(bx0 - bbox_pad, by0 - 1, bx1 + bbox_pad, by1 + 1,
                                             fill="#333b47", outline="", tags=tags)
        self.canvas.tag_raise(tmp, rect)

    def _draw_curve(self, p1, p2, side1, side2, color, width, tags):
        pts_world = self._curve_points_world(p1, p2, side1, side2)
        flat = []
        for wx, wy in pts_world:
            sx, sy = self.world_to_screen(wx, wy)
            flat += [sx, sy]
        smooth = len(pts_world) > 2
        self.canvas.create_line(*flat, fill=color, width=width, capstyle="round",
                                 smooth=smooth, splinesteps=18, tags=tags)
        mid = pts_world[len(pts_world) // 2] if len(pts_world) > 2 else (
            (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)
        return self.world_to_screen(*mid)

    def _draw_connection(self, c, pair_total, pair_seen, zoom):
        from_el = self.get_element(c["from_element"])
        to_el = self.get_element(c["to_element"])
        if not from_el or not to_el:
            return
        p1 = self._anchor_point(from_el, c.get("from_pin"))
        p2 = self._anchor_point(to_el, c.get("to_pin"))
        side1 = self._anchor_side(from_el, c.get("from_pin"))
        side2 = self._anchor_side(to_el, c.get("to_pin"))
        key = frozenset((c["from_element"], c["to_element"]))
        total = pair_total[key]
        idx = pair_seen[key]
        pair_seen[key] += 1
        off = self._parallel_offset(p1, p2, idx, total, 10)
        p1o = (p1[0] + off[0], p1[1] + off[1])
        p2o = (p2[0] + off[0], p2[1] + off[1])
        selected = self.selected == ("connection", c["id"])
        tags = (f'conn_{c["id"]}', "connection")

        if selected:
            self._draw_curve(p1o, p2o, side1, side2, COL_ELEMENT_SELECTED,
                              (c.get("thickness", 6) + 6) * max(zoom, 0.5), tags)

        if c["kind"] == "einzel":
            color = c.get("color", "#3ad6ff")
            thickness = c.get("thickness", 3)
            mx, my = self._draw_curve(p1o, p2o, side1, side2, color,
                                       max(1.4, thickness * max(zoom, 0.4)), tags)
            if c.get("label"):
                self._draw_bg_label(mx, my - 10, c["label"], tags)
            if self.mode == "edit":
                self._draw_small_button(mx, my, "✎", (f'editbtn_conn_{c["id"]}', "connection"))
        else:
            wires = c.get("wires", [])
            n = len(wires)
            s1 = self.world_to_screen(*p1o)
            s2 = self.world_to_screen(*p2o)
            if not c.get("expanded"):
                width = max(4, 6 * max(zoom, 0.4))
                mx, my = self._draw_curve(p1o, p2o, side1, side2, BUNDLE_LINE_COLOR, width, tags)
                text = f'{c.get("standard","")} ({n} Adern) ▸ Klicken zum Aufklappen'
                self._draw_bg_label(mx, my - 14, text, tags)
                if self.mode == "edit":
                    self._draw_small_button(mx, my + 14, "✎", (f'editbtn_conn_{c["id"]}', "connection"))
            else:
                for wi, wire in enumerate(wires):
                    woff = self._parallel_offset(p1o, p2o, wi, n, 6)
                    wp1 = (p1o[0] + woff[0], p1o[1] + woff[1])
                    wp2 = (p2o[0] + woff[0], p2o[1] + woff[1])
                    mx, my = self._draw_curve(wp1, wp2, side1, side2, wire.get("farbe", "#ffffff"),
                                               max(1.4, 3 * max(zoom, 0.4)), tags)
                    if zoom > 0.55:
                        self.canvas.create_text(mx, my - 7, text=wire.get("signal", ""),
                                                 fill="#c7ccd4", font=("Segoe UI", 7), tags=tags)
                mx, my = (s1[0] + s2[0]) / 2, (s1[1] + s2[1]) / 2
                self._draw_bg_label(mx, my - 22, f'{c.get("standard","")} ▾ Klicken zum Einklappen',
                                     tags)
                if self.mode == "edit":
                    self._draw_small_button(mx, my - 40, "✎", (f'editbtn_conn_{c["id"]}', "connection"))
