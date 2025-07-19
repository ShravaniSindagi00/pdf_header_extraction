"""
Main entry point for the PDF Outline Extractor application.

This script processes all PDF files in the 'input' directory and generates
structured JSON outlines in the 'output' directory.
"""

import logging
import argparse
from pathlib import Path
import os
import json # <-- Import json at the top

from extractor import PDFParser, HeadingDetector, OutlineBuilder
from config.settings import Settings
from models.document import Document
from models.outline import Outline

# --- Create logs directory if it doesn't exist ---
os.makedirs("logs", exist_ok=True)

# --- Setup Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/extractor.log'),
    ]
)
# Quieten the noisy pdfminer logger
logging.getLogger("pdfminer").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


def process_pdfs(input_dir: Path, output_dir: Path, settings: Settings):
    """
    Process all PDF files in the input directory and save outlines to the output directory.

    Args:
        input_dir: Path to the directory containing PDF files.
        output_dir: Path to the directory where JSON outlines will be saved.
        settings: Application settings.
    """
    pdf_files = list(input_dir.glob("*.pdf"))

    if not pdf_files:
        logger.warning(f"No PDF files found in {input_dir}")
        return

    logger.info(f"Found {len(pdf_files)} PDF files to process.")

    # Initialize components
    pdf_parser = PDFParser(settings)
    heading_detector = HeadingDetector(settings)
    outline_builder = OutlineBuilder(settings)

    for pdf_path in pdf_files:
        try:
            logger.info(f"Processing file: {pdf_path.name}")

            # Step 1: Parse the PDF
            document = pdf_parser.parse(pdf_path)

            # Step 2: Detect headings
            headings = heading_detector.detect_headings(document)

            # Step 3: Build the outline
            outline = outline_builder.build_outline(headings)

            # Step 4: Format the output JSON
            output_data = {
                "title": document.filename,
                "outline": [
                    {
                        "level": f"H{h.level}",
                        "text": h.text,
                        "page": h.page
                    }
                    for h in outline.headings
                ]
            }

            # Step 5: Save the outline to a JSON file
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

    # Set the root logger level based on the verbose flag
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)

    # Define base paths relative to this script's location
    base_dir = Path(__file__).resolve().parent.parent
    input_directory = base_dir / "input"
    output_directory = base_dir / "output"

    # Create output directory if it doesn't exist
    output_directory.mkdir(exist_ok=True)

    # Load settings
    app_settings = Settings()

    logger.info("Starting PDF Outline Extractor")
    process_pdfs(input_directory, output_directory, app_settings)
    logger.info("Processing complete.")