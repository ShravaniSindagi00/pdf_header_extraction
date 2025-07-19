"""
PDF extraction components.

This package contains the core logic for parsing PDFs, detecting headings,
and building structured outlines.
"""

from .pdf_parser import PDFParser
from .heading_detector import HeadingDetector
from .outline_builder import OutlineBuilder

__all__ = ["PDFParser", "HeadingDetector", "OutlineBuilder"]