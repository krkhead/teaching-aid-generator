"""Convert a markdown teaching aid into a professional PDF using ReportLab.

Design: Clean editorial layout with accent colour bars, tinted section banners,
a structured cover page, auto-generated table of contents, and clear typographic
hierarchy. Modelled after published curriculum documents.
"""

import re
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from image_gen import (
    extract_image_directives,
    clean_image_directives,
    create_image_placeholder,
    generate_image_gemini,
    should_generate_real_images,
)


# ── Colour palette ──────────────────────────────────────────────────────────

PRIMARY      = "#1a3c5e"   # deep navy
ACCENT       = "#2e7d9c"   # teal accent
DARK         = "#0d1b2a"   # near-black for headings
BODY_TEXT     = "#2c3e50"   # warm dark grey
SUBTLE       = "#5a6d7e"   # secondary text
MUTED        = "#8899a6"   # footer / meta
BORDER       = "#d1d9e0"   # rules and dividers
SECTION_BG   = "#eef3f7"   # light tint behind h2
COVER_BAR    = "#1a3c5e"   # top bar on cover
COVER_BOTTOM = "#2e7d9c"   # bottom bar on cover
WHITE        = "#ffffff"


# ── Styles ──────────────────────────────────────────────────────────────────

def make_styles():
    base = getSampleStyleSheet()
    return {
        # ─ Cover ─
        "cover_type": ParagraphStyle(
            "CoverType", parent=base["BodyText"],
            alignment=TA_CENTER, fontName="Helvetica",
            fontSize=10, leading=12, textColor=colors.HexColor(ACCENT),
            spaceAfter=6, letterSpacing=3,
        ),
        "cover_title": ParagraphStyle(
            "CoverTitle", parent=base["Title"],
            alignment=TA_CENTER, fontName="Helvetica-Bold",
            fontSize=26, leading=32, textColor=colors.HexColor(DARK),
            spaceAfter=8,
        ),
        "cover_subtitle": ParagraphStyle(
            "CoverSubtitle", parent=base["BodyText"],
            alignment=TA_CENTER, fontName="Helvetica",
            fontSize=11, leading=16, textColor=colors.HexColor(SUBTLE),
            spaceAfter=20,
        ),
        "cover_meta": ParagraphStyle(
            "CoverMeta", parent=base["BodyText"],
            alignment=TA_CENTER, fontName="Helvetica",
            fontSize=9.5, leading=14, textColor=colors.HexColor(SUBTLE),
            spaceAfter=3,
        ),
        # ─ TOC ─
        "toc_title": ParagraphStyle(
            "TocTitle", parent=base["Heading1"],
            fontName="Helvetica-Bold", fontSize=16, leading=20,
            textColor=colors.HexColor(PRIMARY), spaceBefore=0, spaceAfter=14,
        ),
        "toc_entry": ParagraphStyle(
            "TocEntry", parent=base["BodyText"],
            fontName="Helvetica", fontSize=10, leading=18,
            textColor=colors.HexColor(BODY_TEXT), leftIndent=4,
        ),
        # ─ Content ─
        "h2": ParagraphStyle(
            "H2", parent=base["Heading2"],
            fontName="Helvetica-Bold", fontSize=14, leading=18,
            textColor=colors.HexColor(PRIMARY),
            spaceBefore=18, spaceAfter=8,
        ),
        "h3": ParagraphStyle(
            "H3", parent=base["Heading3"],
            fontName="Helvetica-Bold", fontSize=11, leading=15,
            textColor=colors.HexColor(ACCENT),
            spaceBefore=12, spaceAfter=5,
        ),
        "body": ParagraphStyle(
            "BodyCustom", parent=base["BodyText"],
            fontName="Helvetica", fontSize=9.6, leading=14,
            alignment=TA_JUSTIFY, textColor=colors.HexColor(BODY_TEXT),
            spaceAfter=6,
        ),
        "bullet": ParagraphStyle(
            "BulletCustom", parent=base["BodyText"],
            fontName="Helvetica", fontSize=9.6, leading=13.5,
            leftIndent=20, firstLineIndent=-12, bulletIndent=6,
            textColor=colors.HexColor(BODY_TEXT), spaceAfter=3,
        ),
        "numbered": ParagraphStyle(
            "NumberedCustom", parent=base["BodyText"],
            fontName="Helvetica", fontSize=9.6, leading=13.5,
            leftIndent=20, firstLineIndent=-12,
            textColor=colors.HexColor(BODY_TEXT), spaceAfter=3,
        ),
        # ─ Special ─
        "label_key": ParagraphStyle(
            "LabelKey", parent=base["BodyText"],
            fontName="Helvetica-Bold", fontSize=9.2, leading=13,
            textColor=colors.HexColor(PRIMARY),
        ),
        "label_val": ParagraphStyle(
            "LabelVal", parent=base["BodyText"],
            fontName="Helvetica", fontSize=9.2, leading=13,
            textColor=colors.HexColor(BODY_TEXT),
        ),
    }


