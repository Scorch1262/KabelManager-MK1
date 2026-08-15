#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kabelplan
=========
Lokales Desktop-Programm (kein Webserver/Browser) zur Planung von
Verkabelungen: frei platzierbare Elemente (Steckverbinder, Platinen,
Sensoren, ...), verbunden durch Einzelkabel oder gebuendelte Standard-
Verkabelungen (UART, I2C, SPI, LIN, SENT, Ethernet, Analog Video,
DJI Air Unit, CAN-Bus, PWM, ...).

Konfiguration wird menschenlesbar direkt neben der exe / dem Skript
gespeichert:
  - verkabelung_config.json   (Ansicht, Elemente, Verbindungen)
  - kabelfarben_config.json   (Vorschlags-Farben je Standard-Verkabelung)
"""

import tkinter as tk
from tkinter import ttk, messagebox

import config_manager
from canvas_editor import CanvasEditor

APP_TITLE = "Kabelplan – Verkabelungsplan-Editor"


def get_version():
    try:
        path = config_manager.os.path.join(config_manager.BASE_DIR, "VERSION")
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return "1.0.0"


class KabelplanApp:
    def __init__(self, root):
        self.root = root
        self.version = get_version()
        self.root.title(f"{APP_TITLE}  (v{self.version})")
        self.root.geometry("1280x800")
        self.root.minsize(900, 600)

        self.netz_config = config_manager.load_netz_config()
        self.farben_config = config_manager.load_farben_config()

        self._build_menu()

        self.editor = CanvasEditor(self.root, self.netz_config, self.farben_config,
                                    status_callback=self._set_status)
        self.editor.pack(fill="both", expand=True)

        self.status_bar = ttk.Label(self.root, text="Bereit.", anchor="w",
                                     padding=(8, 3), relief="sunken")
        self.status_bar.pack(side="bottom", fill="x")

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_menu(self):
        menubar = tk.Menu(self.root)

        datei_menu = tk.Menu(menubar, tearoff=0)
        datei_menu.add_command(label="Speichern", command=lambda: self.editor.save())
        datei_menu.add_separator()
        datei_menu.add_command(label="Als PDF exportieren (Querformat) ...",
                                command=lambda: self.editor.export_pdf())
        datei_menu.add_command(label="Netzliste als Excel exportieren ...",
                                command=lambda: self.editor.export_netlist())
        datei_menu.add_separator()
        datei_menu.add_command(label="Beenden", command=self._on_close)
        menubar.add_cascade(label="Datei", menu=datei_menu)

        bearbeiten_menu = tk.Menu(menubar, tearoff=0)
        bearbeiten_menu.add_command(label="Ausgewaehltes bearbeiten",
                                     command=lambda: self.editor.edit_selected())
        bearbeiten_menu.add_command(label="Ausgewaehltes loeschen",
                                     command=lambda: self.editor.delete_selected())
        bearbeiten_menu.add_separator()
        bearbeiten_menu.add_command(label="Kabelfarben-Konfiguration bearbeiten ...",
                                     command=lambda: self.editor.open_color_config())
        menubar.add_cascade(label="Bearbeiten", menu=bearbeiten_menu)

        ansicht_menu = tk.Menu(menubar, tearoff=0)
        ansicht_menu.add_command(label="Zoom zuruecksetzen (100%)",
                                  command=lambda: self.editor._zoom_reset())
        ansicht_menu.add_command(label="Modus wechseln (Bearbeiten/Nutzung)",
                                  command=lambda: self.editor.toggle_mode())
        menubar.add_cascade(label="Ansicht", menu=ansicht_menu)

        hilfe_menu = tk.Menu(menubar, tearoff=0)
        hilfe_menu.add_command(label="Ueber Kabelplan", command=self._show_about)
        menubar.add_cascade(label="Hilfe", menu=hilfe_menu)

        self.root.config(menu=menubar)

    def _set_status(self, text):
        if hasattr(self, "status_bar"):
            self.status_bar.configure(text=text)

    def _show_about(self):
        messagebox.showinfo(
            "Ueber Kabelplan",
            f"Kabelplan – Verkabelungsplan-Editor\nVersion {self.version}\n\n"
            "Lokales Programm zur Planung von Verkabelungen mit Unterstuetzung "
            "fuer Standard-Verkabelungen (UART, I2C, SPI, LIN, SENT, Ethernet, "
            "Analog Video, DJI Air Unit, CAN-Bus, PWM, ...).\n\n"
            "Konfigurationsdateien liegen im Programmverzeichnis:\n"
            f"  {config_manager.NETZ_CONFIG_PATH}\n"
            f"  {config_manager.FARBEN_CONFIG_PATH}",
        )

    def _on_close(self):
        try:
            self.editor.save()
        except Exception:
            pass
        self.root.destroy()


def main():
    root = tk.Tk()
    try:
        style = ttk.Style(root)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure(".", background="#1b1f27", foreground="#f2f5f9")
        style.configure("TFrame", background="#1b1f27")
        style.configure("TLabelframe", background="#1b1f27", foreground="#f2f5f9")
        style.configure("TLabelframe.Label", background="#1b1f27", foreground="#f2f5f9")
        style.configure("TLabel", background="#1b1f27", foreground="#f2f5f9")
        style.configure("TButton", background="#2c3341", foreground="#f2f5f9")
        style.configure("TCheckbutton", background="#1b1f27", foreground="#f2f5f9")
        style.configure("TRadiobutton", background="#1b1f27", foreground="#f2f5f9")
        root.configure(bg="#1b1f27")
    except Exception:
        pass
    KabelplanApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
