from io import BytesIO
from datetime import datetime

from carpinteria.database import DEFAULT_SETTINGS
from carpinteria.utils import fit_text, money

def pdf_escape(text) -> bytes:
    clean = str(text if text is not None else "")
    raw = clean.encode("cp1252", errors="replace")
    return raw.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def fit_text(text, max_chars: int) -> str:
    clean = " ".join(str(text if text is not None else "").split())
    if len(clean) <= max_chars:
        return clean
    return clean[: max_chars - 1].rstrip() + "..."


class PdfCanvas:
    def __init__(self):
        self.width = 612
        self.height = 792
        self.margin = 42
        self.pages: list[list[bytes]] = []
        self.ops: list[bytes] = []
        self.y = self.height - self.margin

    def add_page(self):
        if self.ops:
            self.pages.append(self.ops)
        self.ops = []
        self.y = self.height - self.margin

    def color(self, stroke="#1F2933", fill=None):
        if stroke:
            r, g, b = hex_to_rgb(stroke)
            self.ops.append(f"{r:.3f} {g:.3f} {b:.3f} RG\n".encode())
        if fill:
            r, g, b = hex_to_rgb(fill)
            self.ops.append(f"{r:.3f} {g:.3f} {b:.3f} rg\n".encode())

    def text(self, x, y, text, size=10, bold=False, color="#1F2933"):
        self.color(stroke=color, fill=color)
        font = "F2" if bold else "F1"
        self.ops.append(
            b"BT /"
            + font.encode()
            + f" {size} Tf {x:.2f} {y:.2f} Td (".encode()
            + pdf_escape(text)
            + b") Tj ET\n"
        )

    def right_text(self, x, y, text, size=10, bold=False, color="#1F2933"):
        approx_width = len(str(text)) * size * 0.52
        self.text(x - approx_width, y, text, size, bold, color)

    def rect(self, x, y, w, h, stroke="#D7DEE8", fill=None):
        self.color(stroke=stroke, fill=fill)
        op = "B" if fill and stroke else "f" if fill else "S"
        self.ops.append(f"{x:.2f} {y:.2f} {w:.2f} {h:.2f} re {op}\n".encode())

    def line(self, x1, y1, x2, y2, color="#D7DEE8"):
        self.color(stroke=color)
        self.ops.append(f"{x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S\n".encode())

    def ensure_space(self, needed):
        if self.y - needed < self.margin:
            self.add_page()

    def finish(self) -> bytes:
        if self.ops:
            self.pages.append(self.ops)
        objects = []
        objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
        page_refs = []
        content_start = 5
        for idx in range(len(self.pages)):
            page_obj = content_start + idx * 2
            page_refs.append(f"{page_obj} 0 R".encode())
        objects.append(b"<< /Type /Pages /Kids [" + b" ".join(page_refs) + b"] /Count " + str(len(self.pages)).encode() + b" >>")
        objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
        objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")
        for idx, ops in enumerate(self.pages):
            content_obj = content_start + idx * 2 + 1
            content = b"".join(ops)
            objects.append(
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {self.width} {self.height}] "
                f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents {content_obj} 0 R >>".encode()
            )
            objects.append(b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"endstream")

        out = BytesIO()
        out.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = [0]
        for i, obj in enumerate(objects, start=1):
            offsets.append(out.tell())
            out.write(f"{i} 0 obj\n".encode() + obj + b"\nendobj\n")
        xref = out.tell()
        out.write(f"xref\n0 {len(objects)+1}\n".encode())
        out.write(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            out.write(f"{offset:010d} 00000 n \n".encode())
        out.write(
            f"trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
        )
        return out.getvalue()


def hex_to_rgb(value: str):
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) / 255 for i in (0, 2, 4))

PDF_COLORS = {
    "ink": "#2A1A10",
    "muted": "#6F5948",
    "walnut": "#4B2E1F",
    "wood": "#9A5B2E",
    "wood_dark": "#6B3F24",
    "cream": "#FFF6E8",
    "sawdust": "#F3E2C7",
    "line": "#C7A982",
    "total_bg": "#F8E7C9",
}


