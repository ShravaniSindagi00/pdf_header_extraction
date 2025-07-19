"""
Application-wide settings and configuration.
This module loads settings from an external config.json file.
"""
import json
from dataclasses import dataclass
from pathlib import Path

@dataclass
class Settings:
    """
    Configuration settings for the PDF extractor, loaded from a config file.
    """
    MAX_HEADING_LENGTH: int = 150
    MIN_HEADING_CONFIDENCE: float = 0.4

    @classmethod
    def load(cls):
        """
        Load settings from config.json located in the project root.
        If the file doesn't exist, it uses the default values.
        """
        # The config file is in the project root, which is two levels above this file's directory
        config_path = Path(__file__).resolve().parent.parent.parent / "config.json"
        
        if config_path.exists():
            with open(config_path, 'r') as f:
                config_data = json.load(f)
            return cls(**config_data)
        
        # Return default settings if config file is not found
        return cls()