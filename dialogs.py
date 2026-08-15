# -*- coding: utf-8 -*-
"""
dialogs.py
==========
Saemtliche modalen Dialogfenster der Anwendung (Tkinter Toplevel).
"""

import copy
import tkinter as tk
from tkinter import ttk, colorchooser, messagebox, simpledialog

from standards import ELEMENT_TYPES

PIN_SIDES = ["unten", "oben", "links", "rechts"]


# --------------------------------------------------------------------------
# Kleine Hilfs-Widgets
# --------------------------------------------------------------------------

class FarbSwatch(tk.Frame):
    """Kleines Rechteck + Button, um eine Hex-Farbe auszuwaehlen."""

    def __init__(self, parent, farbe="#3ad6ff", command=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.farbe = farbe
        self._command = command
        self.swatch = tk.Label(self, width=3, bg=self.farbe, relief="solid", bd=1)
        self.swatch.pack(side="left", padx=(0, 4))
        self.btn = ttk.Button(self, text="Farbe waehlen", command=self._pick)
        self.btn.pack(side="left")

    def _pick(self):
        result = colorchooser.askcolor(color=self.farbe, title="Kabelfarbe waehlen")
        if result and result[1]:
            self.set_farbe(result[1])

    def set_farbe(self, farbe):
        self.farbe = farbe
        self.swatch.configure(bg=farbe)
        if self._command:
            self._command(farbe)


# --------------------------------------------------------------------------
# Element-Dialog
# --------------------------------------------------------------------------

class ElementDialog(tk.Toplevel):
    """Anlegen/Bearbeiten eines Elements (Geraet/Steckverbinder)."""

    def __init__(self, parent, element=None):
        super().__init__(parent)
        self.title("Element bearbeiten" if element else "Neues Element")
        self.resizable(False, False)
        self.transient(parent)
        self.result = None
        self._orig = element

        pad = {"padx": 8, "pady": 4}

        frm = ttk.Frame(self, padding=12)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Name:").grid(row=0, column=0, sticky="w", **pad)
        self.name_var = tk.StringVar(value=element["name"] if element else "Neues Element")
        ttk.Entry(frm, textvariable=self.name_var, width=32).grid(row=0, column=1, **pad)

        ttk.Label(frm, text="Typ:").grid(row=1, column=0, sticky="w", **pad)
        self.typ_var = tk.StringVar(value=element["type"] if element else ELEMENT_TYPES[0])
        ttk.Combobox(frm, textvariable=self.typ_var, values=ELEMENT_TYPES,
                     state="readonly", width=29).grid(row=1, column=1, **pad)

        ttk.Label(frm, text="Standort:").grid(row=2, column=0, sticky="w", **pad)
        self.ort_var = tk.StringVar(value=element.get("location", "") if element else "")
        ttk.Entry(frm, textvariable=self.ort_var, width=32).grid(row=2, column=1, **pad)

        ttk.Label(frm, text="Anschlussseite:").grid(row=3, column=0, sticky="w", **pad)
        self.side_var = tk.StringVar(value=element.get("pin_side", "unten") if element else "unten")
        ttk.Combobox(frm, textvariable=self.side_var, values=PIN_SIDES,
                     state="readonly", width=29).grid(row=3, column=1, **pad)

        self.mirror_var = tk.BooleanVar(value=element.get("pin_mirror", False) if element else False)
        ttk.Checkbutton(frm, text="Anschlussreihenfolge spiegeln",
                         variable=self.mirror_var).grid(row=4, column=1, sticky="w", **pad)

        ttk.Label(frm, text="Anschluesse\n(ein Name je Zeile,\nleer lassen = keine Pins):",
                  justify="left").grid(row=5, column=0, sticky="nw", **pad)
        self.pins_text = tk.Text(frm, width=32, height=8)
        pins = element.get("pins", []) if element else []
        self.pins_text.insert("1.0", "\n".join(pins))
        self.pins_text.grid(row=5, column=1, **pad)

        btns = ttk.Frame(frm)
        btns.grid(row=6, column=0, columnspan=2, pady=(10, 0), sticky="e")
        ttk.Button(btns, text="Abbrechen", command=self._cancel).pack(side="right", padx=4)
        ttk.Button(btns, text="Speichern", command=self._save).pack(side="right", padx=4)

        self.bind("<Return>", lambda e: self._save())
        self.bind("<Escape>", lambda e: self._cancel())
        self.grab_set()
        self.after(10, self.focus_set)

    def _save(self):
        name = self.name_var.get().strip() or "Element"
        pins_raw = self.pins_text.get("1.0", "end").strip()
        pins = [p.strip() for p in pins_raw.splitlines() if p.strip()]
        self.result = {
            "name": name,
            "type": self.typ_var.get(),
            "location": self.ort_var.get().strip(),
            "pin_side": self.side_var.get(),
            "pin_mirror": self.mirror_var.get(),
            "pins": pins,
        }
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()


# --------------------------------------------------------------------------
# Verbindungs-Dialog (Einzelkabel oder Standard-Verkabelung)
# --------------------------------------------------------------------------

class ConnectionDialog(tk.Toplevel):
    """Anlegen/Bearbeiten einer Verbindung zwischen zwei Elementen."""

    NONE_PIN = "(kein bestimmter Anschluss)"

    def __init__(self, parent, elements, farben_config, connection=None,
                 preset_from=None, preset_to=None):
        super().__init__(parent)
        self.title("Verbindung bearbeiten" if connection else "Neue Verbindung")
        self.resizable(False, False)
        self.transient(parent)
        self.result = None
        self._orig = connection
        self.elements = elements  # Liste der Element-dicts
        self.farben_config = farben_config
        self._wire_rows = []  # aktuelle Zeilen im Standard-Bereich

        self.by_id = {el["id"]: el for el in elements}
        names = [f'{el["name"]} ({el.get("location","")})' if el.get("location") else el["name"]
                 for el in elements]
        self.id_by_label = {lbl: el["id"] for lbl, el in zip(names, elements)}
        self.label_by_id = {el["id"]: lbl for lbl, el in zip(names, elements)}

        outer = ttk.Frame(self, padding=12)
        outer.pack(fill="both", expand=True)

        # --- Von / Nach ------------------------------------------------
        top = ttk.LabelFrame(outer, text="Verbindung zwischen", padding=8)
        top.pack(fill="x", pady=(0, 8))

        ttk.Label(top, text="Von Geraet:").grid(row=0, column=0, sticky="w", padx=4, pady=3)
        self.von_var = tk.StringVar()
        self.von_cb = ttk.Combobox(top, textvariable=self.von_var, values=names,
                                    state="readonly", width=28)
        self.von_cb.grid(row=0, column=1, padx=4, pady=3)

        ttk.Label(top, text="Von Anschluss:").grid(row=1, column=0, sticky="w", padx=4, pady=3)
        self.von_pin_var = tk.StringVar()
        self.von_pin_cb = ttk.Combobox(top, textvariable=self.von_pin_var,
                                        state="readonly", width=28)
        self.von_pin_cb.grid(row=1, column=1, padx=4, pady=3)

        ttk.Label(top, text="Nach Geraet:").grid(row=0, column=2, sticky="w", padx=4, pady=3)
        self.nach_var = tk.StringVar()
        self.nach_cb = ttk.Combobox(top, textvariable=self.nach_var, values=names,
                                     state="readonly", width=28)
        self.nach_cb.grid(row=0, column=3, padx=4, pady=3)

        ttk.Label(top, text="Nach Anschluss:").grid(row=1, column=2, sticky="w", padx=4, pady=3)
        self.nach_pin_var = tk.StringVar()
        self.nach_pin_cb = ttk.Combobox(top, textvariable=self.nach_pin_var,
                                         state="readonly", width=28)
        self.nach_pin_cb.grid(row=1, column=3, padx=4, pady=3)

        self.von_cb.bind("<<ComboboxSelected>>", lambda e: self._refresh_pins("von"))
        self.nach_cb.bind("<<ComboboxSelected>>", lambda e: self._refresh_pins("nach"))

        # --- Art der Verbindung -----------------------------------------
        art = ttk.LabelFrame(outer, text="Art der Verbindung", padding=8)
        art.pack(fill="x", pady=(0, 8))
        self.art_var = tk.StringVar(value="einzel")
        ttk.Radiobutton(art, text="Einzelkabel", variable=self.art_var, value="einzel",
                         command=self._update_art).pack(side="left", padx=8)
        ttk.Radiobutton(art, text="Standard-Verkabelung (Buendel)", variable=self.art_var,
                         value="standard", command=self._update_art).pack(side="left", padx=8)

        # --- Bezeichnung --------------------------------------------------
        lbl_frame = ttk.Frame(outer)
        lbl_frame.pack(fill="x", pady=(0, 8))
        ttk.Label(lbl_frame, text="Bezeichnung:").pack(side="left", padx=(0, 4))
        self.label_var = tk.StringVar()
        ttk.Entry(lbl_frame, textvariable=self.label_var, width=40).pack(side="left")

        # --- Bereich Einzelkabel -------------------------------------------
        self.einzel_frame = ttk.LabelFrame(outer, text="Einzelkabel-Eigenschaften", padding=8)
        ttk.Label(self.einzel_frame, text="Farbe:").grid(row=0, column=0, sticky="w", padx=4, pady=3)
        self.farb_swatch = FarbSwatch(self.einzel_frame, farbe="#3ad6ff")
        self.farb_swatch.grid(row=0, column=1, sticky="w", padx=4, pady=3)
        ttk.Label(self.einzel_frame, text="Staerke (px):").grid(row=1, column=0, sticky="w", padx=4, pady=3)
        self.staerke_var = tk.IntVar(value=3)
        ttk.Spinbox(self.einzel_frame, from_=1, to=12, textvariable=self.staerke_var,
                    width=6).grid(row=1, column=1, sticky="w", padx=4, pady=3)

        # --- Bereich Standard-Verkabelung -----------------------------------
        self.standard_frame = ttk.LabelFrame(outer, text="Standard-Verkabelung", padding=8)
        ttk.Label(self.standard_frame, text="Standard:").grid(row=0, column=0, sticky="w", padx=4, pady=3)
        self.standard_var = tk.StringVar()
        std_names = list(self.farben_config.get("standards", {}).keys())
        self.standard_cb = ttk.Combobox(self.standard_frame, textvariable=self.standard_var,
                                         values=std_names, state="readonly", width=32)
        self.standard_cb.grid(row=0, column=1, sticky="w", padx=4, pady=3)
        self.standard_cb.bind("<<ComboboxSelected>>", lambda e: self._build_wire_rows())

        self.wires_container = ttk.Frame(self.standard_frame)
        self.wires_container.grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))

        hdr = ttk.Frame(self.wires_container)
        hdr.grid(row=0, column=0, sticky="w")
        ttk.Label(hdr, text="Signal", width=22).grid(row=0, column=0)
        ttk.Label(hdr, text="Farbe", width=16).grid(row=0, column=1)
        ttk.Label(hdr, text="Anschluss (von)", width=16).grid(row=0, column=2)
        ttk.Label(hdr, text="Anschluss (nach)", width=16).grid(row=0, column=3)
        self.wire_rows_frame = ttk.Frame(self.wires_container)
        self.wire_rows_frame.grid(row=1, column=0, sticky="w")

        # --- Buttons -------------------------------------------------------
        btns = ttk.Frame(outer)
        btns.pack(fill="x", pady=(10, 0))
        if connection:
            ttk.Button(btns, text="Loeschen", command=self._delete).pack(side="left")
        ttk.Button(btns, text="Abbrechen", command=self._cancel).pack(side="right", padx=4)
        ttk.Button(btns, text="Speichern", command=self._save).pack(side="right", padx=4)

        self._prefill(connection, preset_from, preset_to)
        self._update_art()

        self.grab_set()
        self.after(10, self.focus_set)

    # -- Hilfsfunktionen ----------------------------------------------------

    def _pins_for(self, element_id):
        el = self.by_id.get(element_id)
        if not el:
            return [self.NONE_PIN]
        return [self.NONE_PIN] + list(el.get("pins", []))

    def _refresh_pins(self, side):
        if side == "von":
            el_id = self.id_by_label.get(self.von_var.get())
            self.von_pin_cb.configure(values=self._pins_for(el_id))
            self.von_pin_var.set(self.NONE_PIN)
        else:
            el_id = self.id_by_label.get(self.nach_var.get())
            self.nach_pin_cb.configure(values=self._pins_for(el_id))
            self.nach_pin_var.set(self.NONE_PIN)

    def _update_art(self):
        if self.art_var.get() == "einzel":
            self.standard_frame.pack_forget()
            self.einzel_frame.pack(fill="x", pady=(0, 8))
        else:
            self.einzel_frame.pack_forget()
            self.standard_frame.pack(fill="x", pady=(0, 8))
            if not self._wire_rows and self.standard_var.get():
                self._build_wire_rows()

    def _build_wire_rows(self, preset_wires=None):
        for w in self.wire_rows_frame.winfo_children():
            w.destroy()
        self._wire_rows = []

        std_name = self.standard_var.get()
        std = self.farben_config.get("standards", {}).get(std_name)
        if not std:
            return
        preset_by_signal = {}
        if preset_wires:
            for w in preset_wires:
                preset_by_signal[w["signal"]] = w

        for i, leitung in enumerate(std.get("leitungen", [])):
            signal = leitung["signal"]
            preset = preset_by_signal.get(signal, {})
            farbe = preset.get("farbe", leitung.get("farbe", "#ffffff"))

            row = ttk.Frame(self.wire_rows_frame)
            row.grid(row=i, column=0, sticky="w", pady=1)
            ttk.Label(row, text=signal, width=22).grid(row=0, column=0)
            swatch = FarbSwatch(row, farbe=farbe)
            swatch.grid(row=0, column=1, sticky="w")
            von_var = tk.StringVar(value=preset.get("von_anschluss", ""))
            ttk.Entry(row, textvariable=von_var, width=17).grid(row=0, column=2, padx=2)
            nach_var = tk.StringVar(value=preset.get("nach_anschluss", ""))
            ttk.Entry(row, textvariable=nach_var, width=17).grid(row=0, column=3, padx=2)

            self._wire_rows.append({
                "signal": signal,
                "swatch": swatch,
                "von_var": von_var,
                "nach_var": nach_var,
            })

    def _prefill(self, connection, preset_from, preset_to):
        if connection:
            self.von_var.set(self.label_by_id.get(connection["from_element"], ""))
            self.nach_var.set(self.label_by_id.get(connection["to_element"], ""))
            self._refresh_pins("von")
            self._refresh_pins("nach")
            if connection.get("from_pin"):
                self.von_pin_var.set(connection["from_pin"])
            if connection.get("to_pin"):
                self.nach_pin_var.set(connection["to_pin"])
            self.label_var.set(connection.get("label", ""))
            if connection["kind"] == "einzel":
                self.art_var.set("einzel")
                self.farb_swatch.set_farbe(connection.get("color", "#3ad6ff"))
                self.staerke_var.set(connection.get("thickness", 3))
            else:
                self.art_var.set("standard")
                self.standard_var.set(connection.get("standard", ""))
                self._build_wire_rows(connection.get("wires", []))
        else:
            if preset_from:
                self.von_var.set(self.label_by_id.get(preset_from, ""))
                self._refresh_pins("von")
            if preset_to:
                self.nach_var.set(self.label_by_id.get(preset_to, ""))
                self._refresh_pins("nach")
            if self.von_var.get() == "" and self.elements:
                self.von_var.set(self.label_by_id[self.elements[0]["id"]])
                self._refresh_pins("von")
            if self.nach_var.get() == "" and len(self.elements) > 1:
                self.nach_var.set(self.label_by_id[self.elements[1]["id"]])
                self._refresh_pins("nach")

    # -- Speichern / Abbrechen -----------------------------------------------

    def _save(self):
        von_label = self.von_var.get()
        nach_label = self.nach_var.get()
        if not von_label or not nach_label:
            messagebox.showerror("Fehler", "Bitte Start- und Zielgeraet waehlen.", parent=self)
            return
        von_id = self.id_by_label.get(von_label)
        nach_id = self.id_by_label.get(nach_label)
        if von_id == nach_id:
            messagebox.showerror("Fehler", "Start- und Zielgeraet muessen unterschiedlich sein.",
                                  parent=self)
            return

        von_pin = self.von_pin_var.get()
        nach_pin = self.nach_pin_var.get()
        von_pin = None if von_pin in ("", self.NONE_PIN) else von_pin
        nach_pin = None if nach_pin in ("", self.NONE_PIN) else nach_pin

        base = {
            "from_element": von_id,
            "from_pin": von_pin,
            "to_element": nach_id,
            "to_pin": nach_pin,
            "label": self.label_var.get().strip(),
        }

        if self.art_var.get() == "einzel":
            base["kind"] = "einzel"
            base["color"] = self.farb_swatch.farbe
            base["thickness"] = int(self.staerke_var.get())
        else:
            if not self.standard_var.get():
                messagebox.showerror("Fehler", "Bitte einen Standard waehlen.", parent=self)
                return
            wires = []
            for row in self._wire_rows:
                wires.append({
                    "signal": row["signal"],
                    "farbe": row["swatch"].farbe,
                    "von_anschluss": row["von_var"].get().strip(),
                    "nach_anschluss": row["nach_var"].get().strip(),
                })
            base["kind"] = "standard"
            base["standard"] = self.standard_var.get()
            base["wires"] = wires
            if not base["label"]:
                base["label"] = self.standard_var.get()
            base["expanded"] = self._orig.get("expanded", False) if self._orig else False

        self.result = base
        self.destroy()

    def _delete(self):
        self.result = "__DELETE__"
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()


