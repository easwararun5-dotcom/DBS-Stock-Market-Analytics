"""
report_utils.py - Professional Styling and Component Helpers for python-docx
Tailored for Academic DBMS Reports (BACSE202 - Fall Semester 2026-2027)
"""

import os
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import nsdecls, qn

# Color Palette Constants
COLOR_NAVY_HEX = "1B365D"       # Deep Academic Navy
COLOR_NAVY_RGB = RGBColor(0x1B, 0x36, 0x5D)

COLOR_SLATE_HEX = "24406B"      # Secondary Slate Navy
COLOR_SLATE_RGB = RGBColor(0x24, 0x40, 0x6B)

COLOR_CHARCOAL_HEX = "334E68"   # Tertiary Heading Charcoal
COLOR_CHARCOAL_RGB = RGBColor(0x33, 0x4E, 0x68)

COLOR_BODY_HEX = "222222"       # Main Text Dark
COLOR_BODY_RGB = RGBColor(0x22, 0x22, 0x22)

COLOR_MUTED_HEX = "627D98"      # Caption / Subtitle Muted Gray
COLOR_MUTED_RGB = RGBColor(0x62, 0x7D, 0x98)

COLOR_ACCENT_HEX = "0D6EFD"     # Interactive Accent Blue
COLOR_ACCENT_RGB = RGBColor(0x0D, 0x6E, 0xFD)

COLOR_ZEBRA_HEX = "F8F9FA"      # Alternating Table Row Light Gray
COLOR_CODE_BG_HEX = "F4F5F7"    # Monospace Code Background
COLOR_BORDER_HEX = "D1D5DB"     # Table Border Gray


def setup_document_styles(doc: Document):
    """Configures global document margins, default typography, and running headers/footers."""
    # 1-inch margins on all sides
    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)
        section.different_first_page_header_footer = True
        
        # Configure Header (for pages 2+)
        header = section.header
        hp = header.paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        hrun = hp.add_run("BACSE202 DBMS Project Report | Stock Market Analytics & Portfolio Management System")
        hrun.font.name = "Calibri"
        hrun.font.size = Pt(8.5)
        hrun.font.italic = True
        hrun.font.color.rgb = COLOR_MUTED_RGB
        
        # Configure Footer (for pages 2+)
        footer = section.footer
        fp = footer.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        
        # Left-aligned institutional note and right-aligned page number
        frun_inst = fp.add_run("Vellore Institute of Technology • School of Computer Science & Engineering\tPage ")
        frun_inst.font.name = "Calibri"
        frun_inst.font.size = Pt(9.0)
        frun_inst.font.color.rgb = COLOR_MUTED_RGB
        
        # XML Page Number Field
        fldChar1 = parse_xml(r'<w:fldChar %s w:fldCharType="begin"/>' % nsdecls('w'))
        instrText = parse_xml(r'<w:instrText %s xml:space="preserve"> PAGE </w:instrText>' % nsdecls('w'))
        fldChar2 = parse_xml(r'<w:fldChar %s w:fldCharType="separate"/>' % nsdecls('w'))
        fldChar3 = parse_xml(r'<w:fldChar %s w:fldCharType="end"/>' % nsdecls('w'))
        
        p_elm = fp._p
        run_pg = fp.add_run()
        run_pg.font.name = "Calibri"
        run_pg.font.size = Pt(9.0)
        run_pg.font.bold = True
        run_pg.font.color.rgb = COLOR_NAVY_RGB
        run_pg._r.append(fldChar1)
        run_pg._r.append(instrText)
        run_pg._r.append(fldChar2)
        run_pg._r.append(fldChar3)


def add_h1(doc: Document, text: str):
    """Adds a major Chapter / Section Heading 1."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(16)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.keep_with_next = True
    run = p.add_run(text)
    run.font.name = "Calibri"
    run.font.size = Pt(18.0)
    run.font.bold = True
    run.font.color.rgb = COLOR_NAVY_RGB
    return p


def add_h2(doc: Document, text: str):
    """Adds a Sub-Section Heading 2."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.keep_with_next = True
    run = p.add_run(text)
    run.font.name = "Calibri"
    run.font.size = Pt(14.0)
    run.font.bold = True
    run.font.color.rgb = COLOR_SLATE_RGB
    return p


def add_h3(doc: Document, text: str):
    """Adds a Sub-Sub-Section Heading 3."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.keep_with_next = True
    run = p.add_run(text)
    run.font.name = "Calibri"
    run.font.size = Pt(12.0)
    run.font.bold = True
    run.font.color.rgb = COLOR_CHARCOAL_RGB
    return p


def add_body_p(doc: Document, text: str, bold_prefix: str = None, italic_prefix: str = None):
    """Adds a standard body paragraph with 1.15 line spacing and 6pt after."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.line_spacing = 1.15
    
    if bold_prefix:
        brun = p.add_run(bold_prefix)
        brun.font.name = "Calibri"
        brun.font.size = Pt(11.0)
        brun.font.bold = True
        brun.font.color.rgb = COLOR_NAVY_RGB
        
    if italic_prefix:
        irun = p.add_run(italic_prefix)
        irun.font.name = "Calibri"
        irun.font.size = Pt(11.0)
        irun.font.italic = True
        irun.font.color.rgb = COLOR_SLATE_RGB
        
    run = p.add_run(text)
    run.font.name = "Calibri"
    run.font.size = Pt(11.0)
    run.font.color.rgb = COLOR_BODY_RGB
    return p


