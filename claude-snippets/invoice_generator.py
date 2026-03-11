"""
invoice_generator.py

Generates a PDF invoice using ReportLab.
Run directly to be prompted for all inputs, or import and call generate_invoice().

Usage:
    python invoice_generator.py
"""

import os
from dataclasses import dataclass, field
from datetime import date
from typing import List

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class Sender:
    name: str
    address: str
    email: str


@dataclass
class LineItem:
    description: str
    detail: str       # e.g. "Hourly rate @ $200"
    qty: float
    rate: float

    @property
    def amount(self) -> float:
        return self.qty * self.rate


@dataclass
class InvoiceData:
    sender: Sender
    client_name: str
    invoice_number: str
    invoice_date: str           # formatted string, e.g. "March 11, 2026"
    line_items: List[LineItem]
    tax_rate: float = 0.0       # e.g. 0.08 for 8%
    output_dir: str = "."


# ---------------------------------------------------------------------------
# PDF builder
# ---------------------------------------------------------------------------

def generate_invoice(data: InvoiceData) -> str:
    """Build the PDF and return the output file path."""

    # Sanitize client name for filename
    client_slug = data.client_name.replace(" ", "_").replace(",", "").replace(".", "")
    filename = f"Invoice_{data.invoice_number}_{client_slug}.pdf"
    output_path = os.path.join(data.output_dir, filename)

    # Colors
    dark_gray   = colors.HexColor('#2d2d2d')
    medium_gray = colors.HexColor('#666666')
    light_gray  = colors.HexColor('#f5f5f5')
    border_gray = colors.HexColor('#e0e0e0')

    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    # --- Styles ---
    name_style          = ParagraphStyle('name',          fontSize=16, fontName='Helvetica-Bold',    textColor=dark_gray,   spaceAfter=2)
    contact_style       = ParagraphStyle('contact',       fontSize=9,  fontName='Helvetica',         textColor=medium_gray, leading=14)
    inv_label_style     = ParagraphStyle('invlabel',      fontSize=9,  fontName='Helvetica',         textColor=medium_gray, alignment=TA_RIGHT)
    inv_value_style     = ParagraphStyle('invvalue',      fontSize=9,  fontName='Helvetica-Bold',    textColor=dark_gray,   alignment=TA_RIGHT)
    section_hdr_style   = ParagraphStyle('sectionheader', fontSize=8,  fontName='Helvetica-Bold',    textColor=medium_gray, spaceAfter=4)
    body_style          = ParagraphStyle('body',          fontSize=9,  fontName='Helvetica',         textColor=dark_gray,   leading=14)
    body_right          = ParagraphStyle('bodyright',     fontSize=9,  fontName='Helvetica',         textColor=dark_gray,   alignment=TA_RIGHT)
    subdesc_style       = ParagraphStyle('subdesc',       fontSize=9,  fontName='Helvetica',         textColor=medium_gray)
    th_style            = ParagraphStyle('th',            fontSize=8,  fontName='Helvetica-Bold',    textColor=medium_gray)
    th_right            = ParagraphStyle('thright',       fontSize=8,  fontName='Helvetica-Bold',    textColor=medium_gray, alignment=TA_RIGHT)
    subtotal_lbl        = ParagraphStyle('subt',          fontSize=9,  fontName='Helvetica',         textColor=medium_gray, alignment=TA_RIGHT)
    subtotal_val        = ParagraphStyle('subtv',         fontSize=9,  fontName='Helvetica',         textColor=dark_gray,   alignment=TA_RIGHT)
    total_lbl           = ParagraphStyle('totlbl',        fontSize=11, fontName='Helvetica-Bold',    textColor=dark_gray,   alignment=TA_RIGHT)
    total_val           = ParagraphStyle('totval',        fontSize=11, fontName='Helvetica-Bold',    textColor=dark_gray,   alignment=TA_RIGHT)
    footer_style        = ParagraphStyle('footer',        fontSize=9,  fontName='Helvetica-Oblique', textColor=medium_gray, alignment=TA_CENTER)
    inv_header_style    = ParagraphStyle('inv',           fontSize=16, fontName='Helvetica-Bold',    textColor=border_gray, alignment=TA_RIGHT)
    bill_name_style     = ParagraphStyle('billname',      fontSize=11, fontName='Helvetica-Bold',    textColor=dark_gray,   spaceAfter=2)

    story = []

    # --- Header ---
    header_table = Table(
        [[Paragraph(data.sender.name, name_style), Paragraph("INVOICE", inv_header_style)]],
        colWidths=[3.5 * inch, 3.5 * inch],
    )
    header_table.setStyle(TableStyle([
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING',    (0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 6))

    # --- Subheader: contact info + invoice meta ---
    contact_info = Paragraph(
        f"{data.sender.address}<br/>{data.sender.email}",
        contact_style,
    )
    invoice_meta_table = Table(
        [
            [Paragraph("Invoice Number", inv_label_style), Paragraph(f"#{data.invoice_number}", inv_value_style)],
            [Paragraph("Invoice Date",   inv_label_style), Paragraph(data.invoice_date,          inv_value_style)],
        ],
        colWidths=[1.5 * inch, 1.5 * inch],
    )
    invoice_meta_table.setStyle(TableStyle([
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING',    (0, 0), (-1, -1), 1),
        ('ALIGN',         (0, 0), (-1, -1), 'RIGHT'),
    ]))

    subheader_table = Table([[contact_info, invoice_meta_table]], colWidths=[3.5 * inch, 3.5 * inch])
    subheader_table.setStyle(TableStyle([
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING',    (0, 0), (-1, -1), 0),
    ]))
    story.append(subheader_table)
    story.append(Spacer(1, 24))

    story.append(HRFlowable(width="100%", thickness=1, color=border_gray))
    story.append(Spacer(1, 20))

    # --- Billed To ---
    story.append(Paragraph("BILLED TO", section_hdr_style))
    story.append(Paragraph(data.client_name, bill_name_style))
    story.append(Spacer(1, 20))

    # --- Line items table ---
    col_widths = [3.5 * inch, 1 * inch, 1 * inch, 1.5 * inch]
    table_rows = [
        [
            Paragraph("DESCRIPTION", th_style),
            Paragraph("QTY",         th_right),
            Paragraph("RATE",        th_right),
            Paragraph("AMOUNT",      th_right),
        ]
    ]

    line_styles = []
    for i, item in enumerate(data.line_items):
        row_index = len(table_rows)
        table_rows.append([
            Paragraph(item.description, body_style),
            Paragraph("", body_right),
            Paragraph("", body_right),
            Paragraph("", body_right),
        ])
        table_rows.append([
            Paragraph(item.detail, subdesc_style),
            Paragraph(f"{item.qty:g}",        body_right),
            Paragraph(f"${item.rate:,.2f}",   body_right),
            Paragraph(f"${item.amount:,.2f}", body_right),
        ])
        line_styles.append(('LINEBELOW', (0, row_index + 1), (-1, row_index + 1), 0.5, border_gray))

    invoice_table = Table(table_rows, colWidths=col_widths)
    invoice_table.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0), light_gray),
        ('TOPPADDING',    (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING',   (0, 0), (-1, -1), 8),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 8),
        ('LINEBELOW',     (0, 0), (-1, 0), 1, border_gray),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        *line_styles,
    ]))
    story.append(invoice_table)

    # --- Totals ---
    subtotal = sum(item.amount for item in data.line_items)
    tax_amount = subtotal * data.tax_rate
    total = subtotal + tax_amount
    tax_label = f"Tax ({data.tax_rate * 100:g}%)"

    totals_table = Table(
        [
            ["", Paragraph("Subtotal",  subtotal_lbl), Paragraph(f"${subtotal:,.2f}",   subtotal_val)],
            ["", Paragraph(tax_label,   subtotal_lbl), Paragraph(f"${tax_amount:,.2f}", subtotal_val)],
            ["", Paragraph("Total Due", total_lbl),    Paragraph(f"${total:,.2f}",       total_val)],
        ],
        colWidths=[3.5 * inch, 1.75 * inch, 1.75 * inch],
    )
    totals_table.setStyle(TableStyle([
        ('TOPPADDING',    (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING',   (0, 0), (-1, -1), 8),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 8),
        ('LINEABOVE',     (1, 2), (-1, 2), 1, border_gray),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(totals_table)
    story.append(Spacer(1, 30))

    story.append(HRFlowable(width="100%", thickness=1, color=border_gray))
    story.append(Spacer(1, 16))
    story.append(Paragraph("Thank you for your business.", footer_style))

    doc.build(story)
    return output_path


# ---------------------------------------------------------------------------
# Interactive prompt
# ---------------------------------------------------------------------------

def prompt_line_items() -> List[LineItem]:
    items = []
    print("\nEnter line items (leave description blank to finish):")
    while True:
        desc = input("  Description (e.g. 'For January and February'): ").strip()
        if not desc:
            if not items:
                print("  At least one line item is required.")
                continue
            break
        detail = input("  Detail (e.g. 'Hourly rate @ $200'): ").strip()
        qty    = float(input("  Quantity (hours/units): ").strip())
        rate   = float(input("  Rate ($): ").strip())
        items.append(LineItem(description=desc, detail=detail, qty=qty, rate=rate))
    return items


def main():
    print("=== Invoice Generator ===\n")

    # Sender
    print("-- Your Info --")
    name    = input("Your name: ").strip()
    address = input("Your address: ").strip()
    email   = input("Your email: ").strip()

    # Client
    print("\n-- Client Info --")
    client_name = input("Client name: ").strip()

    # Invoice meta
    print("\n-- Invoice Details --")
    inv_number = input("Invoice number (e.g. 001): ").strip()
    default_date = date.today().strftime("%B %-d, %Y") if os.name != "nt" else date.today().strftime("%B %d, %Y").replace(" 0", " ")
    inv_date = input(f"Invoice date [{default_date}]: ").strip() or default_date
    tax_input = input("Tax rate % (e.g. 8 for 8%, 0 for none) [0]: ").strip()
    tax_rate = float(tax_input) / 100 if tax_input else 0.0

    # Output
    print("\n-- Output --")
    output_dir = input("Output directory [.]: ").strip() or "."

    # Line items
    line_items = prompt_line_items()

    data = InvoiceData(
        sender=Sender(name=name, address=address, email=email),
        client_name=client_name,
        invoice_number=inv_number,
        invoice_date=inv_date,
        line_items=line_items,
        tax_rate=tax_rate,
        output_dir=output_dir,
    )

    path = generate_invoice(data)
    print(f"\nInvoice saved to: {path}")


if __name__ == "__main__":
    main()
