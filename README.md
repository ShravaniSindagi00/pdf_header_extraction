Of course. Here is a comprehensive and professional `README.md` file for your project.

This README accurately reflects all the advanced features you've built, including the OCR capabilities, multilingual support, and external configuration. Just copy and paste this into the `README.md` file in your project's root directory.

-----

# PDF Outline Extractor

This project is a high-performance, intelligent solution for automatically extracting a hierarchical outline from PDF documents. It identifies the document's title and headings (H1, H2, H3) and outputs them into a structured JSON file, enabling smarter document analysis and experiences.

This solution was built to handle a wide variety of PDF formats, from simple text-based documents to complex, image-based scanned files, and even includes support for multiple languages.

## Key Features

  * **Advanced Heuristic-Based Detection**: Goes beyond simple font size analysis by incorporating text position, layout, whitespace, numbering patterns, and font weight to accurately identify headings.
  * **OCR Fallback for Scanned PDFs**: Automatically detects image-based pages with little to no text and uses the Tesseract OCR engine to extract content, ensuring even scanned documents can be processed.
  * **Multilingual Support**: Features a language detection module that can apply different rule sets for different languages, with a built-in custom ruleset for Japanese documents.
  * **High Performance**: Optimized to process large, multi-page documents quickly, meeting the requirement of handling a 50-page PDF in under 10 seconds.
  * **External Configuration**: Key parameters like heading confidence thresholds can be easily tuned via an external `config.json` file without modifying the source code.
  * **Dockerized and Secure**: The entire application is containerized with Docker, using a non-root user and best practices for small, secure, and reproducible builds.

## The Approach

The extraction process is handled by a sophisticated three-stage pipeline:

1.  **Parsing & Analysis (`pdf_parser.py`)**: The pipeline begins by rapidly parsing the PDF using `PyMuPDF` to extract all text blocks and their rich metadata (font, size, position). It simultaneously analyzes the document to detect the primary language (e.g., English vs. Japanese). For pages that yield little or no text, the system automatically triggers an OCR fallback with `pytesseract` to handle scanned content.

2.  **Heading Detection (`heading_detector.py`)**: This is the core intelligence of the application. Based on the detected language, a specialized set of rules is applied. A scoring algorithm evaluates each text block based on a weighted combination of heuristics:

      * **Font Properties**: Larger and heavier font weights (e.g., "Bold", "Black") are strong indicators.
      * **Positional Layout**: Text that is centered on the page or has significant whitespace above it receives a higher score.
      * **Content Patterns**: The system uses regex to identify common numbering schemes (e.g., "1.1", "A.", "第1章") and checks for keywords common in headings (e.g., "Introduction", "Conclusion", "概要").

3.  **Outline Building (`outline_builder.py`)**: Once the headings are identified and scored, this module takes the flat list, sorts it into the correct reading order, and validates the hierarchy (e.g., ensuring an H3 follows an H2). It then constructs the final, clean JSON output in the required format.

## Libraries & Technologies

  * **Backend**: Python 3.9
  * **PDF Parsing**: `PyMuPDF` (fitz), `pdfplumber`
  * **OCR Engine**: `pytesseract` (a Python wrapper for Google's Tesseract)
  * **Data Handling**: `numpy`
  * **Containerization**: Docker

## Configuration

The application's behavior can be tuned via the `config.json` file located in the project root.

```json
{
  "MAX_HEADING_LENGTH": 150,
  "MIN_HEADING_CONFIDENCE": 0.4
}
```

  * `MAX_HEADING_LENGTH`: The maximum number of characters a line can have to be considered a heading.
  * `MIN_HEADING_CONFIDENCE`: A threshold from 0.0 to 1.0. Text blocks that score below this value will be discarded.

## How to Build and Run

### Prerequisites

  * Docker must be installed and running on your system.

### Step 1: Build the Docker Image

From the root directory of the project, run the following command to build the Docker image.

```bash
docker build -t pdf-outline-extractor .
```

### Step 2: Run the Extractor

1.  Place your PDF files into the `input/` directory.
2.  Run the following command. The container will automatically process all PDFs in the `input` folder.

<!-- end list -->

```bash
docker run --rm -v $(pwd)/input:/app/input -v $(pwd)/output:/app/output pdf-outline-extractor
```

The structured JSON outlines will be generated in the `output/` directory, with each output file named after its corresponding PDF.