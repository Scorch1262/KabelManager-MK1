/* =========================================================================
   Verkabelungsplan – Frontend-Logik
   ========================================================================= */

/* Elementtypen (Stand v3.1.0). Die vorherigen Netzwerk-Typen aus der
   Netzwerkplan-Aera (switch, gateway, server, pc, laptop, lan_socket,
   patchpanel) sind hier absichtlich NICHT mehr enthalten, damit sie nicht
   mehr aus der Palette wählbar sind – bestehende Elemente dieser Typen aus
   älteren config.json-Dateien laden aber weiterhin fehlerfrei (Fallback auf
   "Sonstiges"-Darstellung über `ELEMENT_TYPES[el.type] || ELEMENT_TYPES.generic`)
   und bleiben mit ihrem ursprünglichen `type`-Wert unverändert gespeichert.
   "ethernet_switch" ist die einzige Ausnahme: ein waschechtes Netzwerkgerät,
   das auf Wunsch wieder in die Palette aufgenommen wurde. */
const ELEMENT_TYPES = {
  power_supply:   { label: "Stromversorgung", icon: "⚡", color: "#ffd23d" },
  battery:        { label: "Batterie",        icon: "🔋", color: "#35d68f" },
  motor:          { label: "Motor",           icon: "⚙",  color: "#ff8a3d" },
  actuator:       { label: "Antrieb",         icon: "↻",  color: "#ffb347" },
  board:          { label: "Platine",         icon: "▤",  color: "#3ad6ff" },
  controller:     { label: "Steuergerät",     icon: "▦",  color: "#3ad6ff" },
  terminal_block: { label: "Klemmleiste",     icon: "▥",  color: "#9aa7b8" },
  delay:          { label: "Delay",           icon: "⏱",  color: "#b98bff" },
  raspberry_pi:   { label: "Raspberry Pi",    icon: "◍",  color: "#ff4d5e" },
  camera:         { label: "Kamera",          icon: "◉",  color: "#ffd23d" },
  router:         { label: "Router",          icon: "⇋",  color: "#ff8a3d" },
  ethernet_switch:{ label: "Ethernet Switch", icon: "⇄",  color: "#3ad6ff" },
  relay:          { label: "Relay",           icon: "⟲",  color: "#35d68f" },
  switch_2pos:    { label: "Schalter",        icon: "⏻",  color: "#e8edf4" },
  button:         { label: "Taster",          icon: "●",  color: "#e8edf4" },
  potentiometer:  { label: "Poti",            icon: "◑",  color: "#e8edf4" },
  generic:        { label: "Sonstiges",       icon: "▪",  color: "#9aa7b8" },
};

/* Netzwerkgeraete: bei diesen Typen bleibt es bei "Port"/"Ports" (statt
   "Pin"/"Pins") in der Oberflaeche, Netzliste etc. – siehe portWord(). */
function isNetworkDevice(type) {
  return type === "router" || type === "ethernet_switch"
    // Legacy-Netzwerktypen aus der Netzwerkplan-Aera (Abwaertskompatibilitaet):
    || type === "switch" || type === "patchpanel" || type === "gateway"
    || type === "server" || type === "pc" || type === "laptop" || type === "lan_socket";
}
function portWord(type) { return isNetworkDevice(type) ? "Port" : "Pin"; }
function portWordPlural(type) { return isNetworkDevice(type) ? "Ports" : "Pins"; }

/* Relay: Kontaktart bestimmt die Anzahl der Kontakt-Pins (+2 feste Pins fuer
   die Spule). DIN-Klemmenbezeichnungen (11/12/14) als Standard-Pinnamen. */
const RELAY_TYPES = {
  schliesser: {
    label: "Schließer",
    pinCount: 4,
    names: ["Spule A1", "Spule A2", "gemeinsam (11)", "Schließer (14)"],
  },
  oeffner: {
    label: "Öffner",
    pinCount: 4,
    names: ["Spule A1", "Spule A2", "gemeinsam (11)", "Öffner (12)"],
  },
  wechsler: {
    label: "Wechsler",
    pinCount: 5,
    names: ["Spule A1", "Spule A2", "gemeinsam (11)", "Öffner (12)", "Schließer (14)"],
  },
};
function getRelayType(el) {
  return RELAY_TYPES[el.relay_type] ? el.relay_type : "schliesser";
}

/* Motor: Bauart bestimmt die Anzahl der Anschluss-Pins. */
const MOTOR_TYPES = {
  dc_ac:   { label: "Gleich-/Wechselstrommotor", pinCount: 2, names: ["+", "-"] },
  bldc:    { label: "Bürstenloser Motor (BLDC)", pinCount: 3, names: ["U", "V", "W"] },
  stepper: { label: "Schrittmotor",              pinCount: 4, names: ["A+", "A-", "B+", "B-"] },
};
function getMotorType(el) {
  return MOTOR_TYPES[el.motor_type] ? el.motor_type : "dc_ac";
}

const CONNECTION_COLORS = [
  "#3ad6ff", "#ff8a3d", "#35d68f", "#ff4d5e",
  "#ffd23d", "#b98bff", "#e8edf4", "#5c6b7f",
];

const DEFAULT_ELEMENT_W = 148;
const DEFAULT_ELEMENT_H = 76;

/* Elementtypen mit eigenen Anschluss-Pins/-Ports (je ein Andockpunkt fuer
   Verbindungsleitungen). Wert = Standard-Anzahl bei neuen Elementen (bei
   Relay/Motor nur der Fallback fuer die jeweilige Standard-Bauart, siehe
   RELAY_TYPES/MOTOR_TYPES – die tatsaechliche Anzahl wird beim Aendern der
   Bauart automatisch neu gesetzt). "switch" und "patchpanel" sind aus
   Abwaertskompatibilitaetsgruenden erhalten (siehe Kommentar bei
   ELEMENT_TYPES): so behalten Elemente dieser Typen aus aelteren
   config.json-Dateien ihre Ports/Andockpunkte. board/raspberry_pi starten
   standardmaessig ohne Pins (0) – Pins werden dort optional und individuell
   pro Seite platzierbar hinzugefuegt (siehe hasIndividualPinPlacement). */
const DEFAULT_PORTS = {
  controller: 8,
  terminal_block: 12,
  router: 4,
  ethernet_switch: 8,
  relay: RELAY_TYPES.schliesser.pinCount,
  motor: MOTOR_TYPES.dc_ac.pinCount,
  power_supply: 2,
  battery: 2,
  switch_2pos: 2,
  button: 2,
  potentiometer: 3,
  board: 0,
  raspberry_pi: 0,
  // Legacy (Netzwerkplan v1.x):
  switch: 8,
  patchpanel: 24,
};
/* Mindestanzahl je Typ (Spannungsversorgung/Batterie brauchen mindestens
   Plus- und Minuspol). */
const MIN_PORTS_BY_TYPE = { power_supply: 2, battery: 2 };
function getMinPorts(type) {
  return MIN_PORTS_BY_TYPE[type] || PORT_MIN;
}

const PORT_MIN = 1, PORT_MAX = 48;
const PORT_DOT = 14, PORT_GAP = 5;

/* Reihenfolge beim Rotieren (Uhrzeigersinn): unten -> links -> oben -> rechts */
const PORT_SIDES = ["bottom", "left", "top", "right"];
const OPPOSITE_SIDE = { bottom: "top", top: "bottom", left: "right", right: "left" };

/* Elementtypen, bei denen die Ports auf zwei gegenueberliegenden Seiten mit
   paralleler Nummerierung/Benennung erscheinen (z. B. Vorder-/Rueckseite
   einer Klemmleiste: Port 1 vorne = Port 1 hinten, gleicher Name). */
function hasDualSides(type) {
  return type === "terminal_block" || type === "patchpanel";
}
/* Elementtypen, bei denen jeder Pin einzeln einer Seite zugeordnet werden
   kann (statt eines gemeinsamen Riegels fuer alle Ports auf einer Seite).
   Platine: freie Pin-Platzierung. Raspberry Pi: optionale GPIO-Pins/USB-/
   LAN-Anschluesse, ebenfalls frei platzierbar. */
function hasIndividualPinPlacement(type) {
  return type === "board" || type === "raspberry_pi";
}
function sideAxis(side) {
  return side === "left" || side === "right" ? "horizontal" : "vertical";
}
function sideSlot(side) {
  return side === "top" || side === "left" ? "start" : "end";
}

function hasPorts(type) {
  return Object.prototype.hasOwnProperty.call(DEFAULT_PORTS, type);
}
function getPortCount(el) {
  if (!hasPorts(el.type)) return 0;
  const n = parseInt(el.ports, 10);
  return Number.isFinite(n) && n > 0 ? n : DEFAULT_PORTS[el.type];
}
function getPortSide(el) {
  return PORT_SIDES.includes(el.port_side) ? el.port_side : "bottom";
}
function getPortMirror(el) {
  return !!el.port_mirror;
}
function getPortName(el, index) {
  const arr = el.port_names;
  if (Array.isArray(arr) && typeof arr[index] === "string" && arr[index].trim()) {
    return arr[index].trim();
  }
  return null;
}
/* Individuelle Seite eines einzelnen Pins (nur fuer Platine/Raspberry Pi
   relevant, siehe hasIndividualPinPlacement). Fehlt der Eintrag, wird reihum
   auf bottom/right/top/left verteilt, damit auch ohne manuelle Zuweisung ein
   sinnvolles Layout entsteht. */
function getPinSide(el, index) {
  const arr = el.pin_sides;
  if (Array.isArray(arr) && PORT_SIDES.includes(arr[index])) return arr[index];
  return ["bottom", "right", "top", "left"][index % 4];
}
/* Pin-Art nur fuer Raspberry Pi: "pin" (GPIO), "usb" oder "lan". */
function getPinKind(el, index) {
  const arr = el.pin_kinds;
  if (Array.isArray(arr) && ["pin", "usb", "lan"].includes(arr[index])) return arr[index];
  return "pin";
}

/* ------------------------------------------------------------------ */
/* Schaltplan-Symbole (Anzeigebild) fuer Relay, Motor, Schalter, Taster */
/* und Poti – kompakte Inline-SVGs, die im Element-Icon (26x26px) statt */
/* eines einzelnen Icon-Zeichens dargestellt werden. `currentColor`     */
/* uebernimmt automatisch die Typfarbe (siehe .el-icon style="color").  */
/* ------------------------------------------------------------------ */

function schematicSvg(inner) {
  return `<svg viewBox="0 0 24 24" class="el-icon-svg" xmlns="http://www.w3.org/2000/svg">` +
    `<g stroke="currentColor" fill="none" stroke-width="1.5" stroke-linecap="round">${inner}</g></svg>`;
}

function schematicRelaySvg(relayType) {
  const coil = `<rect x="1" y="7.5" width="7" height="9" rx="1"/>
    <line x1="-1" y1="9.5" x2="1" y2="9.5"/>
    <line x1="-1" y1="14.5" x2="1" y2="14.5"/>
    <circle cx="12" cy="12" r="1.1" fill="currentColor" stroke="none"/>`;
  if (relayType === "oeffner") {
    return schematicSvg(coil +
      `<circle cx="21" cy="19" r="1.1" fill="currentColor" stroke="none"/>
       <circle cx="21" cy="5" r="1.1" fill="none" stroke-width="1" stroke-dasharray="0.8,1.2"/>
       <line x1="12" y1="12" x2="20.3" y2="18"/>`);
  }
  if (relayType === "wechsler") {
    return schematicSvg(coil +
      `<circle cx="21" cy="5" r="1.1" fill="currentColor" stroke="none"/>
       <circle cx="21" cy="19" r="1.1" fill="currentColor" stroke="none"/>
       <line x1="12" y1="12" x2="20.3" y2="18"/>
       <line x1="12" y1="12" x2="20.3" y2="6" stroke-width="1" stroke-dasharray="0.8,1.2"/>`);
  }
  // schliesser (Standard)
  return schematicSvg(coil +
    `<circle cx="21" cy="5" r="1.1" fill="currentColor" stroke="none"/>
     <circle cx="21" cy="19" r="1.1" fill="none" stroke-width="1" stroke-dasharray="0.8,1.2"/>
     <line x1="12" y1="12" x2="20.3" y2="6"/>`);
}

function schematicMotorSvg(motorType) {
  const body = `<circle cx="12" cy="11" r="7.5"/>
    <text x="12" y="14.3" font-size="9" text-anchor="middle" fill="currentColor" stroke="none" font-family="Arial, sans-serif">M</text>`;
  if (motorType === "bldc") {
    return schematicSvg(body +
      `<line x1="12" y1="3.5" x2="12" y2="0.5"/>
       <line x1="6" y1="16" x2="3" y2="21"/>
       <line x1="18" y1="16" x2="21" y2="21"/>`);
  }
  if (motorType === "stepper") {
    return schematicSvg(body +
      `<line x1="12" y1="3.5" x2="12" y2="0.5"/>
       <line x1="12" y1="18.5" x2="12" y2="22.5"/>
       <line x1="4.5" y1="11" x2="0.5" y2="11"/>
       <line x1="19.5" y1="11" x2="23.5" y2="11"/>`);
  }
  // dc_ac (Standard): 2 Anschluesse unten
  return schematicSvg(body +
    `<line x1="8" y1="18" x2="8" y2="23"/>
     <line x1="16" y1="18" x2="16" y2="23"/>`);
}

function schematicSwitchSvg() {
  return schematicSvg(
    `<circle cx="3" cy="18" r="1.4" fill="currentColor" stroke="none"/>
     <circle cx="21" cy="18" r="1.4" fill="currentColor" stroke="none"/>
     <line x1="0" y1="18" x2="3" y2="18"/>
     <line x1="21" y1="18" x2="24" y2="18"/>
     <line x1="3" y1="18" x2="16" y2="7"/>`);
}

function schematicButtonSvg() {
  return schematicSvg(
    `<circle cx="3" cy="19" r="1.4" fill="currentColor" stroke="none"/>
     <circle cx="21" cy="19" r="1.4" fill="currentColor" stroke="none"/>
     <line x1="0" y1="19" x2="3" y2="19"/>
     <line x1="21" y1="19" x2="24" y2="19"/>
     <line x1="3" y1="12" x2="21" y2="12"/>
     <line x1="12" y1="3" x2="12" y2="12"/>
     <line x1="8" y1="3" x2="16" y2="3"/>`);
}

