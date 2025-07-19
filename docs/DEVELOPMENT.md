# Development Guide

## Architecture Overview

The PDF Outline Extractor follows a modular architecture with clear separation of concerns:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   PDF Parser    │───▶│ Heading Detector │───▶│ Outline Builder │
│                 │    │                  │    │                 │
│ - Text extraction│    │ - Font analysis  │    │ - Hierarchy     │
│ - Font metadata │    │ - Position logic │    │ - Validation    │
│ - Layout info   │    │ - Pattern match  │    │ - Quality score │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Core Components

### 1. PDF Parser (`src/extractor/pdf_parser.py`)
**Purpose:** Extract raw text and metadata from PDF files

**Key Methods:**
- `parse(pdf_path)` - Main parsing entry point
- `_extract_page_blocks()` - Extract text blocks from pages
- `_enhance_font_analysis()` - Detailed font information

**Performance Optimizations:**
- Font information caching
- Selective detailed analysis on key pages
- Memory-efficient text block processing

### 2. Heading Detector (`src/extractor/heading_detector.py`)
**Purpose:** Identify headings using multiple heuristics

**Detection Heuristics:**
- **Font Size** (30% weight) - Relative to document average
- **Font Style** (20% weight) - Bold, different family
- **Position** (15% weight) - Left alignment, whitespace
- **Numbering** (15% weight) - "1.", "1.1", "Chapter 1"
- **Keywords** (10% weight) - "Introduction", "Conclusion"
- **Length** (10% weight) - Typical heading length

**Confidence Scoring:**
```python
total_score = (
    font_size_score * 0.3 +
    font_style_score * 0.2 +
    position_score * 0.15 +
    numbering_score * 0.15 +
    keyword_score * 0.1 +
    length_score * 0.1
)
```

### 3. Outline Builder (`src/extractor/outline_builder.py`)
**Purpose:** Create hierarchical structure from detected headings

**Key Features:**
- Hierarchy validation and correction
- Quality metrics calculation
- Tree structure building
- Consistency checking

## Configuration System

### Settings (`src/config/settings.py`)
All configuration is centralized and environment-aware:

```python
# Font size thresholds
HEADING_SIZE_MULTIPLIERS = {
    'h1': 1.5,  # 50% larger than average
    'h2': 1.3,  # 30% larger
    'h3': 1.15  # 15% larger
}

# Performance settings
MAX_PROCESSING_TIME = 10.0  # seconds
BATCH_SIZE = 5  # concurrent documents
```

### Environment Variables
```bash
export PDF_EXTRACTOR_LOG_LEVEL=DEBUG
export PDF_EXTRACTOR_MAX_PROCESSING_TIME=15
export PDF_EXTRACTOR_MIN_HEADING_CONFIDENCE=0.6
```

## Testing Strategy

### Test Structure
```
tests/
├── unit/                 # Individual component tests
│   ├── test_pdf_parser.py
│   ├── test_heading_detector.py
│   └── test_outline_builder.py
├── integration/          # End-to-end tests
│   └── test_full_pipeline.py
└── fixtures/            # Test data
    ├── sample_simple.pdf
    └── expected_outputs/
```

### Running Tests
```bash
# All tests
pytest tests/

# With coverage
pytest tests/ --cov=src --cov-report=html

# Specific test category
pytest tests/unit/ -v
pytest tests/integration/ -v

# Performance tests
pytest tests/ -k "benchmark"
```

## Debugging and Development Tools

### 1. Debug Viewer (`tools/debug_viewer.py`)
Visual debugging tool to inspect:
- Detected text blocks
- Font information
- Heading classifications
- Confidence scores

```bash
python tools/debug_viewer.py input/problematic.pdf
```

### 2. Benchmark Tool (`tools/benchmark.py`)
Performance measurement:
```bash
python tools/benchmark.py --document input/large.pdf
```

### 3. Validation Tool (`tools/validate_output.py`)
Output quality checking:
```bash
python tools/validate_output.py output/document_outline.json
```

## Performance Optimization

### Current Optimizations
1. **Font Caching** - Reuse font analysis across pages
2. **Selective Analysis** - Detailed analysis only on key pages
3. **Batch Processing** - Process multiple documents concurrently
4. **Memory Management** - Efficient text block storage

### Performance Targets
- **50-page document**: ≤10 seconds
- **Memory usage**: ≤100MB per document
- **Accuracy**: ≥85% heading detection

### Profiling
```bash
# Profile a specific document
python -m cProfile -o profile.stats src/main.py
python -c "import pstats; pstats.Stats('profile.stats').sort_stats('cumulative').print_stats(20)"
```

## Extending the System

### Adding New Heuristics
1. Create new scoring method in `HeadingDetector`
2. Add weight to scoring calculation
3. Update configuration settings
4. Add unit tests

Example:
```python
def _calculate_custom_score(self, block: TextBlock) -> float:
    """Custom heuristic for specific document types."""
    # Your logic here
    return score

# Add to _score_candidates method
score += self._calculate_custom_score(candidate) * 0.05
```

### Supporting New Output Formats
1. Create new formatter in `src/formatters/`
2. Update main.py to support new format
3. Add format-specific tests

### Adding Document Type Detection
1. Extend `Document` model with type field
2. Add type detection in `PDFParser`
3. Use type-specific heuristics in `HeadingDetector`

## Code Quality Standards

### Style Guidelines
- **Black** for code formatting
- **flake8** for style checking
- **mypy** for type checking
- **Maximum line length**: 100 characters

### Documentation Standards
- Docstrings for all public methods
- Type hints for all function parameters
- Inline comments for complex logic
- README updates for new features

### Git Workflow
```bash
# Feature development
git checkout -b feature/new-heuristic
# ... make changes ...
git commit -m "feat: add custom heuristic for academic papers"
git push origin feature/new-heuristic
# ... create pull request ...
```

## Deployment Considerations

### Docker Production Build
```dockerfile
# Multi-stage build for smaller image
FROM python:3.9-slim as builder
# ... build dependencies ...

FROM python:3.9-slim as runtime
# ... copy only runtime files ...
```

### Scaling Considerations
- **Horizontal scaling**: Multiple container instances
- **Queue system**: Redis/RabbitMQ for job management
- **Storage**: Shared volume for input/output
- **Monitoring**: Prometheus metrics, health checks

### Security
- **Input validation**: PDF file verification
- **Resource limits**: Memory and CPU constraints
- **Network isolation**: Container security
- **Logging**: Audit trail for processed documents