# --------------------------------------------------------------------------
# Kabelfarben-Konfiguration bearbeiten
# --------------------------------------------------------------------------

class ColorConfigEditor(tk.Toplevel):
    """Editor fuer die kabelfarben_config.json (Standards + Leitungsfarben)."""

    def __init__(self, parent, farben_config):
        super().__init__(parent)
        self.title("Kabelfarben-Konfiguration bearbeiten")
        self.geometry("640x420")
        self.transient(parent)
        self.result = None
        self.data = copy.deepcopy(farben_config)
        if "standards" not in self.data:
            self.data["standards"] = {}

        main = ttk.Frame(self, padding=10)
        main.pack(fill="both", expand=True)

        left = ttk.Frame(main)
        left.pack(side="left", fill="y", padx=(0, 10))
        ttk.Label(left, text="Standard-Verkabelungen:").pack(anchor="w")
        self.std_list = tk.Listbox(left, width=28, height=18, exportselection=False)
        self.std_list.pack(fill="y", expand=True)
        self.std_list.bind("<<ListboxSelect>>", lambda e: self._select_standard())

        std_btns = ttk.Frame(left)
        std_btns.pack(fill="x", pady=4)
        ttk.Button(std_btns, text="Neu", command=self._new_standard).pack(side="left", padx=2)
        ttk.Button(std_btns, text="Umbenennen", command=self._rename_standard).pack(side="left", padx=2)
        ttk.Button(std_btns, text="Entfernen", command=self._delete_standard).pack(side="left", padx=2)

        right = ttk.Frame(main)
        right.pack(side="left", fill="both", expand=True)
        ttk.Label(right, text="Leitungen (Signal / Farbe):").pack(anchor="w")
        self.wire_list = tk.Listbox(right, height=14, exportselection=False)
        self.wire_list.pack(fill="both", expand=True)

        wire_btns = ttk.Frame(right)
        wire_btns.pack(fill="x", pady=4)
        ttk.Button(wire_btns, text="Leitung hinzufuegen", command=self._add_wire).pack(side="left", padx=2)
        ttk.Button(wire_btns, text="Farbe aendern", command=self._change_wire_color).pack(side="left", padx=2)
        ttk.Button(wire_btns, text="Umbenennen", command=self._rename_wire).pack(side="left", padx=2)
        ttk.Button(wire_btns, text="Entfernen", command=self._delete_wire).pack(side="left", padx=2)

        bottom = ttk.Frame(self, padding=(10, 0, 10, 10))
        bottom.pack(fill="x")
        ttk.Button(bottom, text="Abbrechen", command=self._cancel).pack(side="right", padx=4)
        ttk.Button(bottom, text="Speichern", command=self._save).pack(side="right", padx=4)

        self._current_standard = None
        self._reload_standard_list()
        self.grab_set()

    def _reload_standard_list(self, select=None):
        self.std_list.delete(0, "end")
        for name in self.data["standards"].keys():
            self.std_list.insert("end", name)
        if select and select in self.data["standards"]:
            idx = list(self.data["standards"].keys()).index(select)
            self.std_list.selection_set(idx)
            self._select_standard()
        elif self.data["standards"]:
            self.std_list.selection_set(0)
            self._select_standard()

    def _select_standard(self):
        sel = self.std_list.curselection()
        if not sel:
            return
        self._current_standard = self.std_list.get(sel[0])
        self._reload_wire_list()

    def _reload_wire_list(self):
        self.wire_list.delete(0, "end")
        if not self._current_standard:
            return
        std = self.data["standards"][self._current_standard]
        for leitung in std.get("leitungen", []):
            self.wire_list.insert("end", f'{leitung["signal"]}   —   {leitung["farbe"]}')

    def _new_standard(self):
        name = simpledialog.askstring("Neuer Standard", "Name der neuen Standard-Verkabelung:",
                                       parent=self)
        if not name:
            return
        if name in self.data["standards"]:
            messagebox.showerror("Fehler", "Dieser Standard existiert bereits.", parent=self)
            return
        self.data["standards"][name] = {"beschreibung": "", "leitungen": []}
        self._reload_standard_list(select=name)

    def _rename_standard(self):
        if not self._current_standard:
            return
        new_name = simpledialog.askstring("Umbenennen", "Neuer Name:",
                                           initialvalue=self._current_standard, parent=self)
        if not new_name or new_name == self._current_standard:
            return
        self.data["standards"][new_name] = self.data["standards"].pop(self._current_standard)
        self._current_standard = new_name
        self._reload_standard_list(select=new_name)

    def _delete_standard(self):
        if not self._current_standard:
            return
        if messagebox.askyesno("Entfernen", f"Standard '{self._current_standard}' wirklich entfernen?",
                                parent=self):
            del self.data["standards"][self._current_standard]
            self._current_standard = None
            self._reload_standard_list()

    def _add_wire(self):
        if not self._current_standard:
            messagebox.showinfo("Hinweis", "Bitte zuerst einen Standard auswaehlen.", parent=self)
            return
        signal = simpledialog.askstring("Neue Leitung", "Signalname:", parent=self)
        if not signal:
            return
        result = colorchooser.askcolor(color="#3ad6ff", title="Kabelfarbe waehlen")
        farbe = result[1] if result and result[1] else "#3ad6ff"
        self.data["standards"][self._current_standard]["leitungen"].append(
            {"signal": signal, "farbe": farbe})
        self._reload_wire_list()

    def _selected_wire_index(self):
        sel = self.wire_list.curselection()
        return sel[0] if sel else None

    def _change_wire_color(self):
        idx = self._selected_wire_index()
        if idx is None or not self._current_standard:
            return
        leitung = self.data["standards"][self._current_standard]["leitungen"][idx]
        result = colorchooser.askcolor(color=leitung["farbe"], title="Kabelfarbe waehlen")
        if result and result[1]:
            leitung["farbe"] = result[1]
            self._reload_wire_list()

    def _rename_wire(self):
        idx = self._selected_wire_index()
        if idx is None or not self._current_standard:
            return
        leitung = self.data["standards"][self._current_standard]["leitungen"][idx]
        new_name = simpledialog.askstring("Umbenennen", "Neuer Signalname:",
                                           initialvalue=leitung["signal"], parent=self)
        if new_name:
            leitung["signal"] = new_name
            self._reload_wire_list()

    def _delete_wire(self):
        idx = self._selected_wire_index()
        if idx is None or not self._current_standard:
            return
        del self.data["standards"][self._current_standard]["leitungen"][idx]
        self._reload_wire_list()

    def _save(self):
        self.result = self.data
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()
