"""
PDF Parser - Extract text, font information, and layout data from PDF files.
Includes OCR fallback for scanned documents.
"""

import logging
from pathlib import Path
from typing import List
import fitz  # PyMuPDF
import numpy as np
import pytesseract
from PIL import Image
import io

from models.document import Document, TextBlock, FontInfo
from config.settings import Settings

logger = logging.getLogger(__name__)

class PDFParser:
    """
    High-performance PDF parser that extracts text blocks with detailed
    font and positioning information, with OCR fallback for scanned pages.
    """

    def __init__(self, settings: Settings):
        self.settings = settings

    def parse(self, pdf_path: Path) -> Document:
        """
        Parse a PDF file, attempting direct text extraction first, then OCR.
        """
        try:
            logger.debug(f"Starting to parse PDF: {pdf_path}")
            document = Document(filename=pdf_path.name, filepath=str(pdf_path))
            
            with fitz.open(pdf_path) as pdf_doc:
                document.page_count = len(pdf_doc)
                document.page_dimensions = [(page.rect.width, page.rect.height) for page in pdf_doc]
                
                all_text_blocks = []
                for page_num, page in enumerate(pdf_doc):
                    page_number = page_num + 1
                    text_blocks = self._extract_text_blocks_from_page(page, page_number)
                    
                    # If a page has very little text, it's likely scanned. Try OCR.
                    total_text_length = sum(len(block.text) for block in text_blocks)
                    if total_text_length < 50: # Threshold for considering a page "scanned"
                        logger.debug(f"Page {page_number} has little text. Attempting OCR...")
                        ocr_blocks = self._ocr_page(page, page_number)
                        all_text_blocks.extend(ocr_blocks)
                    else:
                        all_text_blocks.extend(text_blocks)
                        
                document.text_blocks = all_text_blocks

            self._calculate_document_stats(document)
            logger.info(f"Parsed {len(document.text_blocks)} text blocks from {document.page_count} pages")
            return document
            
        except Exception as e:
            logger.error(f"Failed to parse PDF {pdf_path}: {str(e)}")
            raise

    def _extract_text_blocks_from_page(self, page: fitz.Page, page_num: int) -> List[TextBlock]:
        """Extracts text directly from the PDF's text layer."""
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
            logger.warning(f"Error extracting direct text from page {page_num}: {str(e)}")
        return text_blocks

    def _ocr_page(self, page: fitz.Page, page_num: int) -> List[TextBlock]:
        """
        Performs OCR on a page image to extract text from scanned documents.
        NOTE: This loses detailed font and position info for individual words.
        """
        ocr_blocks = []
        try:
            # Render page to an image
            pix = page.get_pixmap(dpi=300)
            img = Image.open(io.BytesIO(pix.tobytes()))
            
            # Use pytesseract to get text data
            ocr_text = pytesseract.image_to_string(img)
            
            if ocr_text.strip():
                # Since OCR doesn't give us font info, we create one large text block
                # for the whole page with default font properties.
                default_font = FontInfo(family="OCR", size=12.0, flags=0, color="#000000")
                page_width, page_height = page.rect.width, page.rect.height
                
                # We can split the text by line to create multiple blocks
                for line in ocr_text.splitlines():
                    if line.strip():
                        ocr_blocks.append(TextBlock(
                            text=line.strip(),
                            page=page_num,
                            x=0, y=0, # Position is unknown from OCR
                            width=page_width, height=12, # A-best guess for height
                            font_info=default_font
                        ))
                logger.debug(f"Successfully extracted {len(ocr_blocks)} lines of text via OCR from page {page_num}")
        except Exception as e:
            logger.error(f"OCR failed for page {page_num}: {e}")
        return ocr_blocks


    def _calculate_document_stats(self, document: Document) -> None:
        """Calculate document-wide statistics for heading detection."""
        if not document.text_blocks: return
        
        font_sizes = [b.font_info.size for b in document.text_blocks if b.font_info.size > 0 and b.font_info.family != "OCR"]
        document.avg_font_size = np.mean(font_sizes) if font_sizes else 12.0
        
        font_families = [b.font_info.family for b in document.text_blocks if b.font_info.family != "OCR"]
        if font_families:
            from collections import Counter
            document.primary_font = Counter(font_families).most_common(1)[0][0]
        
        logger.debug(f"Document stats - Avg font size: {document.avg_font_size:.1f}, Primary font: {document.primary_font}")


    def _rgb_to_hex(self, color_int: int) -> str:
        """Convert RGB integer to hex color string."""
        try:
            r, g, b = (color_int >> 16) & 0xFF, (color_int >> 8) & 0xFF, color_int & 0xFF
            return f"#{r:02x}{g:02x}{b:02x}"
        except:
            return "#000000"