# ── Markdown parser ─────────────────────────────────────────────────────────

def escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def inline_format(text: str) -> str:
    """Convert **bold**, *italic*, and `code` to ReportLab XML."""
    text = escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)
    text = re.sub(r"`(.+?)`", r'<font face="Courier" size="8.5">\1</font>', text)
    return text


def _parse_table_lines(lines: list[str]) -> list[list[str]] | None:
    """Parse raw markdown table lines into a list of rows (each row = list of cell strings).
    Separator rows (|---|---|) are skipped.
    """
    rows = []
    for line in lines:
        if re.match(r"^\|[-:\s|]+\|$", line):
            continue  # skip divider row
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        rows.append(cells)
    return rows if rows else None


def parse_markdown(text: str) -> list[tuple[str, any]]:
    blocks: list[tuple[str, any]] = []
    para_lines: list[str] = []
    table_lines: list[str] = []

    def flush_para():
        nonlocal para_lines
        if para_lines:
            blocks.append(("p", " ".join(para_lines).strip()))
            para_lines = []

    def flush_table():
        nonlocal table_lines
        if table_lines:
            parsed = _parse_table_lines(table_lines)
            if parsed:
                blocks.append(("table", parsed))
            table_lines = []

    for raw in text.splitlines():
        line = raw.rstrip()
        stripped = line.strip()

        if not stripped:
            flush_para()
            flush_table()
            continue

        # Table lines start and end with |
        if stripped.startswith("|") and stripped.endswith("|"):
            flush_para()
            table_lines.append(stripped)
            continue
        else:
            flush_table()

        # Detect image directives
        if re.match(r"\[GENERATE IMAGE:", stripped):
            flush_para()
            m = re.search(r"\[GENERATE IMAGE:\s*(.+?)\]", stripped)
            if m:
                blocks.append(("image", m.group(1).strip()))
            continue
        # Detect image placeholders (after cleaning by image_gen)
        if stripped.startswith("[Image:") and stripped.endswith("]"):
            flush_para()
            blocks.append(("image", stripped[7:-1].strip()))
            continue
        if stripped.startswith("### "):
            flush_para()
            blocks.append(("h3", stripped[4:].strip()))
        elif stripped.startswith("## "):
            flush_para()
            blocks.append(("h2", stripped[3:].strip()))
        elif stripped.startswith("# "):
            flush_para()
            blocks.append(("title", stripped[2:].strip()))
        elif re.match(r"^- ", stripped):
            flush_para()
            blocks.append(("bullet", stripped[2:].strip()))
        elif re.match(r"^\d+\.\s", stripped):
            flush_para()
            m = re.match(r"^(\d+)\.\s+(.*)", stripped)
            blocks.append(("numbered", f"{m.group(1)}. {m.group(2)}"))
        elif stripped.startswith("---"):
            flush_para()
            blocks.append(("hr", ""))
        else:
            para_lines.append(stripped)

    flush_para()
    flush_table()
    return blocks


