#!/usr/bin/env python3
"""
generate_report.py - Master Academic Report Generator for BACSE202 DBMS Project
Stock Market Analytics and Portfolio Management System
Fall Semester 2026-2027 • Vellore Institute of Technology
Faculty Guide: Dr. S. Geetha
Team Members:
  - Easwar A P (25BCE1512)
  - Mohamed Irfan (25BCE1462)
  - Mohammed Nadeem (25BCE1771)
"""

import os
import sys
from docx import Document

# Ensure local report-preparation directory is on sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from report_utils import setup_document_styles
from sections.sec01_title_abstract import build_title_page, build_abstract_and_keywords
from sections.sec02_intro_problem import build_intro_problem_objectives
from sections.sec03_existing_systems import build_existing_systems
from sections.sec04_requirements import build_requirements_analysis
from sections.sec05_architecture import build_system_architecture
from sections.sec06_er_schema import build_er_and_relational_schema
from sections.sec07_keys_normalization import build_keys_and_normalization
from sections.sec08_implementation import build_implementation_details
from sections.sec09_sql_operations import build_sql_operations
from sections.sec10_testing_results import build_testing_and_results
from sections.sec11_discussion_conclusion_refs import build_discussion_conclusion_references


def generate_final_report():
    print("=" * 70)
    print("Generating Academic DBMS Project Report (.docx)...")
    print("Project: Stock Market Analytics and Portfolio Management System")
    print("Course:  BACSE202 - Database Management Systems")
    print("=" * 70)

    # Initialize python-docx Document
    doc = Document()

    # Configure typography, 1-inch margins, and headers/footers
    setup_document_styles(doc)
    print("[1/12] Document styles and running headers/footers configured.")

    # Section 1 & Cover
    build_title_page(doc)
    build_abstract_and_keywords(doc)
    print("[2/12] Title Page, Abstract, and Keywords generated.")

    # Section 2: Intro, Problem, Objectives
    build_intro_problem_objectives(doc)
    print("[3/12] Introduction, Problem Statement, Objectives & Scope built.")

    # Section 3: Existing Systems
    build_existing_systems(doc)
    print("[4/12] Existing Systems Research and Comparative Matrix built.")

    # Section 4: Requirements
    build_requirements_analysis(doc)
    print("[5/12] Requirements Analysis (FR, NFR, Implemented Matrix) built.")

    # Section 5: Architecture
    build_system_architecture(doc)
    print("[6/12] System Architecture and Dynamic Routing Matrix built.")

    # Section 6: ER Diagram and Relational Schema
    build_er_and_relational_schema(doc)
    print("[7/12] ER Diagram, Whiteboard Sheets, and Relational Schema built.")

    # Section 7: Keys, FDs, Normalization
    build_keys_and_normalization(doc)
    print("[8/12] Keys, FDs, 1NF-BCNF proofs, and Heath's Theorem built.")

    # Section 8: Implementation Details
    build_implementation_details(doc)
    print("[9/12] Implementation Details, Row Locks, and ML Pipeline built.")

    # Section 9: Important SQL Operations
    build_sql_operations(doc)
    print("[10/12] 10 Important SQL Operations (DDL, Aggregations, Triggers) built.")

    # Section 10: Testing & Results
    build_testing_and_results(doc)
    print("[11/12] Testing Results, Pytest Root-Cause, and Catalog built.")

    # Section 11: Discussion, Conclusion, References, Appendix
    build_discussion_conclusion_references(doc)
    print("[12/12] Discussion, Conclusion, IEEE References & Appendix built.")

    # Target output path
    output_path = os.path.join(SCRIPT_DIR, "DBMS_Project_Report_Final.docx")
    doc.save(output_path)

    # Calculate statistics
    file_size_bytes = os.path.getsize(output_path)
    file_size_mb = file_size_bytes / (1024 * 1024)
    para_count = len(doc.paragraphs)
    table_count = len(doc.tables)

    print("=" * 70)
    print("SUCCESSFULLY GENERATED FINAL REPORT!")
    print(f"Destination:  {output_path}")
    print(f"File Size:    {file_size_mb:.2f} MB ({file_size_bytes:,} bytes)")
    print(f"Paragraphs:   {para_count}")
    print(f"Tables:       {table_count}")
    print("=" * 70)


if __name__ == "__main__":
    generate_final_report()