function schematicPotiSvg() {
  return schematicSvg(
    `<rect x="3" y="9" width="18" height="6" rx="1"/>
     <line x1="0" y1="12" x2="3" y2="12"/>
     <line x1="21" y1="12" x2="24" y2="12"/>
     <line x1="12" y1="1" x2="17" y2="9"/>
     <path d="M 15.5 6.2 L 17 9 L 14 8.3 Z" fill="currentColor" stroke="none"/>`);
}

/* Waehlt zwischen einfachem Icon-Zeichen (def.icon) und einem der obigen
   Schaltplan-Symbole, je nach Elementtyp (und bei Relay/Motor je nach
   gewaehlter Bauart). */
function getElementIconMarkup(el, def) {
  switch (el.type) {
    case "relay": return schematicRelaySvg(getRelayType(el));
    case "motor": return schematicMotorSvg(getMotorType(el));
    case "switch_2pos": return schematicSwitchSvg();
    case "button": return schematicButtonSvg();
    case "potentiometer": return schematicPotiSvg();
    default: return escapeHtml(def.icon);
  }
}


let config = null;
let mode = "edit"; // "edit" | "use"

let scale = 1, panX = 0, panY = 0;
const ZOOM_MIN = 0.25, ZOOM_MAX = 2.5;

let isPanning = false, panStart = { x: 0, y: 0 }, panOrigin = { x: 0, y: 0 };
let draggingEl = null, dragOffset = { x: 0, y: 0 };
let dragGroup = null; // { ids, nodes, startPositions, startPointerCanvas } | null
let selectedElementIds = new Set();
let marqueeState = null; // { startX, startY, el } | null
let highlightedConnId = null; // im Nutzermodus per Klick hervorgehobene Verbindung
let highlightedLocation = null; // per Klick auf einen Standort hervorgehobene Elemente (gleicher Ort)
let draggingWaypoint = null; // { connId, index } | null
let draggingLabel = null; // { connId } | null
let connectMode = false, connectFrom = null; // connectFrom = { id, port } | { id, port: null }
let editingElementId = null;
let editingConnId = null;
let selectedColor = CONNECTION_COLORS[0];

/* Relative Position jedes Ports innerhalb seines Elements (in Canvas-Pixeln,
   unabhaengig vom Zoom). Wird nach jedem Rendern der Elemente neu berechnet. */
let portRelOffsets = {}; // { elementId: [{x,y}, ...] }

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

const viewport = $("#viewport");
const canvas = $("#canvas");
const elementLayer = $("#elementLayer");
const connectionLayer = $("#connectionLayer");

/* ------------------------------------------------------------------ */
/* Initialisierung                                                     */
/* ------------------------------------------------------------------ */

async function init() {
  const res = await fetch("/api/config");
  config = await res.json();

  scale = config.view?.zoom ?? 1;
  panX = config.view?.pan_x ?? 0;
  panY = config.view?.pan_y ?? 0;
  mode = config.mode === "use" ? "use" : "edit";

  $("#chkGrid").checked = config.view?.show_grid ?? true;
  $("#chkSnap").checked = config.view?.snap_to_grid ?? true;

  buildPalette();
  buildColorRow();
  buildTypeSelect();
  applyMode();
  applyTransform();
  applyGridVisibility();
  renderAll();

  $("#ipText").textContent = window.location.host;

  bindGlobalEvents();
}

/* ------------------------------------------------------------------ */
/* Palette (Edit-Modus): Elementtypen zum Hinzufuegen                  */
/* ------------------------------------------------------------------ */

function buildPalette() {
  const palette = $("#palette");
  palette.innerHTML = "";
  for (const [type, def] of Object.entries(ELEMENT_TYPES)) {
    const item = document.createElement("div");
    item.className = "palette-item";
    item.title = "Hinzufuegen: " + def.label;
    item.innerHTML = getElementIconMarkup({ type }, def);
    item.addEventListener("click", () => addElement(type));
    palette.appendChild(item);
  }
}

function buildTypeSelect() {
  const sel = $("#fType");
  sel.innerHTML = "";
  for (const [type, def] of Object.entries(ELEMENT_TYPES)) {
    const opt = document.createElement("option");
    opt.value = type;
    opt.textContent = def.label;
    sel.appendChild(opt);
  }
}

function buildColorRow() {
  const row = $("#colorRow");
  row.innerHTML = "";
  for (const color of CONNECTION_COLORS) {
    const sw = document.createElement("div");
    sw.className = "color-swatch";
    sw.style.background = color;
    sw.dataset.color = color;
    sw.addEventListener("click", () => {
      selectedColor = color;
      $$(".color-swatch").forEach((s) => s.classList.remove("selected"));
      sw.classList.add("selected");
      $("#cColorPicker").value = color;
    });
    row.appendChild(sw);
  }
}

$("#cColorPicker").addEventListener("input", (e) => {
  selectedColor = e.target.value;
  $$(".color-swatch").forEach((s) => s.classList.remove("selected"));
});

/* ------------------------------------------------------------------ */
/* Modus: Bearbeitung <-> Nutzung                                      */
/* ------------------------------------------------------------------ */

function applyMode() {
  const btn = $("#modeToggle");
  const label = $("#modeToggleLabel");
  document.body.classList.toggle("edit-mode", mode === "edit");
  document.body.classList.toggle("use-mode", mode === "use");
  highlightedConnId = null;
  highlightedLocation = null;

  if (mode === "edit") {
    label.textContent = "BEARBEITUNGSMODUS";
    btn.classList.remove("use-mode");
  } else {
    label.textContent = "NUTZUNGSMODUS";
    btn.classList.add("use-mode");
    connectMode = false;
    viewport.classList.remove("connect-mode");
    connectFrom = null;
    if (selectedElementIds.size > 0) {
      selectedElementIds.clear();
    }
    if (marqueeState) {
      marqueeState.el.remove();
      marqueeState = null;
    }
    dragGroup = null;
  }
  setStatus(mode === "edit"
    ? "Bearbeitungsmodus – Elemente verschieben, verbinden und bearbeiten."
    : "Nutzungsmodus – nur Links oeffnen moeglich.");
}

$("#modeToggle").addEventListener("click", () => {
  mode = mode === "edit" ? "use" : "edit";
  config.mode = mode;
  applyMode();
  renderAll();
  persistConfig();
});

/* ------------------------------------------------------------------ */
/* Zoom / Pan                                                          */
/* ------------------------------------------------------------------ */

function applyTransform() {
  canvas.style.transform = `translate(${panX}px, ${panY}px) scale(${scale})`;
  $("#zoomLabel").textContent = Math.round(scale * 100) + "%";
}

function applyGridVisibility() {
  canvas.classList.toggle("no-grid", !$("#chkGrid").checked);
}

function zoomAt(clientX, clientY, factor) {
  const rect = viewport.getBoundingClientRect();
  const x = clientX - rect.left;
  const y = clientY - rect.top;
  const newScale = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, scale * factor));
  const ratio = newScale / scale;
  panX = x - (x - panX) * ratio;
  panY = y - (y - panY) * ratio;
  scale = newScale;
  applyTransform();
}

viewport.addEventListener("wheel", (e) => {
  e.preventDefault();
  const factor = e.deltaY < 0 ? 1.1 : 0.9;
  zoomAt(e.clientX, e.clientY, factor);
  saveViewDebounced();
}, { passive: false });

$("#btnZoomIn").addEventListener("click", () => {
  const rect = viewport.getBoundingClientRect();
  zoomAt(rect.left + rect.width / 2, rect.top + rect.height / 2, 1.2);
  saveViewDebounced();
});
$("#btnZoomOut").addEventListener("click", () => {
  const rect = viewport.getBoundingClientRect();
  zoomAt(rect.left + rect.width / 2, rect.top + rect.height / 2, 0.83);
  saveViewDebounced();
});
$("#btnZoomReset").addEventListener("click", () => {
  scale = 1; panX = 0; panY = 0;
  applyTransform();
  saveViewDebounced();
});

/* Pan bei Klick auf leere Flaeche – bei gehaltener Umschalttaste (Shift)
   wird stattdessen ein Auswahlrahmen aufgezogen (Mehrfachauswahl). */
viewport.addEventListener("mousedown", (e) => {
  if (e.target !== viewport && e.target !== canvas) return;
  if (connectMode) return;

  if (mode === "edit" && e.shiftKey) {
    startMarquee(e);
    return;
  }

  if (selectedElementIds.size > 0) {
    elementLayer.querySelectorAll(".net-element.multi-selected").forEach((n) => n.classList.remove("multi-selected"));
    selectedElementIds.clear();
  }
  if (highlightedConnId) {
    highlightedConnId = null;
    renderConnections();
  }
  if (highlightedLocation) {
    highlightedLocation = null;
    renderElements();
  }

  isPanning = true;
  panStart = { x: e.clientX, y: e.clientY };
  panOrigin = { x: panX, y: panY };
  viewport.classList.add("panning");
});

window.addEventListener("mousemove", (e) => {
  if (isPanning) {
    panX = panOrigin.x + (e.clientX - panStart.x);
    panY = panOrigin.y + (e.clientY - panStart.y);
    applyTransform();
  }
  if (draggingEl) {
    moveDraggingElement(e);
  }
  if (draggingWaypoint) {
    moveDraggingWaypoint(e);
  }
  if (draggingLabel) {
    moveDraggingLabel(e);
  }
  if (marqueeState) {
    const rect = viewport.getBoundingClientRect();
    updateMarqueeRect(marqueeState.startX, marqueeState.startY, e.clientX - rect.left, e.clientY - rect.top);
  }
});

window.addEventListener("mouseup", () => {
  if (isPanning) {
    isPanning = false;
    viewport.classList.remove("panning");
    saveViewDebounced();
  }
  if (draggingEl) {
    finishDraggingElement();
  }
  if (draggingWaypoint) {
    draggingWaypoint = null;
    persistConfig();
  }
  if (draggingLabel) {
    draggingLabel = null;
    persistConfig();
  }
  if (marqueeState) {
    finishMarquee();
  }
});

/* ------------------------------------------------------------------ */
/* Rahmen-Mehrfachauswahl (Shift + Ziehen auf leerer Flaeche)          */
/* ------------------------------------------------------------------ */

function startMarquee(e) {
  const rect = viewport.getBoundingClientRect();
  const el = document.createElement("div");
  el.className = "marquee-rect";
  viewport.appendChild(el);
  marqueeState = {
    startX: e.clientX - rect.left,
    startY: e.clientY - rect.top,
    el,
  };
  updateMarqueeRect(marqueeState.startX, marqueeState.startY, marqueeState.startX, marqueeState.startY);
}

function updateMarqueeRect(x1, y1, x2, y2) {
  const left = Math.min(x1, x2), top = Math.min(y1, y2);
  const w = Math.abs(x2 - x1), h = Math.abs(y2 - y1);
  marqueeState.el.style.left = left + "px";
  marqueeState.el.style.top = top + "px";
  marqueeState.el.style.width = w + "px";
  marqueeState.el.style.height = h + "px";
}

function finishMarquee() {
  const box = marqueeState.el.getBoundingClientRect();
  marqueeState.el.remove();
  const ids = new Set();
  elementLayer.querySelectorAll(".net-element").forEach((node) => {
    const r = node.getBoundingClientRect();
    const intersects = !(r.right < box.left || r.left > box.right || r.bottom < box.top || r.top > box.bottom);
    if (intersects) ids.add(node.dataset.id);
  });
  marqueeState = null;
  selectedElementIds = ids;
  renderElements();
  renderConnections();
  setStatus(ids.size > 0
    ? `${ids.size} Element(e) ausgewaehlt – an einem davon ziehen, um alle gemeinsam zu verschieben.`
    : "Keine Elemente im Auswahlrahmen.");
}

function moveDraggingWaypoint(e) {
  const conn = config.connections.find((c) => c.id === draggingWaypoint.connId);
  if (!conn || !Array.isArray(conn.waypoints)) return;
  const rect = viewport.getBoundingClientRect();
  const x = (e.clientX - rect.left - panX) / scale;
  const y = (e.clientY - rect.top - panY) / scale;
  conn.waypoints[draggingWaypoint.index] = { x, y };
  renderConnections();
}

function moveDraggingLabel(e) {
  const conn = config.connections.find((c) => c.id === draggingLabel.connId);
  if (!conn) return;
  conn.label_at = clientToCanvas(e.clientX, e.clientY);
  renderConnections();
}

function clientToCanvas(clientX, clientY) {
  const rect = viewport.getBoundingClientRect();
  return { x: (clientX - rect.left - panX) / scale, y: (clientY - rect.top - panY) / scale };
}

function canvasToClient(point) {
  const rect = viewport.getBoundingClientRect();
  return { x: rect.left + panX + point.x * scale, y: rect.top + panY + point.y * scale };
}

/* ------------------------------------------------------------------ */
/* Elemente: Rendern                                                   */
/* ------------------------------------------------------------------ */

function renderAll() {
  renderElements();
  renderConnections();
}

function renderElements() {
  elementLayer.innerHTML = "";
  for (const el of config.elements) {
    elementLayer.appendChild(buildElementNode(el));
  }
  computePortRelOffsets();
}

/* Erzeugt einen einzelnen Anschluss-Andockpunkt (Pin oder Port, je nach
   Elementtyp – siehe portWord()). Wird sowohl vom gemeinsamen Portriegel
   (buildPortsBar, eine Seite fuer alle Anschluesse) als auch von der
   individuellen Pin-Platzierung (buildIndividualPinsLayer, jeder Anschluss
   einzeln einer Seite zugeordnet – Platine/Raspberry Pi) verwendet. */
