"""
Main entry point for the PDF Outline Extractor application.
"""

import logging
import argparse
from pathlib import Path
import os
import json

# Corrected import path for the new Settings structure
from config.settings import Settings
from extractor import PDFParser, HeadingDetector, OutlineBuilder
from models.document import Document
from models.outline import Outline

# --- Setup Project and Logging ---
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler('logs/extractor.log')]
)
logging.getLogger("pdfminer").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


def process_pdfs(input_dir: Path, output_dir: Path, settings: Settings):
    """
    Process all PDF files in the input directory.
    """
    pdf_files = list(input_dir.glob("*.pdf"))
    if not pdf_files:
        logger.warning(f"No PDF files found in {input_dir}")
        return
        
    logger.info(f"Found {len(pdf_files)} PDF files to process.")
    
    # Initialize components with the loaded settings
    pdf_parser = PDFParser(settings)
    heading_detector = HeadingDetector(settings)
    outline_builder = OutlineBuilder(settings)
    
    for pdf_path in pdf_files:
        try:
            logger.info(f"Processing file: {pdf_path.name}")
            
            document = pdf_parser.parse(pdf_path)
            headings = heading_detector.detect_headings(document)
            outline = outline_builder.build_outline(headings)
            
            output_data = {
                "title": document.filename,
                "outline": [{"level": f"H{h.level}", "text": h.text, "page": h.page} for h in outline.headings]
            }
            
            output_path = output_dir / f"{pdf_path.stem}_outline.json"
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=4)

            logger.info(f"Successfully generated outline for {pdf_path.name}")

        except Exception as e:
            logger.error(f"Failed to process {pdf_path.name}: {e}", exc_info=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PDF Outline Extractor")
    parser.add_argument("--verbose", action="store_true", help="Enable detailed debug logging")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Use the new method to load settings from config.json
    app_settings = Settings.load()
    logger.info(f"Loaded settings: {app_settings}")

    base_dir = Path(__file__).resolve().parent.parent
    input_directory = base_dir / "input"
    output_directory = base_dir / "output"
    output_directory.mkdir(exist_ok=True)

    logger.info("Starting PDF Outline Extractor")
    process_pdfs(input_directory, output_directory, app_settings)
    logger.info("Processing complete.")