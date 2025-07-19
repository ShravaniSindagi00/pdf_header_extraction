"""
PDF Parser - Extract text, font information, and layout data from PDF files.

This module uses PyMuPDF (fitz) for fast PDF parsing and intelligently uses
pdfplumber for detailed analysis only on critical pages to ensure performance.
"""

import logging
import re
from pathlib import Path
from typing import List
import fitz  # PyMuPDF
import pdfplumber
import numpy as np

from models.document import Document, TextBlock, FontInfo
from config.settings import Settings

logger = logging.getLogger(__name__)

class PDFParser:
    """
    High-performance PDF parser that extracts text blocks with detailed
    font and positioning information.
    """

    def __init__(self, settings: Settings):
        self.settings = settings

    def parse(self, pdf_path: Path) -> Document:
        """
        Parse a PDF file and extract all text blocks with metadata.
        """
        try:
            logger.debug(f"Starting to parse PDF: {pdf_path}")
            document = Document(filename=pdf_path.name, filepath=str(pdf_path))
            
            # Use PyMuPDF for fast, initial text extraction
            with fitz.open(pdf_path) as pdf_doc:
                document.page_count = len(pdf_doc)
                document.page_dimensions = [(page.rect.width, page.rect.height) for page in pdf_doc]
                
                all_text_blocks = []
                for page_num, page in enumerate(pdf_doc):
                    all_text_blocks.extend(self._extract_page_blocks(page, page_num + 1))
                document.text_blocks = all_text_blocks

            # First, calculate statistics from the initial parse
            self._calculate_document_stats(document)

            # NEW: Detect the document's language
            document.language = self._detect_language(document)
            logger.info(f"Detected document language: {document.language}")
            
            # OPTIMIZATION: Intelligently enhance font analysis only on important pages
            self._enhance_font_analysis(document, pdf_path)
            
            logger.info(f"Parsed {len(document.text_blocks)} text blocks from {document.page_count} pages")
            return document
            
        except Exception as e:
            logger.error(f"Failed to parse PDF {pdf_path}: {str(e)}")
            raise

    def _detect_language(self, document: Document) -> str:
        """
        Detect the primary language of the document by checking character ranges.
        This is a simple heuristic and can be expanded.
        """
        japanese_chars = 0
        total_chars = 0
        
        # Check a sample of text blocks for Japanese characters
        for block in document.text_blocks[:100]: # Check first 100 blocks
            for char in block.text:
                total_chars += 1
                # Check if the character is in the common Japanese Unicode ranges
                # (Hiragana, Katakana, CJK Unified Ideographs)
                if '\u3040' <= char <= '\u309F' or \
                   '\u30A0' <= char <= '\u30FF' or \
                   '\u4E00' <= char <= '\u9FFF':
                    japanese_chars += 1
        
        if total_chars > 0 and (japanese_chars / total_chars) > 0.1:
            return 'japanese' # If more than 10% of chars are Japanese
        
        return 'english' # Default


    def _extract_page_blocks(self, page: fitz.Page, page_num: int) -> List[TextBlock]:
        """Extract text blocks from a single page using PyMuPDF."""
        text_blocks = []
        try:
            blocks = page.get_text("dict").get("blocks", [])
            for block in blocks:
                if "lines" not in block: continue
                for line in block["lines"]:
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        if not text: continue
                        
                        font_info = FontInfo(
                            family=span.get("font", "Unknown"),
                            size=span.get("size", 12.0),
                            flags=span.get("flags", 0),
                            color=self._rgb_to_hex(span.get("color", 0))
                        )
                        bbox = span.get("bbox", (0, 0, 0, 0))
                        
                        text_blocks.append(TextBlock(
                            text=text, page=page_num, x=bbox[0], y=bbox[1],
                            width=bbox[2] - bbox[0], height=bbox[3] - bbox[1],
                            font_info=font_info
                        ))
        except Exception as e:
            logger.warning(f"Error extracting blocks from page {page_num}: {str(e)}")
        return text_blocks

    def _calculate_document_stats(self, document: Document) -> None:
        """Calculate document-wide statistics for heading detection."""
        if not document.text_blocks: return
        
        font_sizes = [b.font_info.size for b in document.text_blocks if b.font_info.size > 0]
        document.avg_font_size = np.mean(font_sizes) if font_sizes else 12.0
        
        font_families = [b.font_info.family for b in document.text_blocks]
        if font_families:
            from collections import Counter
            document.primary_font = Counter(font_families).most_common(1)[0][0]
        
        logger.debug(f"Document stats - Avg font size: {document.avg_font_size:.1f}, Primary font: {document.primary_font}")

    def _enhance_font_analysis(self, document: Document, pdf_path: Path) -> None:
        """
        Use pdfplumber for more detailed font analysis ONLY on key pages.
        This performance optimization prevents slowdowns on large documents.
        """
        # pdfplumber is generally better for CJK languages, so we might use it more
        if document.language == 'japanese':
            # For Japanese, we might want to analyze more pages
            key_pages = set(range(1, min(6, document.page_count + 1))) # First 5 pages
        else:
            # For English, stick to the optimized strategy
            key_pages = set()
            for block in document.text_blocks:
                if block.font_info.size > (document.avg_font_size * 1.5):
                    key_pages.add(block.page)
        
        if not key_pages:
            logger.debug("No key pages found for detailed analysis. Skipping.")
            return

        logger.debug(f"Performing detailed font analysis on {len(key_pages)} key pages: {sorted(list(key_pages))}")
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num in key_pages:
                    if page_num <= len(pdf.pages):
                        page = pdf.pages[page_num - 1]
                        for block in document.text_blocks:
                            if block.page == page_num:
                                self._update_block_font_info(block, page.chars)
        except Exception as e:
            logger.warning(f"Detailed font enhancement failed: {str(e)}")

    def _update_block_font_info(self, block: TextBlock, page_chars: List[dict]):
        """Find matching chars in pdfplumber data to get more accurate font names."""
        matching_chars = [
            char for char in page_chars
            if (abs(char['x0'] - block.x) < 5 and abs(char['top'] - block.y) < 5)
        ]
        
        if matching_chars:
            best_char = matching_chars[0]
            block.font_info.family = best_char.get('fontname', block.font_info.family)

    def _rgb_to_hex(self, color_int: int) -> str:
        """Convert RGB integer to hex color string."""
        try:
            r, g, b = (color_int >> 16) & 0xFF, (color_int >> 8) & 0xFF, color_int & 0xFF
            return f"#{r:02x}{g:02x}{b:02x}"
        except:
            return "#000000"