function createPinDot(el, index, sideKey, side) {
  const word = portWord(el.type);
  const dot = document.createElement("div");
  dot.className = "port-dot";
  dot.dataset.port = String(index);
  dot.dataset.side = sideKey;
  const customName = getPortName(el, index);
  const sideHint = sideKey === "b" ? " (" + sideLabel(side) + ")" : "";
  const kind = el.type === "raspberry_pi" ? getPinKind(el, index) : "pin";
  const kindLabel = kind === "usb" ? "USB" : kind === "lan" ? "LAN" : null;
  dot.title = customName
    ? `${customName} (${word} ${index + 1}${sideHint})`
    : (kindLabel ? `${kindLabel} ${index + 1}` : `${word} ${index + 1}`) + sideHint +
      " – Doppelklick: Namen vergeben";
  dot.textContent = customName
    ? (index + 1) + " " + customName
    : (kindLabel ? kindLabel : String(index + 1));
  if (kindLabel) dot.classList.add("port-kind-" + kind);
  if (customName) dot.classList.add("port-named");
  dot.addEventListener("mousedown", (e) => e.stopPropagation());
  dot.addEventListener("click", (e) => {
    e.stopPropagation();
    if (mode === "edit" && connectMode) {
      handleConnectPick(el.id, index, sideKey);
    }
  });
  if (mode === "edit") {
    dot.addEventListener("dblclick", (e) => {
      e.preventDefault();
      e.stopPropagation();
      if (connectMode) return;
      openPortNameEditor(el, index, e.clientX, e.clientY);
    });
  }
  return dot;
}

/* Erzeugt eine Portreihe (ports-bar) fuer eine Seite des Elements.
   sideKey ist "a" (primaere/konfigurierte Seite) oder "b" (bei Patchfeldern/
   Klemmleisten die gegenueberliegende Seite mit paralleler Nummerierung/
   Benennung). Beide Seiten teilen sich el.port_names, daher ist eine
   Umbenennung auf der einen Seite automatisch auch auf der anderen
   sichtbar. */
function buildPortsBar(el, side, sideKey, axis, mirrored, portCount) {
  const bar = document.createElement("div");
  bar.className = "ports-bar " + (axis === "vertical" ? "bar-row" : "bar-col") +
    " slot-" + sideSlot(side) + (mirrored ? " mirrored-bar" : "");
  bar.dataset.side = sideKey;

  for (let i = 0; i < portCount; i++) {
    bar.appendChild(createPinDot(el, i, sideKey, side));
  }
  return bar;
}

/* Individuelle Pin-Platzierung (Platine/Raspberry Pi, siehe
   hasIndividualPinPlacement): jeder Pin kann einzeln einer Seite (oben/
   unten/links/rechts) zugewiesen werden, statt eines gemeinsamen Riegels
   fuer alle Anschluesse. Jeder Punkt wird direkt (ohne zusaetzliche
   positionierte Zwischen-Ebene) absolut innerhalb der Layer-Ebene
   platziert – nach genau derselben Formel wie port_point() in app.py
   (Marge 12px, gleichmaessige Verteilung je Seite), damit PDF-Export und
   Webansicht pixelgenau uebereinstimmen. WICHTIG: computePortRelOffsets()
   liest dot.offsetLeft/offsetTop relativ zum naechsten positionierten
   Vorfahren – waere ein Pin-Punkt in einer eigenen position:absolute-
   Zeile verschachtelt, ginge deren Eigen-Versatz (top/left der Zeile) bei
   der Berechnung verloren und Verbindungen wuerden nicht am tatsaechlichen
   Anschlusspunkt andocken. Layer ist daher die EINZIGE positionierte
   Ebene zwischen Element und Punkt. */
function buildIndividualPinsLayer(el, portCount) {
  const layer = document.createElement("div");
  layer.className = "individual-pins-layer";

  const bySide = { top: [], bottom: [], left: [], right: [] };
  for (let i = 0; i < portCount; i++) {
    bySide[getPinSide(el, i)].push(i);
  }

  const margin = 12;
  const half = PORT_DOT / 2;

  for (const side of PORT_SIDES) {
    const indices = bySide[side];
    const n = indices.length;
    if (n === 0) continue;
    indices.forEach((pinIndex, posInSide) => {
      const dot = createPinDot(el, pinIndex, "a", side);
      dot.classList.add("individual-pin-dot");
      const frac = (posInSide + 0.5) / n;
      if (side === "bottom" || side === "top") {
        const x = margin + frac * Math.max(DEFAULT_ELEMENT_W - 2 * margin, 1);
        dot.style.left = (x - half) + "px";
        dot.style.top = (side === "bottom" ? DEFAULT_ELEMENT_H - half : -half) + "px";
      } else {
        const y = margin + frac * Math.max(DEFAULT_ELEMENT_H - 2 * margin, 1);
        dot.style.top = (y - half) + "px";
        dot.style.left = (side === "right" ? DEFAULT_ELEMENT_W - half : -half) + "px";
      }
      layer.appendChild(dot);
    });
  }
  return layer;
}

/* Rotiert bei individuell platzierten Pins (Platine/Raspberry Pi) ALLE
   Pins gemeinsam um eine Seite weiter (gleiche Reihenfolge wie
   rotatePorts: unten -> links -> oben -> rechts), statt jeden Pin einzeln
   manuell umzustellen. */
function rotateIndividualPins(id) {
  const el = config.elements.find((x) => x.id === id);
  if (!el) return;
  const n = getPortCount(el);
  const sides = Array.from({ length: n }, (_, i) => getPinSide(el, i));
  el.pin_sides = sides.map((side) => PORT_SIDES[(PORT_SIDES.indexOf(side) + 1) % PORT_SIDES.length]);
  renderElements();
  renderConnections();
  persistConfig();
}

function buildElementNode(el) {
  const def = ELEMENT_TYPES[el.type] || ELEMENT_TYPES.generic;
  const node = document.createElement("div");
  node.className = "net-element";
  node.dataset.id = el.id;
  node.style.left = el.x + "px";
  node.style.top = el.y + "px";
  if (selectedElementIds.has(el.id)) node.classList.add("multi-selected");
  if (highlightedLocation) {
    node.classList.add(el.location === highlightedLocation ? "location-highlighted" : "location-dimmed");
  }

  const elLinks = normalizeLinks(el.links);
  const portCount = getPortCount(el);
  const individual = hasIndividualPinPlacement(el.type);
  const side = getPortSide(el);
  const mirrored = getPortMirror(el);
  const dual = portCount > 0 && !individual && hasDualSides(el.type);
  const axis = sideAxis(side);
  const hostDisplay = getElementHost(el);
  const word = portWord(el.type);
  const wordPlural = portWordPlural(el.type);

  if (portCount > 0 && !individual) {
    node.classList.add("has-ports", "axis-" + axis);
    if (mirrored) node.classList.add("mirrored");
  } else if (portCount > 0 && individual) {
    node.classList.add("has-ports", "has-individual-pins");
  }

  const body = document.createElement("div");
  body.className = "el-body";
  body.innerHTML = `
    <div class="el-head">
      <div class="el-icon" style="color:${def.color}">${getElementIconMarkup(el, def)}</div>
      <div>
        <div class="el-name">${escapeHtml(el.name || "(ohne Namen)")}</div>
        <div class="el-type">${def.label}</div>
      </div>
    </div>
    <div class="el-location">${escapeHtml(el.location || "")}</div>
    ${hostDisplay ? `<div class="el-ip" title="Eingestellte IP / Adresse">IP: ${escapeHtml(hostDisplay)}</div>` : ""}
  `;
  node.appendChild(body);

  if (el.location) {
    const locationEl = body.querySelector(".el-location");
    locationEl.classList.add("el-location-clickable");
    locationEl.title = "Klick: alle Elemente am Standort „" + el.location + "\" hervorheben";
    locationEl.addEventListener("mousedown", (e) => e.stopPropagation());
    locationEl.addEventListener("click", (e) => {
      e.stopPropagation();
      highlightedLocation = highlightedLocation === el.location ? null : el.location;
      renderElements();
    });
  }

  if (elLinks.length > 0) {
    const linksWrap = document.createElement("div");
    linksWrap.className = "el-links";
    elLinks.forEach((link, i) => {
      const btn = document.createElement("button");
      btn.className = "el-link-btn";
      btn.textContent = getLinkIcon(link.url) + " " + (link.label || "Webseite " + (i + 1));
      btn.title = getLinkScheme(link.url) === "rdp"
        ? link.url + " – laedt eine .rdp-Datei herunter (Windows-Remotedesktopverbindung)"
        : getLinkScheme(link.url) === "mqtt"
        ? "Sendet beim Klick eine MQTT-Nachricht an " + link.url + (link.topic ? " (Topic: " + link.topic + ")" : "")
        : link.url;
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        openLink(link);
      });
      linksWrap.appendChild(btn);
    });
    body.appendChild(linksWrap);
  }

  if (mode === "edit") {
    const controls = document.createElement("div");
    controls.className = "el-controls";

    const editBtn = document.createElement("div");
    editBtn.className = "el-ctrl-btn";
    editBtn.textContent = "✎";
    editBtn.title = "Bearbeiten";
    editBtn.addEventListener("mousedown", (e) => e.stopPropagation());
    editBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      openElementModal(el.id);
    });
    controls.appendChild(editBtn);

    if (portCount > 0 && !individual) {
      const rotateBtn = document.createElement("div");
      rotateBtn.className = "el-ctrl-btn";
      rotateBtn.textContent = "⟳";
      rotateBtn.title = dual
        ? wordPlural + " auf naechstes Seitenpaar drehen (aktuell: " + sideLabel(side) + " + " + sideLabel(OPPOSITE_SIDE[side]) + ")"
        : wordPlural + " auf naechste Seite drehen (aktuell: " + sideLabel(side) + ")";
      rotateBtn.addEventListener("mousedown", (e) => e.stopPropagation());
      rotateBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        rotatePorts(el.id);
      });
      controls.appendChild(rotateBtn);

      const mirrorBtn = document.createElement("div");
      mirrorBtn.className = "el-ctrl-btn" + (mirrored ? " active" : "");
      mirrorBtn.textContent = "⇋";
      mirrorBtn.title = wordPlural + "-Reihenfolge spiegeln";
      mirrorBtn.addEventListener("mousedown", (e) => e.stopPropagation());
      mirrorBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        mirrorPorts(el.id);
      });
      controls.appendChild(mirrorBtn);
    } else if (portCount > 0 && individual) {
      const rotateBtn = document.createElement("div");
      rotateBtn.className = "el-ctrl-btn";
      rotateBtn.textContent = "⟳";
      rotateBtn.title = wordPlural + " gemeinsam um eine Seite weiterdrehen (unten → links → oben → rechts)";
      rotateBtn.addEventListener("mousedown", (e) => e.stopPropagation());
      rotateBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        rotateIndividualPins(el.id);
      });
      controls.appendChild(rotateBtn);
    }

    body.appendChild(controls);
  }

  node.addEventListener("mousedown", (e) => {
    if (e.target.closest(".el-link-btn") || e.target.closest(".el-ctrl-btn")) return;
    if (mode === "edit" && !connectMode) {
      startDraggingElement(el.id, node, e);
    }
  });

  if (portCount > 0 && individual) {
    /* Platine/Raspberry Pi: jeder Pin wird einzeln, je nach zugewiesener
       Seite, absolut positioniert (siehe buildIndividualPinsLayer) statt in
       einem gemeinsamen Riegel. */
    node.appendChild(buildIndividualPinsLayer(el, portCount));
  } else if (portCount > 0) {
    /* Elemente mit Ports/Pins: Verbindungen duerfen nur an einem konkreten
       Andockpunkt gestartet/beendet werden, nicht am Element selbst.
       Bei Klemmleisten/Patchfeldern (hasDualSides) gibt es zusaetzlich eine
       zweite, identisch nummerierte/benannte Reihe auf der
       gegenueberliegenden Seite (z. B. Vorder-/Rueckseite). */
    node.appendChild(buildPortsBar(el, side, "a", axis, mirrored, portCount));
    if (dual) {
      node.appendChild(buildPortsBar(el, OPPOSITE_SIDE[side], "b", axis, mirrored, portCount));
    }
  } else {
    node.addEventListener("click", (e) => {
      if (e.target.closest(".el-link-btn") || e.target.closest(".el-ctrl-btn")) return;
      if (mode === "edit" && connectMode) {
        handleConnectPick(el.id, null);
      }
    });
  }

  return node;
}

function sideLabel(side) {
  return { bottom: "unten", top: "oben", left: "links", right: "rechts" }[side] || side;
}

/* ------------------------------------------------------------------ */
/* Portnamen per Doppelklick auf einen Port direkt vergeben            */
/* ------------------------------------------------------------------ */

let portNameInputEl = null;

function openPortNameEditor(el, portIndex, clientX, clientY) {
  closePortNameEditor();

  const input = document.createElement("input");
  input.type = "text";
  input.className = "port-name-input";
  input.maxLength = 40;
  input.placeholder = "Name fuer " + portWord(el.type) + " " + (portIndex + 1);
  input.value = getPortName(el, portIndex) || "";

  document.body.appendChild(input);
  const w = 180;
  const vw = window.innerWidth, vh = window.innerHeight;
  const left = Math.min(Math.max(8, clientX - w / 2), vw - w - 8);
  const top = Math.min(Math.max(8, clientY - 34), vh - 40);
  input.style.left = left + "px";
  input.style.top = top + "px";
  input.style.width = w + "px";

  input.focus();
  input.select();

  let done = false;
  const commit = () => {
    if (done) return;
    done = true;
    if (!Array.isArray(el.port_names)) el.port_names = [];
    el.port_names[portIndex] = input.value.trim();
    closePortNameEditor();
    renderElements();
    renderConnections();
    persistConfig();
  };
  const cancel = () => {
    if (done) return;
    done = true;
    closePortNameEditor();
  };

  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); commit(); }
    else if (e.key === "Escape") { e.preventDefault(); cancel(); }
  });
  input.addEventListener("blur", commit);
  input.addEventListener("mousedown", (e) => e.stopPropagation());
  input.addEventListener("click", (e) => e.stopPropagation());

  portNameInputEl = input;
}

function closePortNameEditor() {
  if (portNameInputEl) {
    portNameInputEl.remove();
    portNameInputEl = null;
  }
}

