# Getting Started Guide

## Quick Start (5 Minutes)

### Prerequisites
- Python 3.9+ installed
- Docker installed (recommended)
- At least 2GB free disk space

### Step 1: Clone and Setup
```bash
# Navigate to your project directory
cd pdf-outline-extractor

# Make scripts executable
chmod +x scripts/*.sh

# Run the setup script
./scripts/setup.sh
```

### Step 2: Test the Installation
```bash
# Build the Docker image
./scripts/build.sh

# Run tests to verify everything works
./scripts/test.sh --smoke
```

### Step 3: Process Your First PDF
```bash
# Add a PDF file to the input directory
cp /path/to/your/document.pdf input/

# Run the extraction
./scripts/run.sh

# Check the results
ls output/
cat output/document_outline.json
```

## Development Workflow

### Local Development (Without Docker)
```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run directly
python src/main.py --verbose

# Run tests
pytest tests/ -v
```

### Docker Development
```bash
# Build and run
./scripts/build.sh
./scripts/run.sh --verbose

# Run with custom settings
LOG_LEVEL=DEBUG ./scripts/run.sh
```

## Troubleshooting Common Issues

### Issue: "Docker image not found"
**Solution:** Run `./scripts/build.sh` first

### Issue: "No PDF files found"
**Solution:** Add PDF files to the `input/` directory

### Issue: "Permission denied" on scripts
**Solution:** Run `chmod +x scripts/*.sh`

### Issue: Python import errors
**Solution:** Ensure you're in the virtual environment: `source venv/bin/activate`

## Next Development Steps

1. **Test with your PDFs** - Start with simple documents
2. **Tune parameters** - Adjust settings in `src/config/settings.py`
3. **Add custom heuristics** - Extend `src/extractor/heading_detector.py`
4. **Improve accuracy** - Use the debug tools to analyze results
5. **Scale up** - Test with larger document sets

## Getting Help

- Check `docs/TROUBLESHOOTING.md` for common issues
- Use `python tools/debug_viewer.py` for visual debugging
- Review logs in `logs/extractor.log`
- Run benchmarks with `./scripts/benchmark.sh`