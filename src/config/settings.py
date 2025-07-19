"""
Application-wide settings and configuration.
"""
from dataclasses import dataclass

@dataclass
class Settings:
    """
    Configuration settings for the PDF extractor.
    """
    # Maximum character length for a line to be considered a heading.
    MAX_HEADING_LENGTH: int = 150

    # The minimum confidence score (0.0 to 1.0) for a text block to be
    # classified as a heading.
    MIN_HEADING_CONFIDENCE: float = 0.4