function rotatePorts(id) {
  const el = config.elements.find((x) => x.id === id);
  if (!el) return;
  const current = getPortSide(el);
  const idx = PORT_SIDES.indexOf(current);
  el.port_side = PORT_SIDES[(idx + 1) % PORT_SIDES.length];
  renderElements();
  renderConnections();
  persistConfig();
}

function mirrorPorts(id) {
  const el = config.elements.find((x) => x.id === id);
  if (!el) return;
  el.port_mirror = !getPortMirror(el);
  renderElements();
  renderConnections();
  persistConfig();
}

/* Berechnet fuer jedes Element mit Ports die Position jedes Port-Andockpunkts
   relativ zur linken oberen Ecke des Elements (in unskalierten Canvas-Pixeln).
   Muss nach jedem Neu-Rendern der Elemente aufgerufen werden. */
function computePortRelOffsets() {
  portRelOffsets = {};
  elementLayer.querySelectorAll(".net-element").forEach((node) => {
    const dotsA = node.querySelectorAll('.port-dot[data-side="a"]');
    const dotsB = node.querySelectorAll('.port-dot[data-side="b"]');
    if (dotsA.length === 0 && dotsB.length === 0) return;
    const id = node.dataset.id;
    const toOffsets = (dots) => Array.from(dots).map((dot) => ({
      x: dot.offsetLeft + dot.offsetWidth / 2,
      y: dot.offsetTop + dot.offsetHeight / 2,
    }));
    portRelOffsets[id] = { a: toOffsets(dotsA), b: toOffsets(dotsB) };
  });
}

function escapeHtml(str) {
  const d = document.createElement("div");
  d.textContent = str ?? "";
  return d.innerHTML;
}

/* Extrahiert Host/IP aus der ersten hinterlegten Webseite eines Elements,
   damit die eingestellte IP direkt am Element sichtbar ist (ohne den
   Bearbeiten-Dialog oeffnen zu muessen). Funktioniert mit vollstaendigen
   URLs (https://192.168.1.2/admin) ebenso wie mit reinen Host-/IP-Angaben
   ohne Schema (192.168.1.2). */
/* Wandelt die Links eines Elements in ein einheitliches Format
   { label, url, topic?, payload? } um. Unterstuetzt sowohl das alte Format
   (Array aus reinen URL-Strings) als auch das neue Format, damit
   bestehende config.json-Dateien weiterhin funktionieren. topic/payload
   sind nur bei mqtt://-Eintraegen gesetzt (siehe openLink/publishMqttLink). */
function normalizeLinks(links) {
  if (!Array.isArray(links)) return [];
  return links
    .map((l) => {
      if (typeof l === "string") return { label: "", url: l.trim() };
      if (l && typeof l === "object") {
        const out = { label: (l.label || "").trim(), url: (l.url || "").trim() };
        if (typeof l.topic === "string" && l.topic.trim()) out.topic = l.topic.trim();
        if (typeof l.payload === "string" && l.payload) out.payload = l.payload;
        return out;
      }
      return null;
    })
    .filter((l) => l && l.url);
}

/* Ermittelt das URL-Schema (http, https, rdp, vnc, ssh, mqtt, ...) einer
   Adresse. */
function getLinkScheme(url) {
  const m = (url || "").match(/^([a-zA-Z][a-zA-Z0-9+.-]*):/);
  return m ? m[1].toLowerCase() : "";
}

/* Passendes Icon je nach Protokoll fuer die Schaltflaeche am Element. */
function getLinkIcon(url) {
  const scheme = getLinkScheme(url);
  if (scheme === "rdp") return "🖥";
  if (scheme === "vnc") return "🖵";
  if (scheme === "ssh" || scheme === "telnet") return "⌘";
  if (scheme === "mqtt") return "📡";
  return "↗";
}

/* Oeffnet eine hinterlegte Adresse bzw. loest die hinterlegte Aktion aus.
   `link` ist entweder das normalisierte {label,url,topic?,payload?}-Objekt
   oder (Legacy-Aufrufe) ein reiner URL-String.
   - http(s): oeffnet einen neuen Tab.
   - rdp: Windows registriert "rdp://" standardmaessig NICHT als
     Protokoll, ein einfacher Link-Klick fuehrt dort also zu nichts.
     Stattdessen wird eine echte .rdp-Datei (Remotedesktopverbindung)
     erzeugt und heruntergeladen. Diese Datei enthaelt bereits die
     Ziel-IP; ein Doppelklick auf die heruntergeladene Datei oeffnet
     automatisch die Windows-Remotedesktopverbindung (mstsc) mit
     vorausgefuellter Zieladresse – ein zusaetzlicher Klick des Nutzers
     ist dabei unumgaenglich, da Browser aus Sicherheitsgruenden keine
     heruntergeladenen Dateien selbststaendig ausfuehren duerfen.
   - mqtt: sendet ueber den Server (POST /api/mqtt/publish) eine MQTT-
     Nachricht an Host/Topic aus der hinterlegten Adresse, mit dem
     hinterlegten Payload (siehe publishMqttLink). Laeuft serverseitig,
     da Browser aus Sicherheitsgruenden keine rohen TCP-Verbindungen zu
     einem MQTT-Broker aufbauen koennen.
   - andere Protokolle (vnc://, ssh://, ...): werden ueber einen
     unsichtbaren Link-Klick ausgeloest, sofern im Betriebssystem/Browser
     ein passender Handler dafuer registriert ist (z. B. durch einen
     installierten VNC-/SSH-Client). */
function openLink(link) {
  const linkObj = typeof link === "string" ? { url: link } : (link || {});
  const url = linkObj.url || "";
  const scheme = getLinkScheme(url);
  if (scheme === "mqtt") {
    publishMqttLink(linkObj);
    return;
  }
  if (scheme === "http" || scheme === "https" || scheme === "") {
    window.open(url, "_blank", "noopener");
    return;
  }
  if (scheme === "rdp") {
    downloadRdpFile(url);
    return;
  }
  try {
    const a = document.createElement("a");
    a.href = url;
    a.rel = "noopener";
    a.style.display = "none";
    document.body.appendChild(a);
    a.click();
    a.remove();
  } catch (e) {
    window.open(url, "_blank", "noopener");
  }
}

/* Sendet eine MQTT-Nachricht ueber den Server (paho-mqtt, siehe app.py).
   Adresse hat die Form "mqtt://host:port" (Port optional, Standard 1883);
   Topic und Payload kommen aus den zusaetzlichen Link-Feldern (siehe
   Link-Editor im Element-Dialog). */
function publishMqttLink(link) {
  const withoutScheme = (link.url || "").replace(/^mqtt:\/\//i, "").replace(/\/+$/, "");
  const [hostPart] = withoutScheme.split("/");
  const [host, portStr] = (hostPart || "").split(":");
  const port = parseInt(portStr, 10) || 1883;
  const topic = (link.topic || "").trim();
  const payload = link.payload || "";

  if (!host || !topic) {
    showToast("⚠ MQTT: Broker-Host und Topic muessen gesetzt sein (im Element-Dialog bearbeiten).", 6000);
    return;
  }

  setStatus("Sende MQTT-Nachricht an " + topic + " …");
  fetch("/api/mqtt/publish", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ host, port, topic, payload }),
  })
    .then(async (res) => {
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.status !== "ok") {
        throw new Error((data && data.message) || ("HTTP " + res.status));
      }
      setStatus("MQTT-Nachricht an " + topic + " gesendet.");
      showToast("✓ MQTT-Nachricht gesendet (" + topic + ").", 4000);
    })
    .catch((err) => {
      setStatus("Fehler beim MQTT-Versand.");
      showToast("⚠ MQTT-Versand fehlgeschlagen: " + err.message, 6500);
    });
}

/* Erzeugt aus einer rdp://-Adresse eine echte .rdp-Datei (Format der
   Windows-Remotedesktopverbindung) und stoesst deren Download an. Die
   Zieladresse (inkl. optionalem Port, z. B. rdp://192.168.1.10:3390)
   wird dabei direkt in die Datei uebernommen. */
function downloadRdpFile(url) {
  let target = (url || "").replace(/^rdp:\/\//i, "").replace(/\/+$/, "");
  if (!target) target = url;
  const rdpContent =
    "full address:s:" + target + "\r\n" +
    "prompt for credentials:i:1\r\n" +
    "authentication level:i:2\r\n" +
    "screen mode id:i:2\r\n";

  const blob = new Blob([rdpContent], { type: "application/x-rdp" });
  const blobUrl = URL.createObjectURL(blob);
  const fileNameBase = (target.split(":")[0] || "verbindung").replace(/[^a-zA-Z0-9._-]/g, "_");

  const a = document.createElement("a");
  a.href = blobUrl;
  a.download = fileNameBase + ".rdp";
  a.style.display = "none";
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(blobUrl), 4000);

  setStatus("RDP-Datei fuer " + target + " heruntergeladen.");
  showToast(
    "⬇ RDP-Datei heruntergeladen (" + fileNameBase + ".rdp). " +
    "Zum Verbinden bitte einmal öffnen – Browser dürfen Downloads aus " +
    "Sicherheitsgründen nicht automatisch ausführen.",
    7000
  );
}

