"""Personalized TNEA Choice Sheet PDF Generator using ReportLab."""

import os
import re
import time
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from api.core.config import settings
from api.core.logging import get_logger

logger = get_logger(__name__)

PDF_OUTPUT_DIR = os.path.join("data", "choice_sheets")


def generate_tnea_choice_sheet_pdf(
    cutoff: float,
    community: str,
    choices: list[dict[str, Any]],
    session_key: str = "",
) -> tuple[str, str]:
    """Generate a branded, professional PDF choice filling sheet.

    Returns:
        tuple[str, str]: (absolute_file_path, public_download_url)
    """
    os.makedirs(PDF_OUTPUT_DIR, exist_ok=True)

    # Sanitize session key for filename
    clean_id = re.sub(r"[^\w\-]", "_", session_key) if session_key else "guest"
    ts = int(time.time())
    filename = f"TNEA_Choice_Sheet_{clean_id}_{ts}.pdf"
    filepath = os.path.join(PDF_OUTPUT_DIR, filename)

    doc = SimpleDocTemplate(
        filepath,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )
    styles = getSampleStyleSheet()

    # Custom typography
    header_style = ParagraphStyle(
        "HeaderTitle",
        parent=styles["Heading1"],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1E3A8A"),
        alignment=1,
    )
    sub_style = ParagraphStyle(
        "HeaderSub",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#475569"),
        alignment=1,
    )
    meta_style = ParagraphStyle(
        "MetaText",
        parent=styles["Normal"],
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#0F172A"),
    )
    cell_style = ParagraphStyle(
        "CellText",
        parent=styles["Normal"],
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#0F172A"),
    )
    cell_bold = ParagraphStyle(
        "CellBold",
        parent=styles["Normal"],
        fontSize=8,
        leading=11,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#0F172A"),
    )

    elements = []

    # Title & Subtitle
    elements.append(
        Paragraph("🎓 <b>COLIGO TNEA COUNSELLING ASSISTANT</b>", header_style)
    )
    elements.append(
        Paragraph(
            "Official Personalized Choice Filling Preference Draft • "
            "Tamil Nadu Engineering Admissions",
            sub_style,
        )
    )
    elements.append(Spacer(1, 14))

    # Candidate Profile Box
    profile_data = [
        [
            Paragraph(f"<b>Candidate Cutoff:</b> {cutoff:g} / 200.0", meta_style),
            Paragraph(f"<b>Community Quota:</b> {community.upper()}", meta_style),
            Paragraph("<b>System:</b> Coligo AI Multi-College", meta_style),
        ]
    ]
    t_profile = Table(profile_data, colWidths=[180, 180, 180])
    t_profile.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F1F5F9")),
                ("PADDING", (0, 0), (-1, -1), 8),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
            ]
        )
    )
    elements.append(t_profile)
    elements.append(Spacer(1, 14))

    # Table of Choices
    table_headers = [
        Paragraph("<b>#</b>", cell_bold),
        Paragraph("<b>Code</b>", cell_bold),
        Paragraph("<b>College Name</b>", cell_bold),
        Paragraph("<b>Branch / Department</b>", cell_bold),
        Paragraph("<b>Cutoff</b>", cell_bold),
        Paragraph("<b>Tier</b>", cell_bold),
    ]
    table_rows = [table_headers]

    for idx, c in enumerate(choices, 1):
        tier_val = c.get("tier", "Target")
        tier_color = (
            "#D97706"
            if tier_val == "Ambitious"
            else ("#2563EB" if tier_val == "Target" else "#059669")
        )
        tier_markup = f"<font color='{tier_color}'><b>{tier_val}</b></font>"

        row = [
            Paragraph(str(idx), cell_style),
            Paragraph(str(c.get("college_code", "—")), cell_bold),
            Paragraph(str(c.get("college_name", "—")), cell_style),
            Paragraph(str(c.get("branch_name", "—")), cell_style),
            Paragraph(f"<b>{c.get('cutoff_mark', 0):g}</b>", cell_style),
            Paragraph(tier_markup, cell_style),
        ]
        table_rows.append(row)

    col_widths = [24, 40, 200, 160, 50, 66]
    t_choices = Table(table_rows, colWidths=col_widths)
    t_choices.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                ("TOPPADDING", (0, 0), (-1, 0), 6),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#F8FAFC")],
                ),
                ("TOPPADDING", (0, 1), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
            ]
        )
    )
    elements.append(t_choices)
    elements.append(Spacer(1, 16))

    # TNEA Strategy Guidance Notes
    notes_style = ParagraphStyle(
        "NotesStyle",
        parent=styles["Normal"],
        fontSize=8,
        leading=12,
        textColor=colors.HexColor("#334155"),
    )
    notes_title = ParagraphStyle(
        "NotesTitle",
        parent=styles["Normal"],
        fontSize=9,
        leading=13,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#1E3A8A"),
    )

    elements.append(
        Paragraph("📌 <b>Essential TNEA Choice-Filling Rules:</b>", notes_title)
    )
    elements.append(Spacer(1, 4))
    elements.append(
        Paragraph(
            "1. <b>Strict Top-Down Order:</b> TNEA algorithm assigns the very first "
            "seat you qualify for starting from Priority 1. Always place your Dream / "
            "Ambitious choices at the top.",
            notes_style,
        )
    )
    elements.append(
        Paragraph(
            "2. <b>Never Put Safe Choices First:</b> If you place a Safe college at "
            "Priority 1, TNEA will allot it immediately and you will lose all "
            "chances for higher choices.",
            notes_style,
        )
    )
    elements.append(
        Paragraph(
            "3. <b>Lock Your Choices:</b> Once satisfied with your list on "
            "tneaonline.org, lock your choices before 5:00 PM on Day 3.",
            notes_style,
        )
    )

    doc.build(elements)
    logger.info("pdf_choice_sheet_generated", filepath=filepath, filename=filename)

    base_url = (
        settings.WHATSAPP_WEBHOOK_URL.replace("/webhook", "")
        if hasattr(settings, "WHATSAPP_WEBHOOK_URL") and settings.WHATSAPP_WEBHOOK_URL
        else "https://coligo-college-admission-assistant.onrender.com"
    )
    public_url = f"{base_url}/static/choice_sheets/{filename}"

    return filepath, public_url
