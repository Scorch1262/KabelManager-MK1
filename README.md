# Kabelplan

**Aktuelle Version: 1.0.0** – siehe [CHANGELOG.md](CHANGELOG.md) für alle
Änderungen.

Ein **lokal laufendes Desktop-Programm** (kein Webserver, kein Browser) zur
Planung von **Verkabelungen**: frei platzierbare Elemente (Steckverbinder,
Platinen/PCBs, Sensoren, Aktoren, Stromversorgungen, Verteiler, Sonstiges),
verbunden durch farbige Kabel. Orientiert sich im Aufbau und Funktionsumfang
an [harness.design](https://docs.harness.design/quick-start/schematic) –
inklusive der Idee, dass sich standardisierte Bündel (z. B. ein UART- oder
I2C-Kabel) im Normalfall als **eine dicke Sammelleitung** darstellen und sich
per Klick zu den **einzelnen Adern** aufklappen lassen.

## Wichtigste Eigenschaften

- **Kein Netzwerk-, sondern ein Verkabelungsplaner.** Es geht um physische
  Kabel zwischen Geräten/Steckern, nicht um IP-Netzwerke.
- **Standard-Verkabelungen als Vorlage:** UART, I2C, SPI, LIN, SENT,
  Ethernet (Cat5e/6, T568B), Analog Video (FPV), DJI Air Unit, CAN-Bus, PWM
  – jede Vorlage bringt sinnvolle Signalnamen und Vorschlags-Kabelfarben mit
  (z. B. I2C: SDA = grün, SCL = gelb).
- **Kabelfarben-Konfiguration:** Die Vorschlagsfarben je Standard liegen in
  einer eigenen, von Hand editierbaren Datei `kabelfarben_config.json`
  direkt neben der exe. Änderungen daran wirken sich **nur auf neu
  angelegte** Kabel dieses Standards aus – bestehende Verbindungen im Plan
  behalten ihre einmal gewählte Farbe.
- **Bündel auf-/zuklappen:** Eine Standard-Verkabelung wird normalerweise als
  eine dicke, einfarbige Leitung dargestellt. Ein Klick darauf klappt sie auf
  und zeigt alle enthaltenen Adern einzeln in ihrer jeweiligen Farbe (inkl.
  Signalbezeichnung); erneuter Klick klappt sie wieder zu.
- **Einzelkabel** lassen sich zusätzlich frei mit eigener Farbe, Stärke und
  Bezeichnung anlegen.
- **PDF-Export im Querformat** des kompletten Verkabelungsplans.
- **Netzliste-Export als Excel-Tabelle:** Auflistung aller Einzeladern mit
  Von-Gerät/Anschluss, Nach-Gerät/Anschluss und Kabelfarbe – Standard-Bündel
  werden dabei automatisch in ihre Einzeladern aufgelöst.
- **Menschenlesbare Konfiguration**, komplett auf Deutsch, direkt neben der
  exe gespeichert und von Hand editierbar.

## 1. Benötigte Python-Pakete

Python 3.10+ wird empfohlen. Installation:

```bash
pip install -r requirements.txt
```

entspricht:

```bash
pip install reportlab==4.2.5
pip install openpyxl==3.1.5
pip install pyinstaller==6.10.0
```

- **reportlab** – für den PDF-Export im Querformat.
- **openpyxl** – für den Netzlisten-Export als Excel-Tabelle.
- **PyInstaller** – zum Erzeugen der eigenständigen exe / Mac-Datei.
- Die Bedienoberfläche selbst basiert auf **Tkinter**, das bei den meisten
  Python-Installationen für Windows/macOS bereits enthalten ist (unter
  Linux ggf. `sudo apt install python3-tk`).

## 2. Programm direkt starten (zum Testen)

```bash
python app.py
```

Es öffnet sich ein normales Programmfenster – es wird **kein** Browser oder
Webserver gestartet.

## 3. Ordnerstruktur

```
kabelplan/
├── app.py                    Programmstart / Hauptfenster
├── canvas_editor.py           Zeichenbereich, Werkzeugleiste, Interaktion
├── dialogs.py                  Dialogfenster (Element/Verbindung/Farben)
├── models.py                    Hilfsfunktionen für Elemente/Verbindungen
├── standards.py                  Werksseitige Standard-Verkabelungen
├── config_manager.py              Laden/Speichern der Konfigurationsdateien
├── pdf_export.py                   PDF-Export (Querformat)
├── netlist_export.py                Netzlisten-Export (Excel)
├── verkabelung_config.json           Verkabelungsnetz (wird automatisch angelegt)
├── kabelfarben_config.json            Kabelfarben je Standard (wird automatisch angelegt)
└── requirements.txt
```

## 4. Automatischer Build per GitHub Actions (empfohlen)

Dieses Repository enthält bereits den Workflow
`.github/workflows/build-exe.yml`. Er baut automatisch **sowohl eine
Windows-`.exe`** (auf einem Windows-Runner) **als auch eine ausführbare
Datei für macOS** (auf einem macOS-Runner) – parallel, in einem einzigen
Workflow-Lauf. Es muss also weder ein Windows- noch ein Mac-Rechner lokal
vorhanden sein.

**Vorgehen:**

1. Repository-Inhalt (alle Dateien und Ordner dieses Projekts, inklusive
   `.github/`) in ein neues GitHub-Repository pushen:
   ```bash
   git init
   git add .
   git commit -m "Kabelplan"
   git branch -M main
   git remote add origin https://github.com/<dein-benutzername>/<dein-repo>.git
   git push -u origin main
   ```
2. Der Workflow startet automatisch beim Push auf `main` (auch manuell
   auslösbar über den Reiter **Actions → Build Windows EXE + macOS App →
   Run workflow**).
3. Nach ca. 2–4 Minuten sind die Builds unter **Actions → [letzter Lauf] →
   Artifacts** als ZIP herunterladbar:
   - **Kabelplan-Windows** – enthält `Kabelplan.exe`, `README.md` und
     `VERSION`.
   - **Kabelplan-macOS** – enthält die ausführbare Datei `Kabelplan` (ohne
     Dateiendung), `README.md` und `VERSION`.
4. Für ein richtiges GitHub **Release** (dauerhafte Download-Links für
   beide Plattformen) zusätzlich einen Tag pushen, z. B.:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```
   Der Workflow wartet dann, bis **beide** Builds fertig sind, und erstellt
   automatisch ein Release mit `Kabelplan-Windows.exe`, `Kabelplan-macOS`,
   `README.md` und `VERSION` als Anhang.

Der Workflow benötigt keine zusätzlichen GitHub Secrets – `GITHUB_TOKEN`
wird von GitHub Actions automatisch bereitgestellt.

### Hinweis zur Nutzung der macOS-Datei

Macs blockieren unsignierte, aus dem Internet heruntergeladene Programme
standardmäßig (Gatekeeper). Nach dem Download der Datei `Kabelplan`:

```bash
chmod +x Kabelplan
xattr -d com.apple.quarantine Kabelplan   # Download-Sperre entfernen
./Kabelplan
```

Alternativ: Rechtsklick auf die Datei im Finder → **Öffnen** → im
Warnhinweis erneut **Öffnen** bestätigen.

## 4b. Alternative: manueller Build mit PyInstaller

Im Projektordner (dort, wo `app.py` liegt) folgenden Befehl ausführen:

```bash
pyinstaller --onefile --name Kabelplan app.py
```

Nach dem Build liegt die fertige Datei unter `dist/Kabelplan.exe` (Windows)
bzw. `dist/Kabelplan` (macOS/Linux).

## 5. Wichtig: Konfigurationsdateien liegen neben der exe

Beim ersten Start legt das Programm automatisch zwei Dateien im selben
Verzeichnis wie die exe an, falls noch keine vorhanden sind:

- **`verkabelung_config.json`** – der komplette Verkabelungsplan (Ansicht,
  Elemente, Verbindungen). Wird nach jeder Änderung automatisch
  gespeichert.
- **`kabelfarben_config.json`** – die Vorschlags-Kabelfarben je Standard-
  Verkabelung (UART, I2C, SPI, LIN, SENT, Ethernet, Analog Video, DJI Air
  Unit, CAN-Bus, PWM, ...). Kann über **Bearbeiten → Kabelfarben-
  Konfiguration bearbeiten** im Programm **oder** von Hand in einem
  Texteditor angepasst werden (gültiges JSON beachten). Neue Standards
  bzw. Adern lassen sich hier ebenfalls ergänzen. **Änderungen wirken sich
  ausschließlich auf neu angelegte Kabel dieses Standards aus** – bereits
  im Plan vorhandene Verbindungen behalten ihre Farbe unverändert.

Sollen vorbereitete Konfigurationsdateien verwendet werden, einfach diese
Dateien manuell in denselben Ordner wie `Kabelplan.exe` kopieren, bevor die
exe gestartet wird.

## 6. Bedienung

- **Element hinzufügen:** In der linken Palette auf einen der Typen
  klicken (Steckverbinder, Platine/PCB, Sensor, Aktor, Stromversorgung,
  Verteiler, Sonstiges). Es öffnet sich sofort der Bearbeiten-Dialog für
  Name, Typ, Standort, Anschlussseite und eine Liste der Anschlüsse (ein
  Name je Zeile, z. B. `TX`, `RX`, `GND`).
- **Element verschieben:** Im Bearbeitungsmodus mit gedrückter linker
  Maustaste ziehen (rastet ein, sofern „Einrasten“ aktiviert ist).
- **Ansicht verschieben (Pan):** Auf leerer Fläche ziehen.
- **Zoom:** Mausrad, oder die Buttons „−“ / „+“ / „Zoom 100 %“ in der
  Werkzeugleiste.
- **Element bearbeiten/löschen:** Element anklicken (Auswahl, oranger
  Rahmen), dann „Bearbeiten“ bzw. „Löschen“ in der Werkzeugleiste, oder
  Doppelklick zum direkten Bearbeiten, oder Entf-Taste zum Löschen.
- **Verbindung hinzufügen:** Über den Button „Verbindung hinzufügen“ in der
  Werkzeugleiste öffnet sich ein Dialog: Start- und Zielgerät (sowie
  optional deren Anschluss) auswählen, dann zwischen **Einzelkabel**
  (Farbe, Stärke, Bezeichnung frei wählbar) und **Standard-Verkabelung**
  wählen. Bei einer Standard-Verkabelung wird die Vorlage (z. B. I2C)
  gewählt; alle enthaltenen Adern erscheinen mit ihrer Vorschlagsfarbe aus
  der Kabelfarben-Konfiguration und können für dieses eine Kabel bei Bedarf
  einzeln angepasst werden (Farbe, Von-/Nach-Anschlussbezeichnung).
- **Standard-Bündel auf-/zuklappen:** Im Plan wird eine Standard-
  Verkabelung als eine dicke, graue Sammelleitung mit Beschriftung (z. B.
  „I2C (4 Adern) ▸“) dargestellt. Ein Klick darauf klappt sie auf und zeigt
  alle Adern einzeln in ihrer jeweiligen Farbe mit Signalbezeichnung;
  erneuter Klick klappt sie wieder zu einer Sammelleitung zusammen. Der
  Auf-/Zu-Zustand wird mitgespeichert.
- **Verbindung bearbeiten/löschen:** Verbindung anklicken (Auswahl), dann
  „Bearbeiten“ bzw. „Löschen“, oder Doppelklick zum direkten Bearbeiten.
- **Nutzungsmodus:** Über den Modus-Button oben links lässt sich zwischen
  „Bearbeiten“ (Elemente/Verbindungen anlegen, verschieben, ändern) und
  „Nutzung“ (nur Ansehen, Zoomen, Bündel auf-/zuklappen – keine
  Änderungen) umschalten.
- **PDF-Export:** Menü **Datei → Als PDF exportieren (Querformat) ...**
  exportiert den kompletten aktuellen Plan als PDF im Querformat (A4 quer),
  automatisch skaliert.
- **Netzliste exportieren:** Menü **Datei → Netzliste als Excel
  exportieren ...** erzeugt eine Excel-Tabelle mit einer Zeile je
  Einzelader: Von-Gerät/Standort/Anschluss, Nach-Gerät/Standort/Anschluss,
  Kabelfarbe, Typ (Einzelkabel oder Standard-Name) und
  Bezeichnung/Signal. Standard-Bündel werden dabei automatisch in ihre
  Einzeladern aufgelöst.
- **Speichern:** Über den Button „Speichern“, das Menü **Datei →
  Speichern**, oder automatisch nach jeder Änderung (Elemente,
  Verbindungen, Ansicht, Modus).

## 7. Werksseitig enthaltene Standard-Verkabelungen

| Standard | Adern (Standard-Farben in der Vorlage) |
|---|---|
| UART | TX (orange), RX (blau), VCC (rot), GND (dunkelgrau) |
| I2C | SDA (grün), SCL (gelb), VCC (rot), GND (dunkelgrau) |
| SPI | MOSI, MISO, SCK, CS, VCC, GND |
| LIN | LIN (violett), VCC (rot), GND (dunkelgrau) |
| SENT | SENT (türkis), VCC (rot), GND (dunkelgrau) |
| Ethernet (Cat5e/6, T568B) | 8 Adern nach T568B-Farbschema |
| Analog Video (FPV) | Video (gelb), VCC (rot), GND (dunkelgrau) |
| DJI Air Unit | VBAT, GND, UART2 TX/RX, Video In |
| CAN-Bus | CAN-H, CAN-L, VCC, GND |
| PWM | Signal, VCC, GND |

Alle Standards, Adern und Farben lassen sich über **Bearbeiten →
Kabelfarben-Konfiguration bearbeiten** frei ergänzen, umbenennen oder
entfernen.