function getElementHost(el) {
  const first = normalizeLinks(el.links)[0];
  if (!first) return "";
  try {
    return new URL(first.url).hostname;
  } catch (e) {
    const m = first.url.match(/^[a-zA-Z][a-zA-Z0-9+.-]*:\/\/([^/:?#]+)/) || first.url.match(/^([^/:?#\s]+)/);
    return m ? m[1] : "";
  }
}

/* ------------------------------------------------------------------ */
/* Elemente: Hinzufuegen / Verschieben / Bearbeiten / Loeschen         */
/* ------------------------------------------------------------------ */

function addElement(type) {
  const rect = viewport.getBoundingClientRect();
  const centerX = (rect.width / 2 - panX) / scale - DEFAULT_ELEMENT_W / 2;
  const centerY = (rect.height / 2 - panY) / scale - DEFAULT_ELEMENT_H / 2;

  const el = {
    id: "el-" + Date.now() + "-" + Math.floor(Math.random() * 1000),
    type,
    name: ELEMENT_TYPES[type].label + " neu",
    location: "",
    x: snap(Math.max(0, centerX)),
    y: snap(Math.max(0, centerY)),
    links: [],
  };
  if (type === "relay") {
    el.relay_type = "schliesser";
    el.ports = RELAY_TYPES.schliesser.pinCount;
    el.port_names = RELAY_TYPES.schliesser.names.slice();
  } else if (type === "motor") {
    el.motor_type = "dc_ac";
    el.ports = MOTOR_TYPES.dc_ac.pinCount;
    el.port_names = MOTOR_TYPES.dc_ac.names.slice();
  } else if (hasPorts(type) && DEFAULT_PORTS[type] > 0) {
    el.ports = DEFAULT_PORTS[type];
  }
  config.elements.push(el);
  renderElements();
  renderConnections();
  persistConfig();
  openElementModal(el.id);
}

function snap(value) {
  if (!$("#chkSnap").checked) return Math.round(value);
  const size = config.view?.grid_size || 40;
  return Math.round(value / size) * size;
}

function startDraggingElement(id, node, e) {
  const el = config.elements.find((x) => x.id === id);
  if (!el) return;

  const isGroupDrag = selectedElementIds.size > 1 && selectedElementIds.has(id);

  if (isGroupDrag) {
    const nodes = {};
    const startPositions = {};
    selectedElementIds.forEach((gid) => {
      const gEl = config.elements.find((x) => x.id === gid);
      const gNode = elementLayer.querySelector(`.net-element[data-id="${gid}"]`);
      if (gEl && gNode) {
        nodes[gid] = gNode;
        startPositions[gid] = { x: gEl.x, y: gEl.y };
        gNode.classList.add("dragging");
      }
    });

    // Verbindungen, deren beide Enden innerhalb der Auswahl liegen, werden
    // beim Verschieben starr mitgenommen (inkl. Wegpunkte und Bezeichnung),
    // damit ihre Form/Linienfuehrung erhalten bleibt.
    const idSet = new Set(Object.keys(nodes));
    const connSnapshots = {};
    config.connections.forEach((c) => {
      if (idSet.has(c.from) && idSet.has(c.to)) {
        connSnapshots[c.id] = {
          waypoints: Array.isArray(c.waypoints) ? c.waypoints.map((wp) => ({ x: wp.x, y: wp.y })) : [],
          label_at: c.label_at ? { x: c.label_at.x, y: c.label_at.y } : null,
        };
      }
    });

    dragGroup = {
      ids: Object.keys(nodes),
      nodes,
      startPositions,
      startPointerCanvas: clientToCanvas(e.clientX, e.clientY),
      connSnapshots,
    };
  } else {
    if (selectedElementIds.size > 0) {
      elementLayer.querySelectorAll(".net-element.multi-selected").forEach((n) => n.classList.remove("multi-selected"));
      selectedElementIds.clear();
    }
    dragGroup = null;
    node.classList.add("dragging");
  }

  draggingEl = { id, node };
  const rect = node.getBoundingClientRect();
  dragOffset.x = (e.clientX - rect.left) / scale;
  dragOffset.y = (e.clientY - rect.top) / scale;
  e.stopPropagation();
}

function moveDraggingElement(e) {
  if (dragGroup) {
    moveDragGroup(e);
    return;
  }
  const el = config.elements.find((x) => x.id === draggingEl.id);
  if (!el) return;
  const rect = viewport.getBoundingClientRect();
  const x = (e.clientX - rect.left - panX) / scale - dragOffset.x;
  const y = (e.clientY - rect.top - panY) / scale - dragOffset.y;
  el.x = Math.max(0, x);
  el.y = Math.max(0, y);
  draggingEl.node.style.left = el.x + "px";
  draggingEl.node.style.top = el.y + "px";
  renderConnections();
}

function moveDragGroup(e) {
  const pt = clientToCanvas(e.clientX, e.clientY);
  const dx = pt.x - dragGroup.startPointerCanvas.x;
  const dy = pt.y - dragGroup.startPointerCanvas.y;
  dragGroup.ids.forEach((gid) => {
    const gEl = config.elements.find((x) => x.id === gid);
    const start = dragGroup.startPositions[gid];
    const node = dragGroup.nodes[gid];
    if (!gEl || !start || !node) return;
    gEl.x = Math.max(0, start.x + dx);
    gEl.y = Math.max(0, start.y + dy);
    node.style.left = gEl.x + "px";
    node.style.top = gEl.y + "px";
  });

  // Wegpunkte/Bezeichnung der vollstaendig innerhalb der Auswahl liegenden
  // Verbindungen starr mitverschieben, damit ihre Form erhalten bleibt.
  Object.keys(dragGroup.connSnapshots).forEach((connId) => {
    const conn = config.connections.find((c) => c.id === connId);
    const snap = dragGroup.connSnapshots[connId];
    if (!conn || !snap) return;
    conn.waypoints = snap.waypoints.map((wp) => ({ x: wp.x + dx, y: wp.y + dy }));
    if (snap.label_at) {
      conn.label_at = { x: snap.label_at.x + dx, y: snap.label_at.y + dy };
    }
  });

  renderConnections();
}

function finishDraggingElement() {
  if (dragGroup) {
    dragGroup.ids.forEach((gid) => {
      const gEl = config.elements.find((x) => x.id === gid);
      const node = dragGroup.nodes[gid];
      if (!gEl || !node) return;
      gEl.x = snap(gEl.x);
      gEl.y = snap(gEl.y);
      node.style.left = gEl.x + "px";
      node.style.top = gEl.y + "px";
      node.classList.remove("dragging");
    });
    dragGroup = null;
    draggingEl = null;
    renderConnections();
    persistConfig();
    return;
  }

  const el = config.elements.find((x) => x.id === draggingEl.id);
  if (el) {
    el.x = snap(el.x);
    el.y = snap(el.y);
    draggingEl.node.style.left = el.x + "px";
    draggingEl.node.style.top = el.y + "px";
  }
  draggingEl.node.classList.remove("dragging");
  draggingEl = null;
  renderConnections();
  persistConfig();
}

let pendingPortNames = [];
let pendingPinSides = [];
let pendingPinKinds = [];

/* Aktualisiert Sichtbarkeit/Beschriftung der Anschluss-Felder im
   Element-Dialog abhaengig vom gewaehlten Typ: normale Elemente mit
   Ports/Pins zeigen ein Anzahl-Feld; Relay/Motor zeigen stattdessen eine
   Kontaktart-/Motorart-Auswahl (Anzahl wird daraus automatisch abgeleitet);
   Platine/Raspberry Pi (individuelle Platzierung) zeigen zusaetzlich eine
   Seiten-Auswahl je Anschluss und einen "+ Anschluss hinzufuegen"-Button
   statt eines festen Anzahl-Felds. */
function updatePortsFieldVisibility() {
  const type = $("#fType").value;
  const row = $("#fPortsRow");
  const namesRow = $("#fPortNamesRow");
  const relayRow = $("#fRelayTypeRow");
  const motorRow = $("#fMotorTypeRow");
  const addPinBtn = $("#fAddPin");
  const portsInput = $("#fPorts");

  relayRow.classList.toggle("hidden-field", type !== "relay");
  motorRow.classList.toggle("hidden-field", type !== "motor");

  if (!hasPorts(type)) {
    row.classList.add("hidden-field");
    namesRow.classList.add("hidden-field");
    return;
  }

  namesRow.classList.remove("hidden-field");
  $("#fPortsLabel").textContent = "Anzahl " + portWordPlural(type);
  $("#fPortNamesLabel").textContent = portWordPlural(type) + "namen (optional, zusaetzlich zur Nummer)";

  if (type === "relay" || type === "motor") {
    // Anzahl ergibt sich automatisch aus der Kontakt-/Motorart, kein
    // manuelles Anzahl-Feld noetig.
    row.classList.add("hidden-field");
    addPinBtn.classList.add("hidden-field");
    if (!$("#fPorts").value) $("#fPorts").value = DEFAULT_PORTS[type];
    resizePendingPortNames();
    renderPortNameInputs();
    return;
  }

  const individual = hasIndividualPinPlacement(type);
  if (individual) {
    // Platine/Raspberry Pi: keine feste Anzahl vorgeben, Pins werden ueber
    // "+ Anschluss hinzufuegen" individuell ergaenzt/entfernt.
    row.classList.add("hidden-field");
    addPinBtn.classList.remove("hidden-field");
  } else {
    row.classList.remove("hidden-field");
    addPinBtn.classList.add("hidden-field");
    portsInput.min = String(getMinPorts(type));
    if (!$("#fPorts").value) $("#fPorts").value = DEFAULT_PORTS[type];
  }
  resizePendingPortNames();
  renderPortNameInputs();
}

function resizePendingPortNames() {
  const type = $("#fType").value;
  const individual = hasIndividualPinPlacement(type);
  let n;
  if (type === "relay") {
    n = RELAY_TYPES[$("#fRelayType").value] ? RELAY_TYPES[$("#fRelayType").value].pinCount : RELAY_TYPES.schliesser.pinCount;
  } else if (type === "motor") {
    n = MOTOR_TYPES[$("#fMotorType").value] ? MOTOR_TYPES[$("#fMotorType").value].pinCount : MOTOR_TYPES.dc_ac.pinCount;
  } else if (individual) {
    // Anzahl wird ausschliesslich ueber +/- Buttons gesteuert.
    n = pendingPortNames.length;
  } else {
    n = parseInt($("#fPorts").value, 10);
    if (!Number.isFinite(n)) n = pendingPortNames.length || DEFAULT_PORTS[type] || getMinPorts(type);
    n = Math.min(PORT_MAX, Math.max(getMinPorts(type), n));
    $("#fPorts").value = n;
  }
  const nextNames = [], nextSides = [], nextKinds = [];
  for (let i = 0; i < n; i++) {
    nextNames.push(pendingPortNames[i] || "");
    nextSides.push(pendingPinSides[i] || ["bottom", "right", "top", "left"][i % 4]);
    nextKinds.push(pendingPinKinds[i] || "pin");
  }
  pendingPortNames = nextNames;
  pendingPinSides = nextSides;
  pendingPinKinds = nextKinds;
}

function renderPortNameInputs() {
  const type = $("#fType").value;
  const individual = hasIndividualPinPlacement(type);
  const showKind = type === "raspberry_pi";
  const list = $("#fPortNamesList");
  list.innerHTML = "";
  pendingPortNames.forEach((name, i) => {
    const row = document.createElement("div");
    row.className = "port-name-row" + (individual ? " port-name-row-individual" : "");
    const idx = document.createElement("span");
    idx.className = "port-name-idx";
    idx.textContent = "P" + (i + 1);
    const input = document.createElement("input");
    input.type = "text";
    input.maxLength = 40;
    input.placeholder = portWord(type) + " " + (i + 1);
    input.value = name;
    input.addEventListener("input", () => { pendingPortNames[i] = input.value; });
    row.appendChild(idx);
    row.appendChild(input);

    if (showKind) {
      const kindSelect = document.createElement("select");
      kindSelect.className = "pin-kind-select";
      kindSelect.title = "Anschlussart";
      [["pin", "Pin"], ["usb", "USB"], ["lan", "LAN"]].forEach(([val, txt]) => {
        const o = document.createElement("option");
        o.value = val; o.textContent = txt;
        kindSelect.appendChild(o);
      });
      kindSelect.value = pendingPinKinds[i] || "pin";
      kindSelect.addEventListener("change", () => { pendingPinKinds[i] = kindSelect.value; });
      row.appendChild(kindSelect);
    }

    if (individual) {
      const sideSelect = document.createElement("select");
      sideSelect.className = "pin-side-select";
      sideSelect.title = "Seite dieses Anschlusses";
      [["bottom", "unten"], ["top", "oben"], ["left", "links"], ["right", "rechts"]].forEach(([val, txt]) => {
        const o = document.createElement("option");
        o.value = val; o.textContent = txt;
        sideSelect.appendChild(o);
      });
      sideSelect.value = pendingPinSides[i] || "bottom";
      sideSelect.addEventListener("change", () => { pendingPinSides[i] = sideSelect.value; });
      row.appendChild(sideSelect);

      const removeBtn = document.createElement("button");
      removeBtn.type = "button";
      removeBtn.className = "link-edit-remove";
      removeBtn.title = "Diesen Anschluss entfernen";
      removeBtn.textContent = "✕";
      removeBtn.addEventListener("click", () => {
        pendingPortNames.splice(i, 1);
        pendingPinSides.splice(i, 1);
        pendingPinKinds.splice(i, 1);
        renderPortNameInputs();
      });
      row.appendChild(removeBtn);
    }

    list.appendChild(row);
  });
}

$("#fPorts").addEventListener("input", () => {
  resizePendingPortNames();
  renderPortNameInputs();
});
$("#fRelayType").addEventListener("change", () => {
  const rt = RELAY_TYPES[$("#fRelayType").value] || RELAY_TYPES.schliesser;
  pendingPortNames = rt.names.slice();
  renderPortNameInputs();
});
$("#fMotorType").addEventListener("change", () => {
  const mt = MOTOR_TYPES[$("#fMotorType").value] || MOTOR_TYPES.dc_ac;
  pendingPortNames = mt.names.slice();
  renderPortNameInputs();
});
$("#fAddPin").addEventListener("click", () => {
  pendingPortNames.push("");
  pendingPinSides.push(["bottom", "right", "top", "left"][pendingPortNames.length % 4]);
  pendingPinKinds.push("pin");
  renderPortNameInputs();
});

/* ------------------------------------------------------------------ */
/* Link-Editor im Element-Dialog: Bezeichnung + URL je Zeile           */
/* ------------------------------------------------------------------ */

let pendingLinks = []; // [{label, url}, ...]

function renderLinksEditor() {
  const list = $("#fLinksList");
  list.innerHTML = "";
  pendingLinks.forEach((link, i) => {
    const row = document.createElement("div");
    row.className = "link-edit-row";

    // --- Obere Zeile: Bezeichnung + Entfernen-Button ---
    const topRow = document.createElement("div");
    topRow.className = "link-edit-top";

    const labelInput = document.createElement("input");
    labelInput.type = "text";
    labelInput.className = "link-edit-label";
    labelInput.maxLength = 40;
    labelInput.placeholder = "Bezeichnung (z. B. Admin, Grafana, Remotedesktop)";
    labelInput.value = link.label || "";
    labelInput.addEventListener("input", () => { pendingLinks[i].label = labelInput.value; });

    const removeBtn = document.createElement("button");
    removeBtn.type = "button";
    removeBtn.className = "link-edit-remove";
    removeBtn.title = "Diese Webseite entfernen";
    removeBtn.textContent = "✕";
    removeBtn.addEventListener("click", () => {
      pendingLinks.splice(i, 1);
      renderLinksEditor();
    });

    topRow.appendChild(labelInput);
    topRow.appendChild(removeBtn);

    // --- Untere Zeile: Protokoll-Auswahl + URL (bekommt den meisten Platz) ---
    const bottomRow = document.createElement("div");
    bottomRow.className = "link-edit-bottom";

    const urlInput = document.createElement("input");
    urlInput.type = "text";
    urlInput.className = "link-edit-url";
    urlInput.placeholder = "https://192.168.1.2/admin";
    urlInput.value = link.url || "";
    urlInput.addEventListener("input", () => { pendingLinks[i].url = urlInput.value; });
    urlInput.addEventListener("blur", () => {
      // Zeigt/versteckt die Topic/Payload-Felder, falls das Schema per Hand
      // (nicht ueber die Schnellauswahl) auf mqtt:// geaendert wurde.
      renderLinksEditor();
    });

    const schemeSelect = document.createElement("select");
    schemeSelect.className = "link-edit-scheme";
    schemeSelect.title = "Protokoll-Schnellauswahl";
    [
      { value: "https://", text: "Web" },
      { value: "rdp://", text: "RDP" },
      { value: "vnc://", text: "VNC" },
      { value: "ssh://", text: "SSH" },
      { value: "mqtt://", text: "MQTT" },
      { value: "", text: "…" },
    ].forEach((opt) => {
      const o = document.createElement("option");
      o.value = opt.value;
      o.textContent = opt.text;
      schemeSelect.appendChild(o);
    });
    const currentScheme = (link.url || "").match(/^[a-zA-Z][a-zA-Z0-9+.-]*:\/\//);
    schemeSelect.value = currentScheme ? currentScheme[0] : "";
    schemeSelect.addEventListener("change", () => {
      if (!schemeSelect.value) return;
      const withoutScheme = (urlInput.value || "").replace(/^[a-zA-Z][a-zA-Z0-9+.-]*:\/\//, "");
      urlInput.value = schemeSelect.value + withoutScheme;
      pendingLinks[i].url = urlInput.value;
      urlInput.focus();
      renderLinksEditor();
    });

    bottomRow.appendChild(schemeSelect);
    bottomRow.appendChild(urlInput);

    row.appendChild(topRow);
    row.appendChild(bottomRow);

    // --- MQTT-Zeile: Broker-Adresse (oben) + Topic/Payload (nur bei
    //     mqtt://-Schema sichtbar) – beim Klick auf die Schaltflaeche wird
    //     dann keine URL geoeffnet, sondern ueber den Server eine
    //     MQTT-Nachricht an Topic mit Payload gesendet (siehe openLink). */
    if (getLinkScheme(link.url) === "mqtt") {
      const mqttRow = document.createElement("div");
      mqttRow.className = "link-edit-mqtt";

      const topicInput = document.createElement("input");
      topicInput.type = "text";
      topicInput.className = "link-edit-mqtt-topic";
      topicInput.placeholder = "Topic (z. B. schaltschrank1/relais1/set)";
      topicInput.value = link.topic || "";
      topicInput.addEventListener("input", () => { pendingLinks[i].topic = topicInput.value; });

      const payloadInput = document.createElement("input");
      payloadInput.type = "text";
      payloadInput.className = "link-edit-mqtt-payload";
      payloadInput.placeholder = "Payload (z. B. ON)";
      payloadInput.value = link.payload || "";
      payloadInput.addEventListener("input", () => { pendingLinks[i].payload = payloadInput.value; });

      mqttRow.appendChild(topicInput);
      mqttRow.appendChild(payloadInput);
      row.appendChild(mqttRow);
    }

    list.appendChild(row);
  });
}

$("#fAddLink").addEventListener("click", () => {
  pendingLinks.push({ label: "", url: "" });
  renderLinksEditor();
  const rows = $("#fLinksList").querySelectorAll(".link-edit-url");
  if (rows.length) rows[rows.length - 1].focus();
});

function openElementModal(id) {
  editingElementId = id;
  const el = config.elements.find((x) => x.id === id);
  if (!el) return;
  $("#elementModalTitle").textContent = "Element bearbeiten";
  $("#fName").value = el.name || "";
  $("#fLocation").value = el.location || "";
  populateLocationSuggestions();
  $("#fType").value = el.type;
  $("#fRelayType").value = getRelayType(el);
  $("#fMotorType").value = getMotorType(el);
  pendingLinks = normalizeLinks(el.links);
  renderLinksEditor();
  const n = hasPorts(el.type) ? getPortCount(el) : 0;
  $("#fPorts").value = n || "";
  pendingPortNames = Array.from({ length: n }, (_, i) => (el.port_names && el.port_names[i]) || "");
  pendingPinSides = Array.from({ length: n }, (_, i) => getPinSide(el, i));
  pendingPinKinds = Array.from({ length: n }, (_, i) => getPinKind(el, i));
  updatePortsFieldVisibility();
  $("#elementModal").classList.remove("hidden");
  $("#fName").focus();
}

/* Fuellt die Ortsvorschlaege (datalist) mit bereits im Plan verwendeten
   Standorten sowie ein paar generischen Vorschlaegen (z. B. fuer
   Schaltschraenke) – bewusst KEIN "Serverraum" mehr, da dieses Projekt
   kein Netzwerkplan mehr ist, sondern ein allgemeiner Verkabelungsplan. */
function populateLocationSuggestions() {
  const list = $("#fLocationSuggestions");
  const used = new Set(
    (config.elements || [])
      .map((e) => (e.location || "").trim())
      .filter(Boolean)
  );
  const defaults = ["Schaltschrank 1", "Schaltschrank 2", "Maschine A", "Feldebene"];
  defaults.forEach((d) => used.add(d));
  list.innerHTML = "";
  Array.from(used).sort().forEach((loc) => {
    const opt = document.createElement("option");
    opt.value = loc;
    list.appendChild(opt);
  });
}

$("#fType").addEventListener("change", updatePortsFieldVisibility);

$("#fCancel").addEventListener("click", () => $("#elementModal").classList.add("hidden"));

$("#fSave").addEventListener("click", () => {
  const el = config.elements.find((x) => x.id === editingElementId);
  if (!el) return;
  el.name = $("#fName").value.trim() || "(ohne Namen)";
  el.location = $("#fLocation").value.trim();
  el.type = $("#fType").value;
  el.links = pendingLinks
    .map((l) => ({
      label: (l.label || "").trim(),
      url: (l.url || "").trim(),
      topic: (l.topic || "").trim() || undefined,
      payload: (l.payload || "").trim() || undefined,
    }))
    .filter((l) => l.url);

  if (el.type === "relay") {
    el.relay_type = RELAY_TYPES[$("#fRelayType").value] ? $("#fRelayType").value : "schliesser";
    resizePendingPortNames();
    const n = RELAY_TYPES[el.relay_type].pinCount;
    el.ports = n;
    el.port_names = pendingPortNames.slice(0, n).map((s) => s.trim());
    delete el.pin_sides;
    delete el.pin_kinds;
    clampConnectionsToPortCount(el, n);
  } else if (el.type === "motor") {
    el.motor_type = MOTOR_TYPES[$("#fMotorType").value] ? $("#fMotorType").value : "dc_ac";
    resizePendingPortNames();
    const n = MOTOR_TYPES[el.motor_type].pinCount;
    el.ports = n;
    el.port_names = pendingPortNames.slice(0, n).map((s) => s.trim());
    delete el.pin_sides;
    delete el.pin_kinds;
    clampConnectionsToPortCount(el, n);
  } else if (hasIndividualPinPlacement(el.type)) {
    resizePendingPortNames();
    const n = pendingPortNames.length;
    el.ports = n;
    el.port_names = pendingPortNames.slice(0, n).map((s) => s.trim());
    el.pin_sides = pendingPinSides.slice(0, n);
    if (el.type === "raspberry_pi") {
      el.pin_kinds = pendingPinKinds.slice(0, n);
    } else {
      delete el.pin_kinds;
    }
    clampConnectionsToPortCount(el, n);
  } else if (hasPorts(el.type)) {
    let n = parseInt($("#fPorts").value, 10);
    if (!Number.isFinite(n)) n = DEFAULT_PORTS[el.type];
    n = Math.min(PORT_MAX, Math.max(getMinPorts(el.type), n));
    el.ports = n;
    resizePendingPortNames();
    el.port_names = pendingPortNames.slice(0, n).map((s) => s.trim());
    delete el.pin_sides;
    delete el.pin_kinds;
    clampConnectionsToPortCount(el, n);
  } else {
    delete el.ports;
    delete el.port_names;
    delete el.pin_sides;
    delete el.pin_kinds;
    delete el.relay_type;
    delete el.motor_type;
  }

  $("#elementModal").classList.add("hidden");
  renderElements();
  renderConnections();
  persistConfig();
});

/* Verbindungen, die auf nun nicht mehr existierende Ports/Pins zeigen,
   kappen (Verbindung bleibt bestehen, dockt dann am Element-Mittelpunkt
   an). */
function clampConnectionsToPortCount(el, n) {
  config.connections.forEach((c) => {
    if (c.from === el.id && c.from_port !== null && c.from_port !== undefined && c.from_port >= n) {
      c.from_port = null;
    }
    if (c.to === el.id && c.to_port !== null && c.to_port !== undefined && c.to_port >= n) {
      c.to_port = null;
    }
  });
}

$("#fDelete").addEventListener("click", () => {
  if (!confirm("Dieses Element inklusive aller Verbindungen loeschen?")) return;
  config.elements = config.elements.filter((x) => x.id !== editingElementId);
  config.connections = config.connections.filter(
    (c) => c.from !== editingElementId && c.to !== editingElementId
  );
  cleanupOrphanCables();
  $("#elementModal").classList.add("hidden");
  renderAll();
  persistConfig();
});

/* ------------------------------------------------------------------ */
/* Verbindungen                                                        */
/* ------------------------------------------------------------------ */

$("#newConnColor").addEventListener("input", (e) => {
  selectedColor = e.target.value;
});

$("#btnConnectMode").addEventListener("click", () => {
  connectMode = !connectMode;
  connectFrom = null;
  viewport.classList.toggle("connect-mode", connectMode);
  $("#btnConnectMode").classList.toggle("btn-primary", connectMode);
  clearConnectPickHighlight();
  setStatus(connectMode
    ? "Verbindungsmodus: Element anklicken – bei Elementen mit Anschlüssen einen konkreten Pin/Port anklicken."
    : "Bereit");
});

function portPickNode(id, port, side) {
  const node = elementLayer.querySelector(`.net-element[data-id="${id}"]`);
  if (!node) return null;
  if (port === null || port === undefined) return node;
  const sideKey = side === "b" ? "b" : "a";
  return node.querySelector(`.port-dot[data-port="${port}"][data-side="${sideKey}"]`);
}

function clearConnectPickHighlight() {
  $$(".net-element.connect-pick").forEach((n) => n.classList.remove("connect-pick"));
  $$(".port-dot.port-picked").forEach((n) => n.classList.remove("port-picked"));
}

function handleConnectPick(id, port, side) {
  const sideKey = side === "b" ? "b" : "a";
  const targetNode = portPickNode(id, port, sideKey);
  if (!targetNode) return;

  if (!connectFrom) {
    connectFrom = { id, port: port ?? null, side: sideKey };
    targetNode.classList.add(port === null || port === undefined ? "connect-pick" : "port-picked");
    setStatus("Zweiten Anschluss / zweites Element fuer die Verbindung anklicken.");
    return;
  }

  // Erneuter Klick auf denselben Startpunkt -> Auswahl aufheben
  if (connectFrom.id === id && (connectFrom.port ?? null) === (port ?? null) && connectFrom.side === sideKey) {
    clearConnectPickHighlight();
    connectFrom = null;
    return;
  }

  const conn = {
    id: "conn-" + Date.now() + "-" + Math.floor(Math.random() * 1000),
    from: connectFrom.id,
    to: id,
    from_port: connectFrom.port ?? null,
    from_port_side: connectFrom.side || "a",
    to_port: port ?? null,
    to_port_side: sideKey,
    color: selectedColor,
    thickness: 4,
    label: "",
    label_at: null,
    waypoints: [],
  };
  config.connections.push(conn);
  clearConnectPickHighlight();
  connectFrom = null;
  renderConnections();
  persistConfig();
  setStatus("Verbindung erstellt. Naechste Verbindung: ersten Anschluss anklicken.");
}

function renderConnections() {
  connectionLayer.innerHTML = "";
  const labeledCableIds = new Set();
  for (const conn of config.connections) {
    const fromEl = config.elements.find((x) => x.id === conn.from);
    const toEl = config.elements.find((x) => x.id === conn.to);
    if (!fromEl || !toEl) continue;
    if (!Array.isArray(conn.waypoints)) conn.waypoints = [];

    const p1 = connectionEndpoint(fromEl, conn.from_port, conn.from_port_side);
    const p2 = connectionEndpoint(toEl, conn.to_port, conn.to_port_side);
    const dir1 = connectionDirection(fromEl, conn.from_port, conn.from_port_side);
    const dir2 = connectionDirection(toEl, conn.to_port, conn.to_port_side);

    const path = buildSmoothPath([p1, ...conn.waypoints, p2], dir1, dir2);

    const group = document.createElementNS("http://www.w3.org/2000/svg", "g");
    group.style.pointerEvents = "auto";

    // Kabel-Buendel: liegt die Verbindung in einem Kabel, wird darunter
    // eine breitere, halbtransparente "Huelle" in der Kabelfarbe gezeichnet.
    // Ueberlappende Adern desselben Kabels (typischer Fall: gleiche
    // Endpunkte) verschmelzen dadurch optisch zu einem gemeinsamen Strang.
    const cable = conn.cable_id ? getCableById(conn.cable_id) : null;
    if (cable) {
      const sleeve = document.createElementNS("http://www.w3.org/2000/svg", "path");
      sleeve.setAttribute("d", path);
      sleeve.setAttribute("class", "cable-sleeve");
      sleeve.setAttribute("stroke", cable.color || "#5c6b7f");
      sleeve.setAttribute("stroke-width", (conn.thickness || 4) + 9);
      sleeve.style.pointerEvents = "none";
      group.appendChild(sleeve);

      if (cable.name && !labeledCableIds.has(cable.id)) {
        labeledCableIds.add(cable.id);
        const points = [p1, ...conn.waypoints, p2];
        const mid = pathMidpoint(points);
        const labelPos = { x: mid.x, y: mid.y - 18 };
        const cableLabel = document.createElementNS("http://www.w3.org/2000/svg", "text");
        cableLabel.setAttribute("x", labelPos.x);
        cableLabel.setAttribute("y", labelPos.y);
        cableLabel.setAttribute("class", "cable-label");
        cableLabel.setAttribute("text-anchor", "middle");
        cableLabel.textContent = "🖇 " + cable.name;
        cableLabel.style.fill = cable.color || "#5c6b7f";
        group.appendChild(cableLabel);
      }
    }

    const hitbox = document.createElementNS("http://www.w3.org/2000/svg", "path");
    hitbox.setAttribute("d", path);
    hitbox.setAttribute("class", "conn-hitbox");

    const visible = document.createElementNS("http://www.w3.org/2000/svg", "path");
    visible.setAttribute("d", path);
    visible.setAttribute("class", "conn-path" + (conn.id === highlightedConnId ? " highlighted" : ""));
    visible.setAttribute("stroke", conn.color || "#3ad6ff");
    visible.setAttribute("stroke-width", (conn.thickness || 4) + (conn.id === highlightedConnId ? 3 : 0));
    visible.style.color = conn.color || "#3ad6ff";
    visible.style.pointerEvents = "none";
    if (highlightedConnId && conn.id !== highlightedConnId) {
      visible.style.opacity = "0.3";
    }

    if (mode === "edit") {
      const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
      title.textContent = "Klick (an beliebiger Stelle der Leitung): Details bearbeiten (Staerke, Kabel-Zugehoerigkeit, Wegpunkte zuruecksetzen, Loeschen)";
      hitbox.appendChild(title);

      hitbox.addEventListener("click", () => {
        if (connectMode) return;
        openConnModal(conn.id);
      });
    } else {
      const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
      title.textContent = "Klick: Leitung hervorheben";
      hitbox.appendChild(title);


      hitbox.addEventListener("click", (e) => {
        e.stopPropagation();
        highlightedConnId = highlightedConnId === conn.id ? null : conn.id;
        renderConnections();
      });
    }

    group.appendChild(hitbox);
    group.appendChild(visible);

    if (conn.label) {
      const points = [p1, ...conn.waypoints, p2];
      const isCustomPos = !!conn.label_at;
      const labelPos = isCustomPos
        ? conn.label_at
        : { x: pathMidpoint(points).x, y: pathMidpoint(points).y - 8 };

      // Gestrichelte Fuehrungslinie, wenn die Bezeichnung weiter von der
      // Leitung weg platziert wurde, damit die Zuordnung erkennbar bleibt.
      if (isCustomPos) {
        const anchor = closestPointOnPolyline(points, labelPos);
        if (Math.hypot(labelPos.x - anchor.x, labelPos.y - anchor.y) > 16) {
          const leader = document.createElementNS("http://www.w3.org/2000/svg", "line");
          leader.setAttribute("x1", anchor.x);
          leader.setAttribute("y1", anchor.y);
          leader.setAttribute("x2", labelPos.x);
          leader.setAttribute("y2", labelPos.y);
          leader.setAttribute("class", "conn-label-leader");
          leader.style.pointerEvents = "none";
          group.appendChild(leader);
        }
      }

      const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
      text.setAttribute("x", labelPos.x);
      text.setAttribute("y", labelPos.y);
      text.setAttribute("class", "conn-label");
      text.setAttribute("text-anchor", "middle");
      text.textContent = conn.label;

      if (mode === "edit") {
        const lTitle = document.createElementNS("http://www.w3.org/2000/svg", "title");
        lTitle.textContent = "Ziehen: Bezeichnung frei platzieren";
        text.appendChild(lTitle);
        text.addEventListener("mousedown", (e) => {
          e.stopPropagation();
          draggingLabel = { connId: conn.id };
        });
      }

      group.appendChild(text);
    }

    /* Fester Bearbeiten-Button an der Leitung (wie das ✎ an den Elementen):
       oeffnet zuverlaessig das Kontextmenue mit Name/Farbe/Wegpunkt/Entfernen,
       ganz ohne Doppelklick-Erkennung. */
    if (mode === "edit") {
      const points = [p1, ...conn.waypoints, p2];
      const mid = pathMidpoint(points);
      const btnPos = { x: mid.x, y: mid.y + 16 };

      const editBtnGroup = document.createElementNS("http://www.w3.org/2000/svg", "g");
      editBtnGroup.setAttribute("class", "conn-edit-btn");

      const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      circle.setAttribute("cx", btnPos.x);
      circle.setAttribute("cy", btnPos.y);
      circle.setAttribute("r", 10);

      const icon = document.createElementNS("http://www.w3.org/2000/svg", "text");
      icon.setAttribute("x", btnPos.x);
      icon.setAttribute("y", btnPos.y + 3.5);
      icon.setAttribute("text-anchor", "middle");
      icon.textContent = "✎";

      const btnTitle = document.createElementNS("http://www.w3.org/2000/svg", "title");
      btnTitle.textContent = "Verbindung bearbeiten: Name, Farbe, Wegpunkt, Entfernen";

      editBtnGroup.appendChild(circle);
      editBtnGroup.appendChild(icon);
      editBtnGroup.appendChild(btnTitle);

      editBtnGroup.addEventListener("mousedown", (e) => e.stopPropagation());
      editBtnGroup.addEventListener("click", (e) => {
        e.stopPropagation();
        if (connectMode) return;
        const clientPos = canvasToClient(btnPos);
        openConnContextMenu(conn, btnPos, clientPos.x, clientPos.y);
      });

      group.appendChild(editBtnGroup);
    }


    if (mode === "edit") {
      conn.waypoints.forEach((wp, idx) => {
        const handle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        handle.setAttribute("cx", wp.x);
        handle.setAttribute("cy", wp.y);
        handle.setAttribute("r", 6);
        handle.setAttribute("class", "waypoint-handle");
        handle.style.fill = conn.color || "#3ad6ff";
        const wpTitle = document.createElementNS("http://www.w3.org/2000/svg", "title");
        wpTitle.textContent = "Ziehen: Leitung umlegen";
        handle.appendChild(wpTitle);
        handle.addEventListener("mousedown", (e) => {
          e.stopPropagation();
          draggingWaypoint = { connId: conn.id, index: idx };
        });
        group.appendChild(handle);

        // Eigener, immer sichtbarer Entfernen-Button je Wegpunkt (zuverlaessiger
        // als Doppelklick, da kein Timing-Konflikt mit dem Ziehen entstehen kann).
        const delBtn = document.createElementNS("http://www.w3.org/2000/svg", "g");
        delBtn.setAttribute("class", "waypoint-delete-btn");
        const delCircle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        delCircle.setAttribute("cx", wp.x + 12);
        delCircle.setAttribute("cy", wp.y - 12);
        delCircle.setAttribute("r", 6.5);
        const delIcon = document.createElementNS("http://www.w3.org/2000/svg", "text");
        delIcon.setAttribute("x", wp.x + 12);
        delIcon.setAttribute("y", wp.y - 12 + 3);
        delIcon.setAttribute("text-anchor", "middle");
        delIcon.textContent = "✕";
        const delTitle = document.createElementNS("http://www.w3.org/2000/svg", "title");
        delTitle.textContent = "Wegpunkt entfernen";
        delBtn.appendChild(delCircle);
        delBtn.appendChild(delIcon);
        delBtn.appendChild(delTitle);
        delBtn.addEventListener("mousedown", (e) => e.stopPropagation());
        delBtn.addEventListener("click", (e) => {
          e.stopPropagation();
          conn.waypoints.splice(idx, 1);
          renderConnections();
          persistConfig();
        });
        group.appendChild(delBtn);
      });
    }

    connectionLayer.appendChild(group);
  }
  markPortColors();
}

/* Ermittelt die Austrittsrichtung eines Verbindungsendes: bei einem
   konkreten Port/Pin zeigt die Leitung senkrecht von dessen Seite weg,
   damit Leitungen nicht quer durch das Element oder andere Elemente
   laufen und sich weniger leicht "verknoten". Ohne konkreten Port/Pin:
   keine feste Richtung. */
function connectionDirection(el, portIndex, portSide) {
  if (portIndex === null || portIndex === undefined) return null;
  if (!hasPorts(el.type)) return null;
  let side;
  if (hasIndividualPinPlacement(el.type)) {
    // Platine/Raspberry Pi: jeder Pin hat seine eigene Seite.
    side = getPinSide(el, portIndex);
  } else {
    const primarySide = getPortSide(el);
    side = portSide === "b" ? OPPOSITE_SIDE[primarySide] : primarySide;
  }
  return { bottom: { x: 0, y: 1 }, top: { x: 0, y: -1 }, left: { x: -1, y: 0 }, right: { x: 1, y: 0 } }[side];
}

/* Einheitliches Routing fuer Verbindungen – erzeugt IMMER eine weiche,
   fliessende Kurve (auch wenn manuelle Wegpunkte gesetzt sind), statt
   Wegpunkte nur mit geraden Teilstrecken zu verbinden. An den Enden wird,
   falls vorhanden, die Portrichtung (dir1/dir2) beibehalten, damit
   Leitungen weiterhin senkrecht zur Portseite abgehen (Anti-Verknoten).
   Dazwischenliegende Wegpunkte erhalten eine Catmull-Rom-aehnliche
   Tangente basierend auf ihren Nachbarpunkten fuer eine gleichmaessige,
   runde Linienfuehrung. */
function buildSmoothPath(points, dir1, dir2) {
  const n = points.length;
  if (n < 2) return "";
  if (n === 2 && !dir1 && !dir2) {
    return `M ${points[0].x} ${points[0].y} L ${points[1].x} ${points[1].y}`;
  }

  const segLen = (a, b) => {
    const d = Math.hypot(b.x - a.x, b.y - a.y);
    return Math.max(40, Math.min(160, d * 0.5));
  };
  const normalize = (v) => {
    const len = Math.hypot(v.x, v.y) || 1;
    return { x: v.x / len, y: v.y / len };
  };

  let d = `M ${points[0].x} ${points[0].y} `;

  for (let i = 0; i < n - 1; i++) {
    const p0 = points[i], p1 = points[i + 1];
    const len = segLen(p0, p1);

    let cpA;
    if (i === 0 && dir1) {
      cpA = { x: p0.x + dir1.x * len, y: p0.y + dir1.y * len };
    } else {
      const prev = points[i - 1] || p0;
      const next = points[i + 1];
      const t = normalize({ x: next.x - prev.x, y: next.y - prev.y });
      cpA = { x: p0.x + t.x * (len / 2.2), y: p0.y + t.y * (len / 2.2) };
    }

    let cpB;
    if (i + 1 === n - 1 && dir2) {
      cpB = { x: p1.x + dir2.x * len, y: p1.y + dir2.y * len };
    } else {
      const prevOfNext = points[i];
      const nextOfNext = points[i + 2] !== undefined ? points[i + 2] : p1;
      const t = normalize({ x: nextOfNext.x - prevOfNext.x, y: nextOfNext.y - prevOfNext.y });
      cpB = { x: p1.x - t.x * (len / 2.2), y: p1.y - t.y * (len / 2.2) };
    }

    d += `C ${cpA.x} ${cpA.y}, ${cpB.x} ${cpB.y}, ${p1.x} ${p1.y} `;
  }

  return d;
}

function pathMidpoint(points) {
  const mid = Math.floor((points.length - 1) / 2);
  const a = points[mid], b = points[Math.min(mid + 1, points.length - 1)];
  return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
}

function distToSegment(p, a, b) {
  const dx = b.x - a.x, dy = b.y - a.y;
  const lenSq = dx * dx + dy * dy;
  let t = lenSq === 0 ? 0 : ((p.x - a.x) * dx + (p.y - a.y) * dy) / lenSq;
  t = Math.max(0, Math.min(1, t));
  const projX = a.x + t * dx, projY = a.y + t * dy;
  return Math.hypot(p.x - projX, p.y - projY);
}

/* Naehester Punkt einer Punktfolge (Leitungsverlauf) zu einem gegebenen
   Punkt – wird genutzt, um eine duenne Fuehrungslinie von der frei
   platzierten Bezeichnung zur zugehoerigen Leitung zu zeichnen. */
function closestPointOnPolyline(points, p) {
  let best = points[0], bestDist = Infinity;
  for (let i = 0; i < points.length - 1; i++) {
    const a = points[i], b = points[i + 1];
    const dx = b.x - a.x, dy = b.y - a.y;
    const lenSq = dx * dx + dy * dy;
    let t = lenSq === 0 ? 0 : ((p.x - a.x) * dx + (p.y - a.y) * dy) / lenSq;
    t = Math.max(0, Math.min(1, t));
    const proj = { x: a.x + t * dx, y: a.y + t * dy };
    const d = Math.hypot(p.x - proj.x, p.y - proj.y);
    if (d < bestDist) { bestDist = d; best = proj; }
  }
  return best;
}

/* ------------------------------------------------------------------ */
/* Kontextmenue fuer Verbindungen (Doppelklick im Bearbeitungsmodus):  */
/* Name vergeben, Farbe aendern, Wegpunkt einfuegen, Leitung entfernen */
/* ------------------------------------------------------------------ */

let connCtxMenuEl = null;
let connCtxOutsideHandler = null;

function currentConnPoints(conn) {
  const fromEl = config.elements.find((x) => x.id === conn.from);
  const toEl = config.elements.find((x) => x.id === conn.to);
  if (!fromEl || !toEl) return [];
  const p1 = connectionEndpoint(fromEl, conn.from_port, conn.from_port_side);
  const p2 = connectionEndpoint(toEl, conn.to_port, conn.to_port_side);
  return [p1, ...(conn.waypoints || []), p2];
}

function openConnContextMenu(conn, canvasPoint, clientX, clientY) {
  closeConnContextMenu();

  const menu = document.createElement("div");
  menu.className = "conn-ctx-menu";
  menu.addEventListener("mousedown", (e) => e.stopPropagation());
  menu.addEventListener("click", (e) => e.stopPropagation());
  menu.addEventListener("dblclick", (e) => e.stopPropagation());
  menu.style.visibility = "hidden";

  // --- Name ---
  const nameLabel = document.createElement("div");
  nameLabel.className = "ctx-menu-label";
  nameLabel.textContent = "Bezeichnung";
  const nameInput = document.createElement("input");
  nameInput.type = "text";
  nameInput.className = "ctx-name-input";
  nameInput.placeholder = "z. B. Uplink, 1 GbE …";
  nameInput.maxLength = 60;
  nameInput.value = conn.label || "";
  nameInput.addEventListener("input", () => {
    conn.label = nameInput.value.trim();
    if (!conn.label) conn.label_at = null;
    renderConnectionsPreserving(menu);
  });
  nameInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); closeConnContextMenu(); }
    if (e.key === "Escape") { e.preventDefault(); closeConnContextMenu(); }
  });

  // --- Farbe ---
  const colorLabel = document.createElement("div");
  colorLabel.className = "ctx-menu-label";
  colorLabel.textContent = "Farbe";
  const colorRow = document.createElement("div");
  colorRow.className = "ctx-color-row";
  CONNECTION_COLORS.forEach((color) => {
    const sw = document.createElement("div");
    sw.className = "color-swatch ctx-swatch" + (conn.color === color ? " selected" : "");
    sw.style.background = color;
    sw.addEventListener("click", () => {
      conn.color = color;
      colorRow.querySelectorAll(".ctx-swatch").forEach((s) => s.classList.remove("selected"));
      sw.classList.add("selected");
      colorInput.value = color;
      renderConnectionsPreserving(menu);
    });
    colorRow.appendChild(sw);
  });
  const colorInput = document.createElement("input");
  colorInput.type = "color";
  colorInput.className = "ctx-color-input";
  colorInput.value = /^#[0-9a-f]{6}$/i.test(conn.color || "") ? conn.color : "#3ad6ff";
  colorInput.addEventListener("input", () => {
    conn.color = colorInput.value;
    colorRow.querySelectorAll(".ctx-swatch").forEach((s) => s.classList.remove("selected"));
    renderConnectionsPreserving(menu);
  });
  colorRow.appendChild(colorInput);

  // --- Aktionen ---
  const actions = document.createElement("div");
  actions.className = "ctx-actions";

  const waypointBtn = document.createElement("button");
  waypointBtn.className = "btn ctx-btn";
  waypointBtn.type = "button";
  waypointBtn.textContent = "+ Wegpunkt hier";
  waypointBtn.title = "Fuegt an dieser Stelle einen verschiebbaren Wegpunkt zur Linienfuehrung hinzu";
  waypointBtn.addEventListener("click", () => {
    const points = currentConnPoints(conn);
    let bestIdx = 0, bestDist = Infinity;
    for (let i = 0; i < points.length - 1; i++) {
      const d = distToSegment(canvasPoint, points[i], points[i + 1]);
      if (d < bestDist) { bestDist = d; bestIdx = i; }
    }
    if (!Array.isArray(conn.waypoints)) conn.waypoints = [];
    conn.waypoints.splice(bestIdx, 0, canvasPoint);
    closeConnContextMenu();
  });

  const deleteBtn = document.createElement("button");
  deleteBtn.className = "btn btn-danger ctx-btn";
  deleteBtn.type = "button";
  deleteBtn.textContent = "Entfernen";
  deleteBtn.addEventListener("click", () => {
    if (!confirm("Diese Verbindung wirklich entfernen?")) return;
    config.connections = config.connections.filter((c) => c.id !== conn.id);
    cleanupOrphanCables();
    closeConnContextMenu(true);
    renderConnections();
    persistConfig();
  });

  actions.appendChild(waypointBtn);
  actions.appendChild(deleteBtn);

  menu.appendChild(nameLabel);
  menu.appendChild(nameInput);
  menu.appendChild(colorLabel);
  menu.appendChild(colorRow);
  menu.appendChild(actions);
  document.body.appendChild(menu);

  // Position an der Klickstelle, an den Bildschirmrand geklemmt
  const menuWidth = 220;
  const vw = window.innerWidth, vh = window.innerHeight;
  const menuHeight = menu.offsetHeight || 160;
  const left = Math.min(Math.max(8, clientX - menuWidth / 2), vw - menuWidth - 8);
  const top = Math.min(Math.max(8, clientY + 12), vh - menuHeight - 8);
  menu.style.left = left + "px";
  menu.style.top = top + "px";
  menu.style.width = menuWidth + "px";
  menu.style.visibility = "visible";

  nameInput.focus();
  nameInput.select();

  connCtxMenuEl = menu;

  setTimeout(() => {
    connCtxOutsideHandler = (e) => {
      if (menu.contains(e.target)) return;
      closeConnContextMenu();
    };
    document.addEventListener("mousedown", connCtxOutsideHandler, true);
  }, 0);
}

function closeConnContextMenu(skipPersist) {
  if (connCtxOutsideHandler) {
    document.removeEventListener("mousedown", connCtxOutsideHandler, true);
    connCtxOutsideHandler = null;
  }
  const hadMenu = !!connCtxMenuEl;
  if (connCtxMenuEl) {
    connCtxMenuEl.remove();
    connCtxMenuEl = null;
  }
  renderConnections();
  if (hadMenu && !skipPersist) {
    persistConfig();
  }
}

/* Rendert die Verbindungen neu, ohne das offene Kontextmenue (eigenes
   DOM-Element ausserhalb des SVG) zu beruehren – fuer Live-Vorschau
   waehrend der Eingabe. */
function renderConnectionsPreserving() {
  renderConnections();
}

/* Faerbt jeden belegten Port-Andockpunkt in der Farbe seiner Verbindung ein,
   damit auf einen Blick erkennbar ist, welche Leitung an welchem Port haengt. */
function markPortColors() {
  elementLayer.querySelectorAll(".port-dot").forEach((dot) => {
    dot.style.borderColor = "";
    dot.style.boxShadow = "";
    dot.style.background = "";
    dot.style.color = "";
    dot.classList.remove("port-connected");
  });
  for (const conn of config.connections) {
    const color = conn.color || "#3ad6ff";
    if (conn.from_port !== null && conn.from_port !== undefined) {
      applyPortColor(conn.from, conn.from_port, conn.from_port_side, color);
    }
    if (conn.to_port !== null && conn.to_port !== undefined) {
      applyPortColor(conn.to, conn.to_port, conn.to_port_side, color);
    }
  }
}

function applyPortColor(elId, portIndex, portSide, color) {
  const sideKey = portSide === "b" ? "b" : "a";
  const dot = elementLayer.querySelector(
    `.net-element[data-id="${elId}"] .port-dot[data-port="${portIndex}"][data-side="${sideKey}"]`
  );
  if (!dot) return;
  dot.classList.add("port-connected");
  dot.style.borderColor = color;
  dot.style.boxShadow = "0 0 5px " + color;
  dot.style.background = color;
  dot.style.color = "#0a0e14";
}

function elementCenter(el) {
  return { x: el.x + DEFAULT_ELEMENT_W / 2, y: el.y + DEFAULT_ELEMENT_H / 2 };
}

/* Liefert den Andockpunkt einer Verbindung: bei Switch/Router/Patchfeld den
   konkreten Port (falls vorhanden), sonst den Element-Mittelpunkt. */
function connectionEndpoint(el, portIndex, portSide) {
  const rel = portRelOffsets[el.id];
  const key = portSide === "b" ? "b" : "a";
  if (portIndex !== null && portIndex !== undefined && rel && rel[key] && rel[key][portIndex]) {
    return { x: el.x + rel[key][portIndex].x, y: el.y + rel[key][portIndex].y };
  }
  return elementCenter(el);
}

/* Geschwungene, dicke Verbindungslinien im Stil von harness.design –
   siehe buildSmoothPath() weiter oben fuer das eigentliche Routing. */

/* ------------------------------------------------------------------ */
/* Kabel-Buendel: mehrere Verbindungen zu einem gemeinsamen "Kabel"     */
/* zusammenfassen (z. B. alle Adern eines Motorkabels). Verwaltung      */
/* erfolgt ueber das Verbindungs-Bearbeiten-Modal (Feld "Kabel-Buendel"). */
/* ------------------------------------------------------------------ */

function getCables() {
  if (!Array.isArray(config.cables)) config.cables = [];
  return config.cables;
}
function getCableById(id) {
  return getCables().find((c) => c.id === id) || null;
}
/* Entfernt Kabel, auf die keine Verbindung mehr verweist (z. B. nach dem
   Entfernen der letzten Ader oder dem Umhaengen auf ein anderes Kabel). */
function cleanupOrphanCables() {
  const used = new Set(config.connections.map((c) => c.cable_id).filter(Boolean));
  config.cables = getCables().filter((c) => used.has(c.id));
}
function populateCableSelect(currentCableId) {
  const sel = $("#cCable");
  sel.innerHTML = "";
  const noneOpt = document.createElement("option");
  noneOpt.value = "";
  noneOpt.textContent = "— Kein Kabel —";
  sel.appendChild(noneOpt);
  getCables().forEach((cable) => {
    const o = document.createElement("option");
    o.value = cable.id;
    o.textContent = cable.name;
    sel.appendChild(o);
  });
  const newOpt = document.createElement("option");
  newOpt.value = "__new__";
  newOpt.textContent = "+ Neues Kabel…";
  sel.appendChild(newOpt);
  sel.value = currentCableId || "";
}

function openConnModal(id) {
  editingConnId = id;
  const conn = config.connections.find((c) => c.id === id);
  if (!conn) return;
  $("#cLabel").value = conn.label || "";
  $("#cThickness").value = conn.thickness || 4;
  $("#cThicknessVal").textContent = conn.thickness || 4;
  selectedColor = conn.color || CONNECTION_COLORS[0];
  $("#cColorPicker").value = selectedColor;
  $$(".color-swatch").forEach((s) => {
    s.classList.toggle("selected", s.dataset.color === selectedColor);
  });
  populateCableSelect(conn.cable_id || "");
  $("#connModal").classList.remove("hidden");
}

$("#cThickness").addEventListener("input", (e) => {
  $("#cThicknessVal").textContent = e.target.value;
});

$("#cCancel").addEventListener("click", () => $("#connModal").classList.add("hidden"));

$("#cResetRoute").addEventListener("click", () => {
  const conn = config.connections.find((c) => c.id === editingConnId);
  if (!conn) return;
  conn.waypoints = [];
  $("#connModal").classList.add("hidden");
  renderConnections();
  persistConfig();
});

$("#cSave").addEventListener("click", () => {
  const conn = config.connections.find((c) => c.id === editingConnId);
  if (!conn) return;
  conn.label = $("#cLabel").value.trim();
  if (!conn.label) conn.label_at = null;
  conn.thickness = parseInt($("#cThickness").value, 10);
  conn.color = selectedColor;

  const cableVal = $("#cCable").value;
  if (cableVal === "__new__") {
    const name = (window.prompt('Name des neuen Kabels (z. B. "Motorkabel 1"):', "") || "").trim();
    if (name) {
      const newCable = {
        id: "cable-" + Date.now() + "-" + Math.floor(Math.random() * 1000),
        name,
        color: "#5c6b7f",
      };
      getCables().push(newCable);
      conn.cable_id = newCable.id;
    }
    // Abgebrochen (leerer Name) -> bisherige Kabel-Zuordnung unveraendert lassen.
  } else {
    conn.cable_id = cableVal || null;
  }
  cleanupOrphanCables();

  $("#connModal").classList.add("hidden");
  renderConnections();
  persistConfig();
});

$("#cDelete").addEventListener("click", () => {
  config.connections = config.connections.filter((c) => c.id !== editingConnId);
  cleanupOrphanCables();
  $("#connModal").classList.add("hidden");
  renderConnections();
  persistConfig();
});

/* ------------------------------------------------------------------ */
/* Raster / Einrasten Toggle                                           */
/* ------------------------------------------------------------------ */

$("#chkGrid").addEventListener("change", () => {
  config.view.show_grid = $("#chkGrid").checked;
  applyGridVisibility();
  persistConfig();
});
$("#chkSnap").addEventListener("change", () => {
  config.view.snap_to_grid = $("#chkSnap").checked;
  persistConfig();
});

/* ------------------------------------------------------------------ */
/* Speichern                                                            */
/* ------------------------------------------------------------------ */

let saveTimer = null;
function saveViewDebounced() {
  config.view.zoom = scale;
  config.view.pan_x = panX;
  config.view.pan_y = panY;
  clearTimeout(saveTimer);
  saveTimer = setTimeout(persistConfig, 600);
}

async function persistConfig() {
  config.view.zoom = scale;
  config.view.pan_x = panX;
  config.view.pan_y = panY;
  try {
    await fetch("/api/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config),
    });
    setStatus("Gespeichert.");
  } catch (err) {
    setStatus("Fehler beim Speichern!");
  }
}