def build_furniture_quote_pdf(
    furniture,
    lines,
    material_total,
    subtotal,
    margin_amount,
    grand_total,
    workshop=None,
    meta=None,
) -> bytes:
    c = PDF_COLORS
    workshop = workshop or DEFAULT_SETTINGS
    meta = meta or {}
    title = meta.get("title") or furniture["name"]
    subtitle = meta.get("subtitle") or furniture["description"] or ""
    folio = meta.get("folio") or f"M-{furniture['id']:04d}"
    customer = meta.get("customer") or ""
    created_at = meta.get("created_at") or datetime.now().strftime("%Y-%m-%d")
    pdf = PdfCanvas()
    pdf.rect(0, 0, pdf.width, pdf.height, stroke=None, fill="#FFFCF6")
    pdf.rect(0, pdf.height - 112, pdf.width, 112, stroke=None, fill=c["walnut"])
    pdf.rect(0, pdf.height - 116, pdf.width, 8, stroke=None, fill=c["wood"])
    pdf.text(42, 740, fit_text(workshop.get("workshop_name") or "Carpinteria", 34), 20, True, "#FFFFFF")
    pdf.text(42, 716, "Cotizacion de mueble", 12, False, c["sawdust"])
    contact = " | ".join(part for part in [workshop.get("phone"), workshop.get("address")] if part)
    if contact:
        pdf.text(42, 698, fit_text(contact, 64), 9, False, c["sawdust"])
    pdf.right_text(570, 740, f"Fecha: {created_at}", 10, False, "#FFFFFF")
    pdf.right_text(570, 722, f"Folio: {folio}", 10, True, c["sawdust"])

    pdf.y = 654
    pdf.text(42, pdf.y, "Trabajo", 11, True, c["wood_dark"])
    pdf.text(42, pdf.y - 20, title, 18, True, c["ink"])
    if customer:
        pdf.text(42, pdf.y - 39, f"Cliente: {fit_text(customer, 72)}", 10, True, c["wood_dark"])
        desc_y = pdf.y - 56
    else:
        desc_y = pdf.y - 39
    if subtitle:
        pdf.text(42, desc_y, fit_text(subtitle, 96), 10, False, c["muted"])

    pdf.y -= 88
    draw_quote_table(pdf, lines, c)

    pdf.ensure_space(170)
    total_x = 350
    pdf.y -= 8
    pdf.line(total_x, pdf.y, 570, pdf.y, c["line"])
    totals = [
        ("Materiales", material_total),
        ("Margen fijo 100%", margin_amount),
    ]
    for label, value in totals:
        pdf.y -= 22
        pdf.text(total_x, pdf.y, label, 10, False, c["muted"])
        pdf.right_text(560, pdf.y, money(value), 11, True, c["ink"])

    pdf.y -= 36
    pdf.rect(total_x - 8, pdf.y - 12, 228, 36, stroke=c["wood_dark"], fill=c["walnut"])
    pdf.text(total_x, pdf.y, "Total sugerido", 11, True, "#FFFFFF")
    pdf.right_text(560, pdf.y, money(grand_total), 16, True, "#FFFFFF")

    pdf.y -= 48
    pdf.text(42, pdf.y, "Notas", 10, True, c["wood_dark"])
    pdf.text(42, pdf.y - 18, fit_text(workshop.get("quote_validity"), 105), 9, False, c["muted"])
    pdf.text(42, pdf.y - 34, fit_text(workshop.get("payment_terms"), 105), 9, False, c["muted"])
    return pdf.finish()


def draw_quote_table(pdf: PdfCanvas, lines, colors):
    headers = ["Material", "Proveedor", "Cant.", "Unidad", "Precio", "Total"]
    widths = [190, 110, 48, 54, 70, 70]
    x0 = 42
    row_h = 26
    pdf.text(x0, pdf.y, "Materiales necesarios", 12, True, colors["wood_dark"])
    pdf.y -= 30
    draw_table_header(pdf, x0, pdf.y, headers, widths, colors)
    pdf.y -= row_h
    for line in lines:
        pdf.ensure_space(row_h + 120)
        if pdf.y > pdf.height - pdf.margin - 5:
            draw_table_header(pdf, x0, pdf.y, headers, widths, colors)
            pdf.y -= row_h
        values = [
            fit_text(line["material_name"], 30),
            fit_text(line["supplier_name"] or "-", 18),
            f"{line['quantity']:.3f}".rstrip("0").rstrip("."),
            fit_text(line["unit"], 8),
            money(line["unit_price"]),
            money(line["total"]),
        ]
        draw_table_row(pdf, x0, pdf.y, values, widths, colors)
        pdf.y -= row_h
    if not lines:
        pdf.text(x0 + 8, pdf.y + 8, "Aun no hay materiales capturados para este mueble.", 10, False, colors["muted"])
        pdf.y -= row_h


def draw_table_header(pdf: PdfCanvas, x, y, headers, widths, colors):
    pdf.rect(x, y - 8, sum(widths), 26, stroke=colors["wood"], fill=colors["walnut"])
    col_x = x
    for header, width in zip(headers, widths):
        pdf.text(col_x + 6, y, header, 9, True, "#FFFFFF")
        col_x += width


def draw_table_row(pdf: PdfCanvas, x, y, values, widths, colors):
    pdf.line(x, y - 8, x + sum(widths), y - 8, colors["line"])
    col_x = x
    for idx, (value, width) in enumerate(zip(values, widths)):
        if idx >= 4:
            pdf.right_text(col_x + width - 6, y, value, 9, False, colors["ink"])
        else:
            pdf.text(col_x + 6, y, value, 9, False, colors["ink"])
        col_x += width
