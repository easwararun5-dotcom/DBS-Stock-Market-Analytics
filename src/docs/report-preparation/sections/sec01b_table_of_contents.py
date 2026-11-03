"""
sec01b_table_of_contents.py - Formal Table of Contents
"""

from docx import Document
from docx.shared import Inches, Pt
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
from report_utils import add_h1, add_body_p, create_styled_table

def build_table_of_contents(doc: Document):
    """Renders a structured Table of Contents for universal cross-platform viewing."""
    add_h1(doc, "Table of Contents")
    
    add_body_p(
        doc,
        "This academic report is organized into the following major chapters and syllabus evaluation sections. The structured index below provides immediate cross-platform section navigation:"
    )
    
    headers = ["Section / Chapter", "Title & Key Analytical Topics", "Evaluation Scope"]
    toc_data = [
        ["1. Academic Abstract", "Executive summary of hybrid architecture, 28-chunk hypertable, and ACID ledgers.", "Preliminary"],
        ["2. Keywords", "Technical indexing terms: RDBMS, TimescaleDB, BCNF, Pessimistic Locking, Hypertables.", "Preliminary"],
        ["3. Introduction & Objectives", "Financial data characteristics, 3 core database bottlenecks, formal problem statement, 6 objectives.", "Core Foundations"],
        ["4. Existing Systems Research", "Comparative benchmark of TradingView, Yahoo Finance, Zerodha Kite, and Portfolio Visualizer.", "Literature & Audit"],
        ["5. Requirements Analysis", "Functional Requirements (FR1-FR8), Non-Functional Requirements (NFR1-NFR5), Implementation matrix.", "Specification"],
        ["6. Proposed Architecture", "3-tier architecture, decoupled PostgreSQL and TimescaleDB, Figure 1 diagram, active routing matrix.", "System Design"],
        ["7. Database Design & ER", "Conceptual ER model, Figures 2-4 whiteboard sheets, Figure 5 relational layout, 16 tables full spec.", "Database Design"],
        ["8. Keys & Normalization", "Minimal candidate key proof, table FD sets, 1NF-BCNF proofs, Heath's Theorem, bounded cache.", "Relational Theory"],
        ["9. Implementation Details", "Runtime environment, dual connection pools, row-level pessimistic locking, ML predictive pipeline.", "Implementation"],
        ["10. Important SQL Operations", "10 executable SQL listings: DDL hypertables, time_bucket, multi-table joins, subqueries, triggers.", "SQL Mastery"],
        ["11. Testing & Verification", "Automated test suite breakdown, honest exit code 1 root cause, lifecycle tests, storage, UI checklist.", "Empirical Results"],
        ["12. Discussion", "Decoupled database evaluation, application vs database locking trade-offs, Migration 05 lessons.", "Synthesis"],
        ["13. Conclusion", "Project achievements summary, validation of hypotheses, and BACSE202 curriculum alignment.", "Conclusion"],
        ["14. Limitations & Future Work", "Architectural constraints (static feed, simulated fill) and future roadmap (Kafka, options modeling).", "Future Directions"],
        ["15. References (IEEE Format)", "12 peer-reviewed academic papers, classic database textbooks, and official technical citations.", "Bibliography"],
        ["16. Appendix", "Faculty evaluation checklist alignment matrix verifying 100% assignment criteria coverage.", "Compliance Audit"]
    ]
    
    # 1.8 + 3.6 + 1.1 = 6.50 inches
    create_styled_table(doc, headers, toc_data, [Inches(1.8), Inches(3.6), Inches(1.1)])
    
    # Word Native TOC Field
    p_fld = doc.add_paragraph()
    p_fld.paragraph_format.space_before = Pt(4)
    p_fld.paragraph_format.space_after = Pt(4)
    fldSimple = parse_xml(r'<w:fldSimple %s w:instr="TOC &quot;1-3&quot; \h \z \u"/>' % nsdecls('w'))
    p_fld._p.append(fldSimple)
    
    # Page Break after Table of Contents
    doc.add_page_break()