$("#btnSave").addEventListener("click", persistConfig);

function setStatus(text) {
  $("#statusText").textContent = text;
}

/* Gut sichtbare, kurzzeitig eingeblendete Meldung (z. B. fuer den Hinweis
   nach einem Datei-Download) – im Gegensatz zur duennen Statuszeile am
   unteren Rand leichter zu bemerken. */
let toastTimer = null;
function showToast(message, durationMs) {
  let toast = document.getElementById("appToast");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "appToast";
    toast.className = "app-toast";
    document.body.appendChild(toast);
  }
  toast.textContent = message;
  toast.classList.add("visible");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    toast.classList.remove("visible");
  }, durationMs || 5000);
}

/* ------------------------------------------------------------------ */
/* Export: PDF (Querformat, dunkel/hell) und Netzliste (CSV)           */
/* Beide Exporte senden den aktuellen In-Memory-Stand (`config`) direkt */
/* an den Server, damit auch noch ungespeicherte Aenderungen enthalten  */
/* sind – ein separates "Speichern" davor ist nicht noetig.            */
/* ------------------------------------------------------------------ */

$("#btnExport").addEventListener("click", () => {
  $("#exportModal").classList.remove("hidden");
});
$("#exportCancel").addEventListener("click", () => $("#exportModal").classList.add("hidden"));
$("#btnExportPdfDark").addEventListener("click", () => exportPdf("dark"));
$("#btnExportPdfLight").addEventListener("click", () => exportPdf("light"));
$("#btnExportNetlist").addEventListener("click", () => exportNetlist());

