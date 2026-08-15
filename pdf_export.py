# -*- coding: utf-8 -*-
"""
pdf_export.py
=============
Exportiert den aktuellen Verkabelungsplan als PDF im Querformat (A4 quer).
"""

import datetime
from collections import defaultdict

from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.lib.units import mm
from reportlab.lib import colors

from models import ELEMENT_WIDTH as EW, ELEMENT_HEIGHT as EH


def _pin_positions(el):
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
        usable = EW - 2 * margin_p
        for idx, pin_idx in enumerate(order):
            px = el["x"] + margin_p + (usable * (idx + 0.5) / n if n else usable / 2)
            py = el["y"] + EH if side == "unten" else el["y"]
            result.append((pins[pin_idx], (px, py)))
    else:
        usable = EH - 2 * margin_p
        for idx, pin_idx in enumerate(order):
            py = el["y"] + margin_p + (usable * (idx + 0.5) / n if n else usable / 2)
            px = el["x"] + EW if side == "rechts" else el["x"]
            result.append((pins[pin_idx], (px, py)))
    return result


def _anchor(el, pin_name):
    if pin_name:
        for name, pt in _pin_positions(el):
            if name == pin_name:
                return pt
    return (el["x"] + EW / 2, el["y"] + EH / 2)


def _offset(p1, p2, idx, total, spacing):
    if total <= 1:
        return (0, 0)
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    length = (dx ** 2 + dy ** 2) ** 0.5 or 1
    perp = (-dy / length, dx / length)
    f = (idx - (total - 1) / 2) * spacing
    return (perp[0] * f, perp[1] * f)


def export_to_pdf(path, netz_config, title="Verkabelungsplan"):
    elements = netz_config.get("elements", [])
    connections = netz_config.get("connections", [])
    if not elements:
        raise ValueError("Es sind keine Elemente vorhanden - der Plan ist leer.")

    xs, ys = [], []
    for el in elements:
        xs += [el["x"], el["x"] + EW]
        ys += [el["y"], el["y"] + EH]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    content_w = max(max_x - min_x, 1)
    content_h = max(max_y - min_y, 1)

    page_w, page_h = landscape(A4)
    margin = 18 * mm
    top_margin = 26 * mm
    avail_w = page_w - 2 * margin
    avail_h = page_h - margin - top_margin
    scale = min(avail_w / content_w, avail_h / content_h)
    scale = min(scale, 1.6)

    def tx(x):
        return margin + (x - min_x) * scale

    def ty(y):
        return page_h - top_margin - (y - min_y) * scale

    c = pdfcanvas.Canvas(path, pagesize=landscape(A4))
    c.setTitle(title)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin, page_h - 14 * mm, title)
    c.setFont("Helvetica", 9)
    c.drawString(margin, page_h - 19 * mm,
                 "Erstellt am " + datetime.datetime.now().strftime("%d.%m.%Y %H:%M"))

    by_id = {el["id"]: el for el in elements}

    pair_total = defaultdict(int)
    for conn in connections:
        pair_total[frozenset((conn["from_element"], conn["to_element"]))] += 1
    pair_seen = defaultdict(int)

    # Verbindungen zuerst zeichnen, damit die Elemente darueber liegen
    for conn in connections:
        fel = by_id.get(conn["from_element"])
        tel = by_id.get(conn["to_element"])
        if not fel or not tel:
            continue
        p1 = _anchor(fel, conn.get("from_pin"))
        p2 = _anchor(tel, conn.get("to_pin"))
        key = frozenset((conn["from_element"], conn["to_element"]))
        idx = pair_seen[key]
        pair_seen[key] += 1
        off = _offset(p1, p2, idx, pair_total[key], 10)
        p1o = (p1[0] + off[0], p1[1] + off[1])
        p2o = (p2[0] + off[0], p2[1] + off[1])

        if conn["kind"] == "einzel":
            c.setStrokeColor(colors.HexColor(conn.get("color", "#3ad6ff")))
            c.setLineWidth(max(0.6, conn.get("thickness", 3) * scale * 0.5))
            c.line(tx(p1o[0]), ty(p1o[1]), tx(p2o[0]), ty(p2o[1]))
        else:
            wires = conn.get("wires", [])
            n = len(wires)
            for wi, wire in enumerate(wires):
                woff = _offset(p1o, p2o, wi, n, 5.5)
                wp1 = (p1o[0] + woff[0], p1o[1] + woff[1])
                wp2 = (p2o[0] + woff[0], p2o[1] + woff[1])
                c.setStrokeColor(colors.HexColor(wire.get("farbe", "#000000")))
                c.setLineWidth(max(0.5, 2.2 * scale * 0.5))
                c.line(tx(wp1[0]), ty(wp1[1]), tx(wp2[0]), ty(wp2[1]))

    # Elemente zeichnen
    for el in elements:
        x0, y0 = tx(el["x"]), ty(el["y"])
        x1, y1 = tx(el["x"] + EW), ty(el["y"] + EH)
        rx0, ry0 = min(x0, x1), min(y0, y1)
        w = abs(x1 - x0)
        h = abs(y1 - y0)
        c.setFillColor(colors.HexColor("#f2f4f6"))
        c.setStrokeColor(colors.HexColor("#2b2b2b"))
        c.roundRect(rx0, ry0, w, h, 4, fill=1, stroke=1)
        c.setFillColor(colors.HexColor("#111111"))
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(rx0 + w / 2, ry0 + h - 12, el["name"])
        sub = el.get("type", "")
        if el.get("location"):
            sub += "  ·  " + el["location"]
        c.setFont("Helvetica", 6.5)
        c.drawCentredString(rx0 + w / 2, ry0 + h - 21, sub)
        for name, (px, py) in _pin_positions(el):
            sx, sy = tx(px), ty(py)
            c.setFillColor(colors.HexColor("#1f6fb2"))
            c.circle(sx, sy, 1.5, fill=1, stroke=0)

    c.showPage()
    c.save()
