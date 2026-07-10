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
    _final = appraisal.get("final_value")
    final_val = (
        f"{appraisal.get('currency','USD')} {_final:,.2f}"
        if _final is not None else "Pendiente de firma"
    )
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


def generate_monthly_report_pdf(report: dict, brand: dict) -> bytes:
    """Informe de reporte mensual (WO F4-03).

    `report` = dict con los campos reales de un `monthly_report` (code,
    region, kind, period_year, period_month, source, tasar_index,
    median_price_per_m2, yoy_change_pct, mom_change_pct, active_listings,
    avg_days_on_market, new_permits, sample_size, top_zones: list[dict]).
    NO se inventan datos: todo KPI ausente (None) se muestra "-". `brand`
    = {name, subtitle} del workspace/producto.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=1.8 * cm, bottomMargin=1.8 * cm,
    )
    styles = getSampleStyleSheet()
    brand_style = ParagraphStyle(
        "brand", parent=styles["Heading1"], fontSize=16,
        textColor=colors.HexColor("#0f172a"), spaceAfter=2,
    )
    title = ParagraphStyle(
        "title", parent=styles["Heading1"], fontSize=20,
        textColor=colors.HexColor("#1e293b"), spaceAfter=8,
    )
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=13,
                         textColor=colors.HexColor("#1e293b"), spaceBefore=14)
    normal = styles["BodyText"]
    small = ParagraphStyle("small", parent=styles["BodyText"], fontSize=8,
                            textColor=colors.HexColor("#64748b"))

    MONTHS_ES = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                 "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

    def _n(v, suffix="") -> str:
        return "-" if v is None else f"{v}{suffix}"

    month_label = MONTHS_ES[report["period_month"]] if 1 <= report.get("period_month", 0) <= 12 else "-"

    story = []
    story.append(Paragraph(brand.get("name", "TasAR"), brand_style))
    story.append(Paragraph(brand.get("subtitle", "Inteligencia de mercado inmobiliario"), small))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(f"REPORTE {report.get('kind', 'mensual').upper()}", title))
    story.append(Paragraph(
        f"Edicion {report.get('code', '-')} &nbsp;|&nbsp; {month_label} {report.get('period_year', '-')} "
        f"&nbsp;|&nbsp; Region: {report.get('region', '-')}", normal))
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("1. Indicadores", h2))
    data = [
        ["Indice TasAR", _n(report.get("tasar_index"))],
        ["Mediana USD/m2", _n(report.get("median_price_per_m2"))],
        ["Variacion interanual (YoY)", _n(report.get("yoy_change_pct"), "%")],
        ["Variacion mensual (MoM)", _n(report.get("mom_change_pct"), "%")],
        ["Oferta activa", _n(report.get("active_listings"))],
        ["Dias promedio en mercado", _n(report.get("avg_days_on_market"))],
        ["Permisos de obra nueva", _n(report.get("new_permits"))],
        ["Avisos usados en el calculo", _n(report.get("sample_size"))],
    ]
    t = Table(data, colWidths=[7 * cm, 9 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f1f5f9")),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(t)

    top_zones = report.get("top_zones") or []
    if top_zones:
        story.append(Paragraph("2. Top zonas", h2))
        rows = [["#", "Zona", "USD/m2", "Avisos"]]
        for i, z in enumerate(top_zones[:12], 1):
            rows.append([
                i, z.get("zone", "-"),
                f"{z.get('usd_m2', '-')}",
                f"{z.get('listings_count', '-')}",
            ])
        zt = Table(rows, repeatRows=1, colWidths=[1 * cm, 7 * cm, 4 * cm, 4 * cm])
        zt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3b82f6")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
        ]))
        story.append(zt)

    story.append(Spacer(1, 0.6 * cm))
    if report.get("source") == "custom":
        story.append(Paragraph(
            "Reporte generado agregando avisos activos reales de TasAR Market "
            "(market_listings) para la region, tipo y periodo solicitados.", small))
    else:
        story.append(Paragraph(
            "[DEMO] Reporte de referencia generado con datos de ejemplo (seed), no es una "
            "agregacion en vivo. Para un analisis en tiempo real, usa el buscador de "
            "Comparables o generá un reporte custom.", small))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def generate_express_valuation_pdf(
    valuation: dict,
    anchor: dict | None,
    brand: dict,
) -> bytes:
    """Informe de Tasacion Express anclada (WO F1-03), brandeado por workspace.

    2 paginas:
      1) Marca + datos del inmueble + valor + rango + factores (a favor / en contra)
      2) Top comparables reales usados como ancla + alcance (scope) + confianza.

    `valuation` = contrato del endpoint /api/valuations/express (bandas, totales,
    factores, estrategia, scope, ai_used). `anchor` = ancla usada (o None si no
    hubo datos). `brand` = {name, subtitle} del workspace. NO se inventan datos:
    si un campo falta, se muestra "-".
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=1.6 * cm, bottomMargin=1.6 * cm,
    )
    styles = getSampleStyleSheet()
    brand_style = ParagraphStyle(
        "brand", parent=styles["Heading1"], fontSize=18,
        textColor=colors.HexColor("#0f172a"), spaceAfter=2,
    )
    title = ParagraphStyle(
        "title", parent=styles["Heading1"], fontSize=22,
        textColor=colors.HexColor("#1e293b"), spaceAfter=8,
    )
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=13,
                        textColor=colors.HexColor("#1e293b"), spaceBefore=14)
    normal = styles["BodyText"]
    small = ParagraphStyle("small", parent=styles["BodyText"], fontSize=8,
                           textColor=colors.HexColor("#64748b"))

    inp = valuation.get("input", {})
    out = valuation.get("output", {})
    ppm2 = out.get("pricePerM2USD", {}) or {}
    total = out.get("totalPriceUSD", {}) or {}
    currency = valuation.get("currency", "USD")

    story = []

    # --- Marca del workspace ---
    story.append(Paragraph(brand.get("name", "TasAR"), brand_style))
    story.append(Paragraph(brand.get("subtitle", "Tasacion express anclada a comparables reales"), small))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("TASACION EXPRESS", title))
    story.append(Paragraph(f"Emitido: {datetime.utcnow().strftime('%d/%m/%Y')}", small))
    story.append(Spacer(1, 0.3 * cm))

    # --- Datos del inmueble ---
    story.append(Paragraph("1. Inmueble evaluado", h2))
    # reportlab no acepta None en celdas: coercionar a "-" (el input_json guarda
    # null en los campos opcionales que el usuario no completo).
    def _cell(v) -> str:
        return "-" if v is None or v == "" else str(v)
    loc = " - ".join(p for p in [inp.get("neighborhood"), inp.get("city"), inp.get("province")] if p) or "-"
    data = [
        ["Tipo", _cell(inp.get("property_type"))],
        ["Ubicacion", loc],
        ["Direccion", _cell(inp.get("address"))],
        ["Superficie total", f"{_cell(inp.get('total_area_m2'))} m2"],
        ["Ambientes", _cell(inp.get("rooms"))],
        ["Dormitorios", _cell(inp.get("bedrooms"))],
        ["Antiguedad", f"{_cell(inp.get('age_years'))} anios"],
        ["Estado", _cell(inp.get("condition"))],
    ]
    t = Table(data, colWidths=[5 * cm, 11 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f1f5f9")),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(t)

    # --- Valor estimado ---
    story.append(Paragraph("2. Valor estimado", h2))
    typical = total.get("typical")
    typical_str = f"{currency} {typical:,.0f}" if typical is not None else "-"
    story.append(Paragraph(f"<b>{typical_str}</b>", title))
    low, high = total.get("low"), total.get("high")
    if low is not None and high is not None:
        story.append(Paragraph(
            f"Rango: {currency} {low:,.0f} - {currency} {high:,.0f}", normal))
    if ppm2.get("typical") is not None:
        story.append(Paragraph(
            f"USD/m2: {ppm2.get('low', '-')} - <b>{ppm2.get('typical')}</b> - {ppm2.get('high', '-')}", normal))
    conf = out.get("confidence")
    method = "IA anclada" if valuation.get("ai_used") else "estimacion deterministica (ancla)"
    story.append(Paragraph(
        f"Confianza: <b>{conf or '-'}</b> &nbsp;|&nbsp; Metodo: {method} &nbsp;|&nbsp; "
        f"Alcance del ancla: <b>{valuation.get('scope', '-')}</b>", small))

    if out.get("marketSummary"):
        story.append(Spacer(1, 0.2 * cm))
        story.append(Paragraph(out["marketSummary"], normal))

    # --- Factores ---
    ups = out.get("factorsUp") or []
    downs = out.get("factorsDown") or []
    if ups or downs:
        story.append(Paragraph("3. Factores", h2))
        rows = [["A favor (+)", "En contra (-)"]]
        for i in range(max(len(ups), len(downs))):
            rows.append([
                ups[i] if i < len(ups) else "",
                downs[i] if i < len(downs) else "",
            ])
        ft = Table(rows, colWidths=[8 * cm, 8 * cm], repeatRows=1)
        ft.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#dcfce7")),
            ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#fee2e2")),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(ft)

    if out.get("commercialStrategy"):
        story.append(Paragraph("4. Estrategia comercial", h2))
        story.append(Paragraph(out["commercialStrategy"], normal))

    # === Pagina 2: comparables reales usados como ancla ===
    story.append(PageBreak())
    story.append(Paragraph("5. Comparables reales usados", h2))
    if anchor and anchor.get("comparables"):
        a_ppm2 = anchor.get("price_per_m2", {})
        story.append(Paragraph(
            f"Alcance: {anchor.get('scope', '-')} &nbsp;|&nbsp; "
            f"{anchor.get('count', '-')} propiedades del segmento similar &nbsp;|&nbsp; "
            f"Mediana USD/m2: {a_ppm2.get('median', '-')}", small))
        story.append(Spacer(1, 0.2 * cm))
        rows = [["#", "Titulo", "Ubicacion", "m2", "USD", "USD/m2"]]
        for i, c in enumerate(anchor["comparables"], 1):
            rows.append([
                i,
                (c.get("title") or "")[:34],
                (c.get("location") or "")[:28],
                f"{c.get('surface_m2', '-'):.0f}" if c.get("surface_m2") else "-",
                f"{c.get('total_price_usd'):,.0f}" if c.get("total_price_usd") else "-",
                f"{c.get('price_per_m2_usd', '-')}",
            ])
        ct = Table(rows, repeatRows=1, colWidths=[0.8 * cm, 5.5 * cm, 4.5 * cm, 1.5 * cm, 2.4 * cm, 1.9 * cm])
        ct.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3b82f6")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(ct)
    else:
        story.append(Paragraph(
            "No se encontraron comparables suficientes en el catalogo para esta "
            "propiedad. El valor es una estimacion preliminar.", normal))

    story.append(Spacer(1, 0.6 * cm))
    story.append(Paragraph(
        "Informe orientativo generado automaticamente a partir de comparables de "
        "mercado. No constituye una tasacion firmada. Para un informe con validez "
        "profesional, genera una tasacion completa.", small))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