async function exportPdf(theme) {
  const themeLabel = theme === "light" ? "hell" : "dunkel";
  setStatus("Erzeuge PDF (" + themeLabel + ", Querformat)…");
  try {
    const res = await fetch("/api/export/pdf", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ config, theme }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => null);
      throw new Error((err && err.message) || ("HTTP " + res.status));
    }
    const blob = await res.blob();
    triggerBlobDownload(blob, filenameFromResponse(res, "Verkabelungsplan_" + theme + ".pdf"));
    $("#exportModal").classList.add("hidden");
    setStatus("PDF (" + themeLabel + ") heruntergeladen.");
  } catch (err) {
    setStatus("Fehler beim PDF-Export.");
    showToast("⚠ PDF-Export fehlgeschlagen: " + err.message, 6000);
  }
}

async function exportNetlist() {
  setStatus("Erzeuge Netzliste…");
  try {
    const res = await fetch("/api/export/netlist", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ config }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => null);
      throw new Error((err && err.message) || ("HTTP " + res.status));
    }
    const blob = await res.blob();
    triggerBlobDownload(blob, filenameFromResponse(res, "Netzliste.csv"));
    $("#exportModal").classList.add("hidden");
    setStatus("Netzliste heruntergeladen.");
  } catch (err) {
    setStatus("Fehler beim Netzliste-Export.");
    showToast("⚠ Netzliste-Export fehlgeschlagen: " + err.message, 6000);
  }
}

