"""
PDF Outline Extractor

A robust Python application for extracting structured outlines from PDF files.
"""

__version__ = "1.0.0"
__author__ = "PDF Outline Extractor Team"
__email__ = "support@example.com"

from .extractor import PDFParser, HeadingDetector, OutlineBuilder
from .models import Document, Outline, Heading

__all__ = [
    "PDFParser",
    "HeadingDetector", 
    "OutlineBuilder",
    "Document",
    "Outline",
    "Heading"
]