def add_bullet_p(doc: Document, text: str, bold_prefix: str = None, level: int = 0):
    """Adds a cleanly formatted bullet point."""
    p = doc.add_paragraph(style='List Bullet')
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.12
    p.paragraph_format.left_indent = Inches(0.25 * (level + 1))
    
    if bold_prefix:
        brun = p.add_run(bold_prefix)
        brun.font.name = "Calibri"
        brun.font.size = Pt(10.5)
        brun.font.bold = True
        brun.font.color.rgb = COLOR_NAVY_RGB
        
    run = p.add_run(text)
    run.font.name = "Calibri"
    run.font.size = Pt(10.5)
    run.font.color.rgb = COLOR_BODY_RGB
    return p


def add_callout_box(doc: Document, text: str, title: str = "ARCHITECTURAL TAKEAWAY", border_color: str = COLOR_NAVY_HEX, fill_color: str = "F0F4F8"):
    """Adds an academic callout / note block with custom left bar and shaded background."""
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False
    tbl.columns[0].width = Inches(6.5)
    
    cell = tbl.cell(0, 0)
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_color}"/>')
    tcBorders = parse_xml(f'<w:tcBorders {nsdecls("w")}><w:left w:val="single" w:sz="36" w:space="0" w:color="{border_color}"/><w:top w:val="none"/><w:right w:val="none"/><w:bottom w:val="none"/></w:tcBorders>')
    tcMar = parse_xml(f'<w:tcMar {nsdecls("w")}><w:top w:w="120" w:type="dxa"/><w:bottom w:w="120" w:type="dxa"/><w:left w:w="200" w:type="dxa"/><w:right w:w="200" w:type="dxa"/></w:tcMar>')
    tcPr.append(shd)
    tcPr.append(tcBorders)
    tcMar_existing = tcPr.find(qn('w:tcMar'))
    if tcMar_existing is not None:
        tcPr.remove(tcMar_existing)
    tcPr.append(tcMar)
    
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(2)
    trun = p.add_run(f"■ {title}\n")
    trun.font.name = "Calibri"
    trun.font.size = Pt(10.0)
    trun.font.bold = True
    trun.font.color.rgb = COLOR_NAVY_RGB
    
    crun = p.add_run(text)
    crun.font.name = "Calibri"
    crun.font.size = Pt(10.0)
    crun.font.italic = False
    crun.font.color.rgb = COLOR_BODY_RGB
    
    # Add small spacing after callout table
    sp_p = doc.add_paragraph()
    sp_p.paragraph_format.space_before = Pt(0)
    sp_p.paragraph_format.space_after = Pt(4)


def add_code_block(doc: Document, code_text: str, caption: str = None):
    """Adds a syntax-formatted monospace code block inside a shaded container."""
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False
    tbl.columns[0].width = Inches(6.5)
    
    cell = tbl.cell(0, 0)
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{COLOR_CODE_BG_HEX}"/>')
    tcBorders = parse_xml(f'<w:tcBorders {nsdecls("w")}><w:left w:val="single" w:sz="24" w:space="0" w:color="{COLOR_NAVY_HEX}"/><w:top w:val="single" w:sz="4" w:space="0" w:color="{COLOR_BORDER_HEX}"/><w:right w:val="single" w:sz="4" w:space="0" w:color="{COLOR_BORDER_HEX}"/><w:bottom w:val="single" w:sz="4" w:space="0" w:color="{COLOR_BORDER_HEX}"/></w:tcBorders>')
    tcMar = parse_xml(f'<w:tcMar {nsdecls("w")}><w:top w:w="120" w:type="dxa"/><w:bottom w:w="120" w:type="dxa"/><w:left w:w="160" w:type="dxa"/><w:right w:w="160" w:type="dxa"/></w:tcMar>')
    tcPr.append(shd)
    tcPr.append(tcBorders)
    tcMar_existing = tcPr.find(qn('w:tcMar'))
    if tcMar_existing is not None:
        tcPr.remove(tcMar_existing)
    tcPr.append(tcMar)
    
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = 1.05
    run = p.add_run(code_text.strip())
    run.font.name = "Consolas"
    run.font.size = Pt(8.5)
    run.font.color.rgb = RGBColor(0x1F, 0x24, 0x2E)
    
    if caption:
        cap_p = doc.add_paragraph()
        cap_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap_p.paragraph_format.space_before = Pt(2)
        cap_p.paragraph_format.space_after = Pt(6)
        cap_run = cap_p.add_run(caption)
        cap_run.font.name = "Calibri"
        cap_run.font.size = Pt(9.5)
        cap_run.font.italic = True
        cap_run.font.color.rgb = COLOR_MUTED_RGB
    else:
        sp_p = doc.add_paragraph()
        sp_p.paragraph_format.space_before = Pt(0)
        sp_p.paragraph_format.space_after = Pt(4)