function filenameFromResponse(res, fallback) {
  const cd = res.headers.get("Content-Disposition") || "";
  const m = cd.match(/filename="?([^";]+)"?/i);
  return m ? m[1] : fallback;
}

function triggerBlobDownload(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.style.display = "none";
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 4000);
}

/* ------------------------------------------------------------------ */
/* Globale Events                                                      */
/* ------------------------------------------------------------------ */

function bindGlobalEvents() {
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      $("#elementModal").classList.add("hidden");
      $("#connModal").classList.add("hidden");
      $("#exportModal").classList.add("hidden");
      if (connCtxMenuEl) closeConnContextMenu();
      closePortNameEditor();
      if (marqueeState) {
        marqueeState.el.remove();
        marqueeState = null;
      }
      if (selectedElementIds.size > 0) {
        elementLayer.querySelectorAll(".net-element.multi-selected").forEach((n) => n.classList.remove("multi-selected"));
        selectedElementIds.clear();
      }
      if (highlightedConnId) {
        highlightedConnId = null;
        renderConnections();
      }
      if (highlightedLocation) {
        highlightedLocation = null;
        renderElements();
      }
      if (connectMode) {
        connectMode = false;
        connectFrom = null;
        viewport.classList.remove("connect-mode");
        $("#btnConnectMode").classList.remove("btn-primary");
        clearConnectPickHighlight();
      }
    }
  });

  window.addEventListener("beforeunload", () => {
    // Bestes Bemuehen: letzten Stand synchron sichern
    navigator.sendBeacon &&
      navigator.sendBeacon(
        "/api/config",
        new Blob([JSON.stringify(config)], { type: "application/json" })
      );
  });
}

init();
