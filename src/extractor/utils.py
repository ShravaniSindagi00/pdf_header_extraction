"""
Utility functions for PDF extraction and text processing.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import hashlib

logger = logging.getLogger(__name__)


def clean_text(text: str) -> str:
    """
    Clean and normalize text extracted from PDFs.
    
    Args:
        text: Raw text from PDF
        
    Returns:
        Cleaned and normalized text
    """
    if not text:
        return ""
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove common PDF artifacts
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\xff]', '', text)
    
    # Fix common encoding issues
    replacements = {
        'â€™': "'",
        'â€œ': '"',
        'â€': '"',
        'â€"': '—',
        'â€"': '–',
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    return text.strip()


def normalize_font_name(font_name: str) -> str:
    """
    Normalize font names for consistent comparison.
    
    Args:
        font_name: Raw font name from PDF
        
    Returns:
        Normalized font name
    """
    if not font_name:
        return "Unknown"
    
    # Remove common prefixes and suffixes
    font_name = re.sub(r'^[A-Z]{6}\+', '', font_name)  # Remove subset prefix
    font_name = re.sub(r'[,\-].*$', '', font_name)     # Remove variants
    
    # Normalize case
    font_name = font_name.title()
    
    # Common font name mappings
    mappings = {
        'Timesnewroman': 'Times New Roman',
        'Timesnewromanps': 'Times New Roman',
        'Arialmt': 'Arial',
        'Helvetica': 'Arial',  # Treat as similar
        'Calibri': 'Calibri',
    }
    
    return mappings.get(font_name, font_name)


def calculate_text_similarity(text1: str, text2: str) -> float:
    """
    Calculate similarity between two text strings.
    
    Args:
        text1, text2: Text strings to compare
        
    Returns:
        Similarity score between 0 and 1
    """
    if not text1 or not text2:
        return 0.0
    
    # Normalize texts
    text1 = text1.lower().strip()
    text2 = text2.lower().strip()
    
    if text1 == text2:
        return 1.0
    
    # Simple word-based similarity
    words1 = set(text1.split())
    words2 = set(text2.split())
    
    if not words1 or not words2:
        return 0.0
    
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    
    return len(intersection) / len(union)


def extract_numbering_pattern(text: str) -> Optional[Tuple[str, str]]:
    """
    Extract numbering pattern from heading text.
    
    Args:
        text: Heading text
        
    Returns:
        Tuple of (numbering, remaining_text) or None
    """
    patterns = [
        (r'^(\d+\.)\s*(.+)', 'decimal'),
        (r'^(\d+\.\d+)\s*(.+)', 'decimal_sub'),
        (r'^(\d+\.\d+\.\d+)\s*(.+)', 'decimal_subsub'),
        (r'^([A-Z]\.)\s*(.+)', 'alpha'),
        (r'^([IVX]+\.)\s*(.+)', 'roman'),
        (r'^(\(\d+\))\s*(.+)', 'parenthetical'),
        (r'^(Chapter\s+\d+)\s*(.+)', 'chapter'),
        (r'^(Section\s+\d+)\s*(.+)', 'section'),
    ]
    
    for pattern, pattern_type in patterns:
        match = re.match(pattern, text.strip(), re.IGNORECASE)
        if match:
            return (match.group(1), match.group(2).strip())
    
    return None


def is_likely_page_header_footer(text: str, page_height: float, y_position: float) -> bool:
    """
    Determine if text is likely a page header or footer.
    
    Args:
        text: Text content
        page_height: Height of the page
        y_position: Y position of the text
        
    Returns:
        True if likely header/footer
    """
    # Check position (top 10% or bottom 10% of page)
    if y_position < page_height * 0.1 or y_position > page_height * 0.9:
        # Check for common header/footer patterns
        header_footer_patterns = [
            r'^\d+$',  # Page numbers
            r'^Page\s+\d+',
            r'^\d+\s*$',
            r'^Chapter\s+\d+\s*$',
            r'^\w+\s+\d{4}$',  # Date patterns
            r'^©.*\d{4}',  # Copyright
        ]
        
        for pattern in header_footer_patterns:
            if re.match(pattern, text.strip(), re.IGNORECASE):
                return True
    
    return False


def calculate_reading_order_score(blocks: List[Any]) -> List[Tuple[Any, float]]:
    """
    Calculate reading order scores for text blocks.
    
    Args:
        blocks: List of text blocks with position information
        
    Returns:
        List of (block, score) tuples sorted by reading order
    """
    scored_blocks = []
    
    for block in blocks:
        # Primary sort: top to bottom (y position)
        # Secondary sort: left to right (x position)
        score = block.y * 1000 + block.x
        scored_blocks.append((block, score))
    
    # Sort by score (reading order)
    scored_blocks.sort(key=lambda x: x[1])
    
    return scored_blocks


def generate_content_hash(text: str) -> str:
    """
    Generate a hash for text content to detect duplicates.
    
    Args:
        text: Text content
        
    Returns:
        SHA-256 hash of the text
    """
    normalized_text = re.sub(r'\s+', ' ', text.lower().strip())
    return hashlib.sha256(normalized_text.encode('utf-8')).hexdigest()[:16]


def validate_pdf_file(file_path: Path) -> bool:
    """
    Validate that a file is a readable PDF.
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        True if valid PDF, False otherwise
    """
    try:
        if not file_path.exists():
            return False
        
        if file_path.suffix.lower() != '.pdf':
            return False
        
        # Check file size (not empty, not too large)
        file_size = file_path.stat().st_size
        if file_size == 0 or file_size > 100 * 1024 * 1024:  # 100MB limit
            return False
        
        # Try to open with PyMuPDF
        import fitz
        with fitz.open(file_path) as doc:
            if len(doc) == 0:
                return False
        
        return True
        
    except Exception as e:
        logger.warning(f"PDF validation failed for {file_path}: {str(e)}")
        return False


def format_confidence_score(confidence: float) -> str:
    """
    Format confidence score for display.
    
    Args:
        confidence: Confidence score (0-1)
        
    Returns:
        Formatted confidence string
    """
    percentage = confidence * 100
    
    if percentage >= 90:
        return f"{percentage:.0f}% (High)"
    elif percentage >= 70:
        return f"{percentage:.0f}% (Medium)"
    elif percentage >= 50:
        return f"{percentage:.0f}% (Low)"
    else:
        return f"{percentage:.0f}% (Very Low)"


def estimate_processing_time(page_count: int) -> float:
    """
    Estimate processing time based on page count.
    
    Args:
        page_count: Number of pages in the document
        
    Returns:
        Estimated processing time in seconds
    """
    # Base time per page (empirically determined)
    base_time_per_page = 0.15  # seconds
    
    # Additional overhead
    base_overhead = 1.0  # seconds
    
    # Scale factor for complex documents
    complexity_factor = 1.2
    
    estimated_time = (page_count * base_time_per_page * complexity_factor) + base_overhead
    
    return max(estimated_time, 1.0)  # Minimum 1 second


def create_debug_info(document: Any, headings: List[Any]) -> Dict[str, Any]:
    """
    Create debug information for troubleshooting.
    
    Args:
        document: Parsed document
        headings: Detected headings
        
    Returns:
        Debug information dictionary
    """
    debug_info = {
        'document_stats': {
            'filename': document.filename,
            'page_count': document.page_count,
            'text_blocks': len(document.text_blocks),
            'avg_font_size': getattr(document, 'avg_font_size', 0),
            'primary_font': getattr(document, 'primary_font', 'Unknown'),
        },
        'heading_stats': {
            'total_headings': len(headings),
            'by_level': {},
            'avg_confidence': 0,
        },
        'font_analysis': {},
        'potential_issues': []
    }
    
    if headings:
        # Heading level distribution
        level_counts = {}
        total_confidence = 0
        
        for heading in headings:
            level = f'h{heading.level}'
            level_counts[level] = level_counts.get(level, 0) + 1
            total_confidence += heading.confidence
        
        debug_info['heading_stats']['by_level'] = level_counts
        debug_info['heading_stats']['avg_confidence'] = total_confidence / len(headings)
        
        # Font analysis
        fonts_used = {}
        for heading in headings:
            font_key = f"{heading.font_info.family}_{heading.font_info.size}"
            fonts_used[font_key] = fonts_used.get(font_key, 0) + 1
        
        debug_info['font_analysis'] = fonts_used
        
        # Identify potential issues
        if len(headings) == 0:
            debug_info['potential_issues'].append("No headings detected")
        elif len([h for h in headings if h.level == 1]) == 0:
            debug_info['potential_issues'].append("No H1 headings found")
        elif debug_info['heading_stats']['avg_confidence'] < 0.5:
            debug_info['potential_issues'].append("Low average confidence scores")
    
    return debug_info