# ── Helpers ─────────────────────────────────────────────────────────────────

def extract_cover_info(blocks):
    remaining = blocks[:]
    title = subtitle = None
    if remaining and remaining[0][0] == "title":
        title = remaining.pop(0)[1]
    if remaining and remaining[0][0] == "p":
        subtitle = remaining.pop(0)[1]
    return title, subtitle, remaining


def make_section_banner(text: str, styles: dict) -> Table:
    """Create a tinted background banner for ## headings."""
    para = Paragraph(inline_format(text), styles["h2"])
    t = Table([[para]], colWidths=[16.4 * cm], rowHeights=[None])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(SECTION_BG)),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("ROUNDEDCORNERS", [3, 3, 3, 3]),
    ]))
    return t


def make_label_row(key: str, value: str, styles: dict) -> Table:
    """Create a key: value row used in structured sections (lesson plans, etc.)."""
    k = Paragraph(f"<b>{escape(key)}</b>", styles["label_key"])
    v = Paragraph(inline_format(value), styles["label_val"])
    t = Table([[k, v]], colWidths=[4 * cm, 12.4 * cm])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (0, 0), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return t


def detect_label_line(text: str) -> tuple[str, str] | None:
    """Detect lines like 'Topic: Algebra' or 'Duration: 2 hours'."""
    m = re.match(r"^([A-Z][A-Za-z\s/]+?):\s+(.+)$", text)
    if m and len(m.group(1)) < 35:
        return m.group(1).strip(), m.group(2).strip()
    return None


# ── PDF builder ─────────────────────────────────────────────────────────────