def add_figure(doc: Document, image_path: str, caption_text: str, width: Inches = Inches(6.2)):
    """Inserts a centered image with a professional academic figure caption."""
    if not os.path.exists(image_path):
        add_callout_box(doc, f"Image not found at path: {image_path}", title="IMAGE MISSING", border_color="CC0000")
        return
        
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(4)
    run = p.add_run()
    run.add_picture(image_path, width=width)
    
    cap_p = doc.add_paragraph()
    cap_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap_p.paragraph_format.space_before = Pt(2)
    cap_p.paragraph_format.space_after = Pt(10)
    cap_p.paragraph_format.keep_with_next = False
    
    c_run_bold = cap_p.add_run("Figure: ")
    c_run_bold.font.name = "Calibri"
    c_run_bold.font.size = Pt(9.5)
    c_run_bold.font.bold = True
    c_run_bold.font.color.rgb = COLOR_NAVY_RGB
    
    c_run = cap_p.add_run(caption_text)
    c_run.font.name = "Calibri"
    c_run.font.size = Pt(9.5)
    c_run.font.italic = True
    c_run.font.color.rgb = COLOR_MUTED_RGB


def create_styled_table(doc: Document, headers: list, data: list, col_widths: list = None):
    """
    Creates an academic-grade formatted table with:
    - Dark Navy Header row (#1B365D) with white bold text
    - Alternating Zebra rows (#F8F9FA)
    - Subtle cell borders (#D1D5DB)
    - Padded cell margins
    - Repeated header row across page boundaries (tblHeader)
    - Row cantSplit property enabled to avoid awkward mid-row breaks
    """
    tbl = doc.add_table(rows=len(data) + 1, cols=len(headers))
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False
    
    # Format Header Row
    hdr_cells = tbl.rows[0].cells
    hdr_tr = tbl.rows[0]._tr.get_or_add_trPr()
    hdr_tr.append(parse_xml(f'<w:tblHeader {nsdecls("w")}/>'))
    hdr_tr.append(parse_xml(f'<w:cantSplit {nsdecls("w")}/>'))
    
    for i, header_text in enumerate(headers):
        cell = hdr_cells[i]
        if col_widths and i < len(col_widths):
            cell.width = col_widths[i]
            
        tcPr = cell._tc.get_or_add_tcPr()
        shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{COLOR_NAVY_HEX}"/>')
        tcPr.append(shd)
        
        tcMar = parse_xml(f'<w:tcMar {nsdecls("w")}><w:top w:w="120" w:type="dxa"/><w:bottom w:w="120" w:type="dxa"/><w:left w:w="140" w:type="dxa"/><w:right w:w="140" w:type="dxa"/></w:tcMar>')
        tcPr.append(tcMar)
        
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        run = p.add_run(str(header_text))
        run.font.name = "Calibri"
        run.font.size = Pt(9.5)
        run.font.bold = True
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        
    # Format Data Rows
    for row_idx, row_data in enumerate(data):
        row_cells = tbl.rows[row_idx + 1].cells
        tr = tbl.rows[row_idx + 1]._tr.get_or_add_trPr()
        tr.append(parse_xml(f'<w:cantSplit {nsdecls("w")}/>'))
        
        is_even = (row_idx % 2 == 1)
        row_fill = COLOR_ZEBRA_HEX if is_even else "FFFFFF"
        
        for col_idx, cell_value in enumerate(row_data):
            cell = row_cells[col_idx]
            if col_widths and col_idx < len(col_widths):
                cell.width = col_widths[col_idx]
                
            tcPr = cell._tc.get_or_add_tcPr()
            if row_fill != "FFFFFF":
                shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{row_fill}"/>')
                tcPr.append(shd)
                
            tcBorders = parse_xml(f'<w:tcBorders {nsdecls("w")}><w:top w:val="single" w:sz="4" w:space="0" w:color="{COLOR_BORDER_HEX}"/><w:bottom w:val="single" w:sz="4" w:space="0" w:color="{COLOR_BORDER_HEX}"/><w:left w:val="none"/><w:right w:val="none"/></w:tcBorders>')
            tcPr.append(tcBorders)
            
            tcMar = parse_xml(f'<w:tcMar {nsdecls("w")}><w:top w:w="90" w:type="dxa"/><w:bottom w:w="90" w:type="dxa"/><w:left w:w="140" w:type="dxa"/><w:right w:w="140" w:type="dxa"/></w:tcMar>')
            tcPr.append(tcMar)
            
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.1
            run = p.add_run(str(cell_value))
            run.font.name = "Calibri"
            run.font.size = Pt(9.0)
            run.font.color.rgb = COLOR_BODY_RGB
            
    # Add spacing after table
    sp_p = doc.add_paragraph()
    sp_p.paragraph_format.space_before = Pt(0)
    sp_p.paragraph_format.space_after = Pt(6)
    return tbl

