"""
Data models for representing a parsed PDF document and its components.
"""

from dataclasses import dataclass, field
from typing import List, Tuple
from datetime import datetime

@dataclass
class FontInfo:
    """Stores information about the font used in a text block."""
    family: str
    size: float
    flags: int
    color: str

@dataclass
class TextBlock:
    """Represents a block of text extracted from a PDF page."""
    text: str
    page: int
    x: float
    y: float
    width: float
    height: float
    font_info: FontInfo

@dataclass
class Document:
    """Represents a complete parsed PDF document."""
    filename: str
    filepath: str
    page_count: int = 0
    processed_at: datetime = field(default_factory=datetime.now)
    text_blocks: List[TextBlock] = field(default_factory=list)
    
    # Statistics for analysis
    avg_font_size: float = 0.0
    median_font_size: float = 0.0
    font_size_std: float = 0.0
    primary_font: str = "Unknown"
    # NEW: Store page dimensions for layout analysis
    page_dimensions: List[Tuple[float, float]] = field(default_factory=list)