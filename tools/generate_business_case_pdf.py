from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

BUSINESS_CASE = {
    'title': 'RoleFit Analyzer - Business Case',
    'subtitle': 'One-page summary for HR decision-makers',
    'sections': [
        ('Executive Summary', 'RoleFit Analyzer automates and standardizes CV screening while producing evidence-based, auditable decisions recruiters can rely on — decreasing time-to-hire, reducing bias, and improving candidate-job fit.'),
        ('Problem', 'Manual CV screening is time-consuming and inconsistent; existing AI solutions often lack an audit trail and evidence; scaling screening during hiring spikes is expensive.'),
        ('Solution', 'An explainable, evidence-first AI pipeline: PDF extraction into session memory, deterministic evidence search, and JSON outputs for ATS integration.'),
        ('Benefits & KPI', 'Saves recruiter time, improves quality of hire, reduces legal risk. KPI examples: time-saved per CV, reduction in time-to-fill, accuracy vs manual screening, % of claims with evidence.'),
        ('Pilot Plan', '6–8 week pilot: setup, controlled trial, integration, and governance. Deliverables: demo environment, integration with ATS, KPI report.'),
        ('Call to Action', 'Sponsor a pilot for a single job family to demonstrate time-and-cost savings and auditability.'),
    ],
}


def build_pdf(target_path: str):
    doc = SimpleDocTemplate(target_path, pagesize=letter, rightMargin=0.4*inch, leftMargin=0.4*inch, topMargin=0.4*inch, bottomMargin=0.4*inch)
    styles = getSampleStyleSheet()
    story = []

    title_style = styles['Heading1']
    title_style.alignment = 1  # center
    title_style.fontSize = 16

    subtitle_style = ParagraphStyle('Subtitle', parent=styles['Normal'], fontSize=10, alignment=1, textColor=colors.grey)
    heading_style = styles['Heading3']
    heading_style.fontSize = 10
    heading_style.spaceBefore = 6
    heading_style.spaceAfter = 3

    body_style = styles['BodyText']
    body_style.fontSize = 9
    body_style.leading = 11

    story.append(Paragraph(BUSINESS_CASE['title'], title_style))
    story.append(Paragraph(BUSINESS_CASE['subtitle'], subtitle_style))
    story.append(Spacer(1, 12))

    # Build a 2-column table layout for compactness
    table_data = []
    col_data = []
    for i, (h, t) in enumerate(BUSINESS_CASE['sections']):
        # Build para
        section = f'<b>{h}</b><br/>{t}'
        p = Paragraph(section, body_style)
        col_data.append(p)
        # Place two sections per row in the table
        if len(col_data) == 2:
            table_data.append(col_data)
            col_data = []
    if col_data:
        # single last column
        col_data.append(Paragraph('', body_style))
        table_data.append(col_data)

    table = Table(table_data, colWidths=[3.55*inch, 3.55*inch], hAlign='LEFT')
    table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LINEBELOW', (0,0), (-1,-1), 0.3, colors.lightgrey),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))

    story.append(table)
    story.append(Spacer(1, 12))

    # small footer
    footer_style = ParagraphStyle('footer', parent=styles['Normal'], fontSize=8, alignment=1, textColor=colors.grey)
    foot = Paragraph('RoleFit Analyzer (Pilot) — Built with Google ADK. Contact engineering for pilot onboarding.', footer_style)
    story.append(foot)

    doc.build(story)


if __name__ == '__main__':
    import os
    out_path = os.path.join('docs', 'RoleFit_Analyzer_Business_Case.pdf')
    build_pdf(out_path)
    print(f"PDF generated at {out_path}")
