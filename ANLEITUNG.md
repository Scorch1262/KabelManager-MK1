# Kabel Doku Uebersicht — v2.0.0

## Dateien in diesem Paket

| Datei | Zweck |
|---|---|
| `kabel_doku.py` | Das Hauptprogramm |
| `config.json` | Allgemeine Einstellungen (muss neben der exe liegen) |
| `colors.json` | Standard-Kabelfarben je Verkabelungstyp, haendisch anpassbar (muss neben der exe liegen) |
| `netz.json` | Wird beim ersten Speichern automatisch neben der exe angelegt (das eigentliche Verkabelungsnetz) |
| `requirements.txt` | Python-Pakete fuer Entwicklung/Build |
| `.github/workflows/build.yml` | GitHub-Actions-Workflow: baut automatisch eine Windows-exe **und** eine macOS-Datei |

## 1. Benoetigte Python-Pakete

Python 3.10+ empfohlen. Installation:

```bash
pip install -r requirements.txt
```

entspricht:

```bash
pip install pyinstaller reportlab openpyxl
```

- **pyinstaller** – zum Erzeugen der exe / macOS-Binary
- **reportlab** – fuer den PDF-Export (Verkabelungsplan im Querformat)
- **openpyxl** – fuer den Netzliste-Export als `.xlsx`
- `tkinter` gehoert bei den meisten Python-Installationen fest dazu (unter Linux ggf. `sudo apt install python3-tk`, unter Windows/macOS ist es im offiziellen Python-Installer enthalten)
- Alles Weitere (json, csv, subprocess, webbrowser, uuid, math) ist Teil der Python-Standardbibliothek

## 2. Programm lokal starten

```bash
python kabel_doku.py
```

Beim ersten Start werden `config.json` und `colors.json` automatisch angelegt, falls sie fehlen.

## 3. Manuell zu exe/Binary bauen (PyInstaller)

**Windows:**
```bash
pyinstaller --noconfirm --onefile --windowed --name KabelDoku --add-data "config.json;." --add-data "colors.json;." kabel_doku.py
```

**macOS / Linux:**
```bash
pyinstaller --noconfirm --onefile --windowed --name KabelDoku --add-data "config.json:." --add-data "colors.json:." kabel_doku.py
```

Nach dem Bauen liegt die ausfuehrbare Datei in `dist/`. **Wichtig:** `config.json` und `colors.json` danach manuell (oder wie im Workflow automatisiert) in denselben Ordner wie die exe kopieren — das Programm sucht sie immer direkt neben seiner eigenen ausfuehrbaren Datei, niemals im PyInstaller-Bundle selbst, damit Aenderungen dauerhaft erhalten bleiben.

## 4. Automatischer Build ueber GitHub Actions

Der Workflow `.github/workflows/build.yml` erzeugt bei jedem Push auf `main`/`master`, bei jedem Tag `v*` oder manuell ueber "Run workflow":

- eine **Windows-exe** (`KabelDoku.exe`, Job `build-windows`)
- eine **macOS-Datei** (`KabelDoku-macos.zip`, enthaelt die ausfuehrbare Binary, Job `build-macos`)

Beide Artefakte kannst du in GitHub unter **Actions → gewaehlter Lauf → Artifacts** herunterladen.

Wird zusaetzlich ein Git-Tag im Format `v2.0.0` gepusht, erstellt der `release`-Job automatisch ein GitHub-Release mit beiden Dateien im Anhang:

```bash
git tag v2.0.0
git push origin v2.0.0
```

## 5. Bedienung — Kurzuebersicht

**Bearbeitungsmodus:**
- Doppelklick auf leere Flaeche → neues Element anlegen
- Element anklicken + ziehen → verschieben (mit Rahmen mehrere markieren → gemeinsam verschieben, Kabel/Wegpunkte werden mitgenommen)
- Rechtsklick auf Element → Drehen (90°) / Spiegeln / Bearbeiten / Loeschen
- Port anklicken, dann zweiten Port anklicken → Kabel-Dialog (Standard/Freie Farbe waehlen)
- Kabel anklicken → auswaehlen/markieren (bei Bus-Standards: ein-/ausklappen der Einzelsignale)
- Doppelklick auf ein Kabel → Wegpunkt einfuegen (weiche Kurve); Wegpunkt-Ziehpunkt mit rechter Maustaste entfernen
- Rechtsklick auf Kabel → Bearbeiten / Loeschen
- Mausrad → Zoom, mittlere Maustaste ziehen → Verschieben der Ansicht (Pan)
- `Entf`-Taste → markierte Elemente/Kabel loeschen

**Nutzungsmodus** (Umschalten oben links):
- alle Bearbeitungs-Schaltflaechen werden ausgeblendet
- Schaltflaechen an Elementen oeffnen Links (neuer Tab) bzw. RDP (`mstsc`)
- Kabel anklicken hebt die komplette Leitung hervor
- Highlight nach Ort ueber das Dropdown oben rechts

## 6. Versionierung

Die Versionsnummer steht oben in `kabel_doku.py` als `APP_VERSION` und im Fenstertitel.
Aktuell: **v2.0.0** — "Initiale vollstaendige Ueberarbeitung (V2): freie Platzierung mit Hilfslinien/Raster, Ports mit Namen, Standard-Bus-Verkabelungen mit ein-/ausklappbaren Signalen, Bearbeitungs-/Nutzungsmodus, PDF- und Netzlisten-Export, GitHub-Actions-Build fuer Windows und macOS."
