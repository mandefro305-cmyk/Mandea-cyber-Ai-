import io
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

def generate_pdf_audit_report(filename: str, findings: list[str], patch_diff: str = "") -> bytes:
    """
    Generates a PDF audit report byte stream using ReportLab.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=22,
        leading=26,
        textColor=colors.HexColor('#1E293B'),
        spaceAfter=12
    )
    heading_style = ParagraphStyle(
        'DocHeading',
        parent=styles['Heading2'],
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#0F172A'),
        spaceBefore=14,
        spaceAfter=8
    )
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#334155')
    )
    code_style = ParagraphStyle(
        'DocCode',
        parent=styles['Code'],
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#0284C7'),
        backColor=colors.HexColor('#F1F5F9')
    )

    elements = []

    # Title & Metadata
    elements.append(Paragraph("🛡️ Security Audit Report", title_style))
    elements.append(Paragraph(f"<b>Target File:</b> {filename}", body_style))
    elements.append(Paragraph(f"<b>Total Findings:</b> {len(findings)}", body_style))
    elements.append(Spacer(1, 15))

    # Findings Table
    elements.append(Paragraph("Automated Vulnerability Findings", heading_style))
    if findings:
        table_data = [["#", "Finding Description"]]
        for idx, f in enumerate(findings, 1):
            table_data.append([str(idx), Paragraph(f, body_style)])

        t = Table(table_data, colWidths=[30, 500])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#E2E8F0')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#0F172A')),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,0), 6),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ]))
        elements.append(t)
    else:
        elements.append(Paragraph("✅ No security vulnerabilities detected.", body_style))

    elements.append(Spacer(1, 15))

    # Suggested Patch Diff
    if patch_diff:
        elements.append(Paragraph("Suggested Remediation Git Patch", heading_style))
        diff_lines = patch_diff.replace("<", "&lt;").replace(">", "&gt;")
        elements.append(Paragraph(f"<font name='Courier'>{diff_lines.replace('\n', '<br/>')}</font>", code_style))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()
