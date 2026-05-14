"""Generación de PDF para Tasaciones con ReportLab."""
import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)


def generate_appraisal_pdf(
    appraisal: dict,
    property_: dict,
    market_study: dict | None,
    comparables: list[dict] | None,
    signer: dict,
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "title", parent=styles["Heading1"],
        fontSize=20, textColor=colors.HexColor("#1e293b"),
        spaceAfter=12,
    )
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=14,
                         textColor=colors.HexColor("#1e293b"), spaceBefore=12)
    normal = styles["BodyText"]

    story = []
    story.append(Paragraph("INFORME DE TASACIÓN", title))
    story.append(Paragraph(f"<b>TasAR</b> — Tasaciones inteligentes", normal))
    story.append(Paragraph(f"Emitido: {datetime.utcnow().strftime('%d/%m/%Y')}", normal))
    story.append(Spacer(1, 0.4 * cm))

    # Datos del inmueble
    story.append(Paragraph("1. Datos del inmueble", h2))
    data = [
        ["Título", property_.get("title", "")],
        ["Tipo", property_.get("property_type", "")],
        ["Dirección", property_.get("address", "")],
        ["Localidad", f"{property_.get('city','')} — {property_.get('province','')}"],
        ["Superficie total", f"{property_.get('total_area_m2','-')} m²"],
        ["Superficie cubierta", f"{property_.get('covered_area_m2','-')} m²"],
        ["Ambientes", property_.get("rooms", "-")],
        ["Antigüedad", f"{property_.get('age_years','-')} años"],
        ["Estado", property_.get("condition", "-")],
    ]
    t = Table(data, colWidths=[5 * cm, 11 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f1f5f9")),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(t)

    # Comparables
    if comparables:
        story.append(Paragraph("2. Comparables analizados", h2))
        rows = [["#", "Título", "m²", "Precio", "Ajustado/m²", "Peso"]]
        for i, c in enumerate(comparables, 1):
            rows.append([
                i, c.get("title", "")[:40],
                f"{c.get('total_area_m2','-')}",
                f"{c.get('currency','USD')} {c.get('price','-')}",
                f"{c.get('adjusted_price_per_m2','-')}",
                f"{c.get('weight','-')}",
            ])
        ct = Table(rows, repeatRows=1)
        ct.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3b82f6")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
        ]))
        story.append(ct)

    # Resultado
    story.append(Paragraph("3. Valor de tasación", h2))
    final_val = f"{appraisal.get('currency','USD')} {appraisal.get('final_value','-'):,.2f}"
    story.append(Paragraph(f"<b>{final_val}</b>", title))
    if market_study:
        story.append(Paragraph(
            f"Rango sugerido por ACM: {appraisal.get('currency','USD')} "
            f"{market_study.get('suggested_value_min','-')} – "
            f"{market_study.get('suggested_value_max','-')} "
            f"(confianza {market_study.get('confidence_score','-')})",
            normal))

    if appraisal.get("methodology"):
        story.append(Paragraph("4. Metodología", h2))
        story.append(Paragraph(appraisal["methodology"], normal))

    if appraisal.get("observations"):
        story.append(Paragraph("5. Observaciones", h2))
        story.append(Paragraph(appraisal["observations"], normal))

    # Firma
    story.append(Spacer(1, 1.5 * cm))
    story.append(Paragraph("_____________________________", normal))
    story.append(Paragraph(f"<b>{signer.get('full_name','')}</b>", normal))
    if signer.get("license_number"):
        story.append(Paragraph(f"Matrícula: {signer['license_number']}", normal))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
