# PDF Outline Extractor

This project is a solution for the "Round 1A: Understand Your Document" challenge. It extracts a hierarchical outline (Title, H1, H2, H3) from PDF files and outputs it as a structured JSON file.

## Approach

My approach to this problem is a multi-stage pipeline that mimics human-like heuristics for identifying document structure. The process is broken down into three main components:

1.  **PDF Parsing (`extractor/pdf_parser.py`)**: The system first parses the PDF to extract all text blocks along with their rich metadata, including font size, family, weight, and precise page position. It uses `PyMuPDF` for high-speed initial extraction and `pdfplumber` for more detailed analysis on a select few key pages to improve accuracy without sacrificing performance.

2.  **Heading Detection (`extractor/heading_detector.py`)**: This is the core of the solution. It uses a sophisticated scoring system to identify headings. Each text block is evaluated and scored based on a combination of:
    * **Font Properties**: Larger, bolder, and different font families receive higher scores.
    * **Positional Heuristics**: Text that is centered, has significant whitespace above it, or spans a column is favored.
    * **Content-Based Clues**: It uses regex to detect numbering patterns (e.g., "1.1", "A.", "Chapter 1") and matches against a dictionary of common heading keywords (e.g., "Introduction", "Conclusion").

3.  **Outline Building (`extractor/outline_builder.py`)**: Once headings are detected, this module sorts them by their natural reading order and validates the hierarchy. For instance, it ensures that an H3 is not orphaned without a parent H2. It then constructs the final, nested JSON output.

## Libraries and Models

* **`PyMuPDF` (fitz)**: For high-speed, core PDF parsing.
* **`pdfplumber`**: For detailed font and position analysis, especially for complex or non-standard PDFs.
* **`numpy`**: For efficient statistical calculations (e.g., average font size).
* **No pre-trained models were used** to keep the solution lightweight and fast, in compliance with the <= 200MB constraint.

## How to Build and Run

### Build the Docker Image

From the root directory of the project, run the following command:

```bash
docker build -t pdf-outline-extractor .