def build_pdf(
    md_path: Path,
    pdf_path: Path | None = None,
    doc_type_label: str = "Professional Teaching Aid",
    meta_lines: list[str] | None = None,
):
    if pdf_path is None:
        pdf_path = md_path.with_suffix(".pdf")

    styles = make_styles()
    text = md_path.read_text(encoding="utf-8")

    # Extract image directives and convert to placeholder format for parsing
    image_directives = extract_image_directives(text)
    if image_directives:
        print(f"  Found {len(image_directives)} image directive(s)")

    # Clean image directives to placeholder format for markdown parsing
    text = clean_image_directives(text)

    blocks = parse_markdown(text)
    title, subtitle, content_blocks = extract_cover_info(blocks)
    short_title = (title or "Teaching Aid")[:60]

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.6 * cm,
        title=title or "Teaching Aid",
        author="Teaching Aid Generator",
    )

    story: list = []

    # ════════════════════════════════════════════════════════════════
    #  COVER PAGE
    # ════════════════════════════════════════════════════════════════

    story.append(Spacer(1, 4 * cm))

    # Document type label (small caps style)
    type_text = doc_type_label.upper()
    story.append(Paragraph(type_text, styles["cover_type"]))
    story.append(Spacer(1, 0.3 * cm))

    # Accent rule under the type label
    rule_data = [[""]]
    rule = Table(rule_data, colWidths=[6 * cm], rowHeights=[0.5])
    rule.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, 0), 2, colors.HexColor(ACCENT)),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    # Centre the rule
    outer = Table([[rule]], colWidths=[16.4 * cm])
    outer.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    story.append(outer)
    story.append(Spacer(1, 0.5 * cm))

    # Title
    story.append(Paragraph(escape(title or "Teaching Aid"), styles["cover_title"]))

    # Subtitle
    if subtitle:
        story.append(Paragraph(inline_format(subtitle), styles["cover_subtitle"]))

    story.append(Spacer(1, 1.2 * cm))

    # Meta info box
    if meta_lines:
        meta_rows = []
        for line in meta_lines:
            meta_rows.append([Paragraph(escape(line), styles["cover_meta"])])
        mt = Table(meta_rows, colWidths=[12 * cm])
        mt.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        outer_mt = Table([[mt]], colWidths=[16.4 * cm])
        outer_mt.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
        story.append(outer_mt)

    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════
    #  TABLE OF CONTENTS
    # ════════════════════════════════════════════════════════════════

    h2_titles = [c for k, c in content_blocks if k == "h2"]
    if h2_titles:
        story.append(Paragraph("Contents", styles["toc_title"]))

        # Thin rule under "Contents"
        toc_rule = Table([[""]], colWidths=[16.4 * cm], rowHeights=[0.5])
        toc_rule.setStyle(TableStyle([
            ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor(BORDER)),
        ]))
        story.append(toc_rule)
        story.append(Spacer(1, 0.4 * cm))

        for i, t in enumerate(h2_titles, 1):
            entry_text = f'<font color="{ACCENT}"><b>{i}.</b></font>  {escape(t)}'
            story.append(Paragraph(entry_text, styles["toc_entry"]))

        story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════
    #  CONTENT PAGES
    # ════════════════════════════════════════════════════════════════

    for kind, content in content_blocks:
        if kind == "title":
            story.append(Spacer(1, 0.5 * cm))
            story.append(Paragraph(escape(content), styles["cover_title"]))
            story.append(Spacer(1, 0.3 * cm))

        elif kind == "h2":
            banner = make_section_banner(content, styles)
            story.append(Spacer(1, 0.3 * cm))
            story.append(banner)
            story.append(Spacer(1, 0.2 * cm))

        elif kind == "h3":
            # Accent left-bar effect via a small coloured prefix
            h3_text = (
                f'<font color="{ACCENT}">\u2503</font>  '
                + inline_format(content)
            )
            story.append(Paragraph(h3_text, styles["h3"]))

        elif kind == "bullet":
            story.append(Paragraph(
                inline_format(content), styles["bullet"],
                bulletText="\u2022",
            ))

        elif kind == "numbered":
            story.append(Paragraph(inline_format(content), styles["numbered"]))

        elif kind == "image":
            story.append(Spacer(1, 0.3 * cm))

            # Try real image generation if enabled, fall back to placeholder
            img_element = None
            if should_generate_real_images():
                try:
                    print(f"  Generating image: {content[:60]}...")
                    img_bytes = generate_image_gemini(content)
                    if img_bytes:
                        from io import BytesIO
                        from reportlab.platypus import Image
                        img_io = BytesIO(img_bytes)
                        img_element = Image(img_io, width=14 * cm, height=9 * cm)
                except Exception as e:
                    print(f"  [!] Real image generation failed, using placeholder: {e}")

            if img_element:
                story.append(img_element)
            else:
                # Fallback to styled placeholder
                placeholder = create_image_placeholder(content, width=14 * cm, height=9 * cm)
                story.append(placeholder)

            story.append(Spacer(1, 0.3 * cm))

        elif kind == "hr":
            story.append(Spacer(1, 0.25 * cm))
            hr = Table([[""]], colWidths=[16.4 * cm], rowHeights=[0.5])
            hr.setStyle(TableStyle([
                ("LINEBELOW", (0, 0), (-1, 0), 0.4, colors.HexColor(BORDER)),
            ]))
            story.append(hr)
            story.append(Spacer(1, 0.25 * cm))

        elif kind == "table":
            rows = content  # list[list[str]]
            if not rows:
                continue
            col_count = max(len(r) for r in rows)
            # Pad all rows to the same width
            rows = [r + [""] * (col_count - len(r)) for r in rows]
            col_width = 16.4 * cm / col_count

            # Header row in bold white-on-navy; data rows plain body text
            table_data = []
            for i, row in enumerate(rows):
                cell_style = styles["label_key"] if i == 0 else styles["body"]
                table_data.append(
                    [Paragraph(inline_format(cell), cell_style) for cell in row]
                )

            ts = TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(PRIMARY)),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor(BORDER)),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ])
            # Alternating row tint for readability
            for i in range(1, len(rows)):
                if i % 2 == 0:
                    ts.add("BACKGROUND", (0, i), (-1, i), colors.HexColor(SECTION_BG))

            t = Table(table_data, colWidths=[col_width] * col_count)
            t.setStyle(ts)
            story.append(Spacer(1, 0.2 * cm))
            story.append(t)
            story.append(Spacer(1, 0.3 * cm))

        else:  # paragraph
            # Detect structured "Key: Value" lines and render as label rows
            label = detect_label_line(content)
            if label:
                story.append(make_label_row(label[0], label[1], styles))
            else:
                story.append(Paragraph(inline_format(content), styles["body"]))

    # ════════════════════════════════════════════════════════════════
    #  PAGE DECORATIONS
    # ════════════════════════════════════════════════════════════════

    def draw_cover(canvas, document):
        w, h = A4
        canvas.saveState()
        # Top bar
        canvas.setFillColor(colors.HexColor(COVER_BAR))
        canvas.rect(0, h - 1.4 * cm, w, 1.4 * cm, fill=1, stroke=0)
        # Thin accent line below top bar
        canvas.setStrokeColor(colors.HexColor(ACCENT))
        canvas.setLineWidth(2)
        canvas.line(0, h - 1.4 * cm, w, h - 1.4 * cm)
        # Bottom bar
        canvas.setFillColor(colors.HexColor(COVER_BOTTOM))
        canvas.rect(0, 0, w, 0.8 * cm, fill=1, stroke=0)
        # Left accent strip
        canvas.setFillColor(colors.HexColor(ACCENT))
        canvas.rect(0, 0.8 * cm, 4 * mm, h - 2.2 * cm, fill=1, stroke=0)
        canvas.restoreState()

    def draw_pages(canvas, document):
        w, h = A4
        canvas.saveState()
        # Top line
        canvas.setStrokeColor(colors.HexColor(BORDER))
        canvas.setLineWidth(0.5)
        canvas.line(
            document.leftMargin, h - 1.2 * cm,
            w - document.rightMargin, h - 1.2 * cm,
        )
        # Header text
        canvas.setFont("Helvetica-Bold", 8)
        canvas.setFillColor(colors.HexColor(PRIMARY))
        canvas.drawString(document.leftMargin, h - 1.0 * cm, short_title)
        # Small accent dot after header
        canvas.setFillColor(colors.HexColor(ACCENT))
        tw = canvas.stringWidth(short_title, "Helvetica-Bold", 8)
        canvas.circle(
            document.leftMargin + tw + 6, h - 0.95 * cm, 1.5, fill=1, stroke=0,
        )
        # Footer line
        canvas.setStrokeColor(colors.HexColor(BORDER))
        canvas.line(
            document.leftMargin, 1.1 * cm,
            w - document.rightMargin, 1.1 * cm,
        )
        # Page number
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor(MUTED))
        canvas.drawRightString(
            w - document.rightMargin, 0.65 * cm,
            f"Page {canvas.getPageNumber()}",
        )
        # Left accent strip on content pages
        canvas.setFillColor(colors.HexColor(ACCENT))
        canvas.rect(0, 0, 2.5 * mm, h, fill=1, stroke=0)
        canvas.restoreState()

    doc.build(story, onFirstPage=draw_cover, onLaterPages=draw_pages)
    return pdf_path


# ── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_pdf.py <markdown_file> [output.pdf]")
        sys.exit(1)

    md = Path(sys.argv[1])
    if not md.exists():
        print(f"File not found: {md}")
        sys.exit(1)

    out = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    result = build_pdf(md, out)
    print(f"PDF generated: {result}")
