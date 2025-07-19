# Troubleshooting Guide

## Common Issues and Solutions

### Installation Issues

#### Issue: "Python 3.9+ required"
**Symptoms:** Setup script fails with Python version error
**Solution:**
```bash
# Install Python 3.9+ using pyenv
curl https://pyenv.run | bash
pyenv install 3.9.16
pyenv global 3.9.16
```

#### Issue: "Docker not found"
**Symptoms:** Build script fails with Docker error
**Solution:**
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
sudo usermod -aG docker $USER
# Log out and back in
```

#### Issue: "Permission denied on scripts"
**Symptoms:** Cannot execute shell scripts
**Solution:**
```bash
chmod +x scripts/*.sh
# Or individually:
chmod +x scripts/build.sh scripts/run.sh scripts/test.sh
```

### PDF Processing Issues

#### Issue: "No headings detected"
**Symptoms:** Output JSON shows empty outline
**Possible Causes & Solutions:**

1. **Font size threshold too high**
   ```python
   # In src/config/settings.py, lower the multipliers
   HEADING_SIZE_MULTIPLIERS = {
       'h1': 1.3,  # Instead of 1.5
       'h2': 1.2,  # Instead of 1.3
       'h3': 1.1   # Instead of 1.15
   }
   ```

2. **Confidence threshold too high**
   ```python
   MIN_HEADING_CONFIDENCE = 0.3  # Instead of 0.5
   ```

3. **Document uses unusual fonts**
   - Use debug viewer: `python tools/debug_viewer.py input/problem.pdf`
   - Check font analysis in logs
   - Adjust font-based heuristics

#### Issue: "Too many false positive headings"
**Symptoms:** Output includes non-heading text as headings
**Solutions:**

1. **Increase confidence threshold**
   ```python
   MIN_HEADING_CONFIDENCE = 0.7  # Instead of 0.5
   ```

2. **Adjust maximum heading length**
   ```python
   MAX_HEADING_LENGTH = 100  # Instead of 200
   ```

3. **Review and tune heuristic weights**
   ```python
   # In heading_detector.py, adjust weights
   score += font_size_score * 0.4  # Increase font size importance
   score += length_score * 0.2     # Increase length importance
   ```

#### Issue: "Incorrect heading levels (H1/H2/H3)"
**Symptoms:** Headings classified at wrong hierarchical level
**Solutions:**

1. **Enable strict hierarchy validation**
   ```python
   STRICT_HIERARCHY_VALIDATION = True
   ```

2. **Adjust font size multipliers for better separation**
   ```python
   HEADING_SIZE_MULTIPLIERS = {
       'h1': 1.6,  # Larger gap between levels
       'h2': 1.3,
       'h3': 1.1
   }
   ```

### Performance Issues

#### Issue: "Processing takes too long"
**Symptoms:** Documents take >10 seconds to process
**Solutions:**

1. **Check document complexity**
   ```bash
   # Use benchmark tool
   python tools/benchmark.py --document input/slow.pdf
   ```

2. **Reduce batch size for memory-constrained systems**
   ```bash
   BATCH_SIZE=1 ./scripts/run.sh
   ```

3. **Enable font caching**
   ```python
   ENABLE_FONT_CACHING = True
   ```

4. **Profile the bottleneck**
   ```bash
   python -m cProfile -o profile.stats src/main.py
   python -c "import pstats; pstats.Stats('profile.stats').sort_stats('cumulative').print_stats(10)"
   ```

#### Issue: "Out of memory errors"
**Symptoms:** Process killed or memory allocation errors
**Solutions:**

1. **Increase Docker memory limit**
   ```bash
   docker run --memory=2g pdf-outline-extractor
   ```

2. **Process documents individually**
   ```bash
   BATCH_SIZE=1 ./scripts/run.sh
   ```

3. **Check for memory leaks**
   ```bash
   python tools/memory_profiler.py input/large.pdf
   ```

### Output Quality Issues

#### Issue: "Missing page numbers in output"
**Symptoms:** Headings detected but page numbers are 0 or incorrect
**Cause:** Page numbering issue in PDF parser
**Solution:**
```python
# Check page extraction logic in pdf_parser.py
# Ensure page_num is correctly passed to TextBlock
text_block = TextBlock(
    text=text,
    page=page_num + 1,  # Ensure 1-based indexing
    # ... other parameters
)
```

#### Issue: "Garbled text in headings"
**Symptoms:** Output contains strange characters or encoding issues
**Solutions:**

1. **Check PDF encoding**
   ```bash
   python -c "
   import fitz
   doc = fitz.open('input/problem.pdf')
   print('PDF version:', doc.metadata.get('format', 'Unknown'))
   print('Encrypted:', doc.needs_pass)
   "
   ```

2. **Improve text cleaning**
   ```python
   # In utils.py, enhance clean_text function
   def clean_text(text: str) -> str:
       # Add more encoding fixes
       text = text.encode('utf-8', errors='ignore').decode('utf-8')
       return text
   ```

### Docker Issues

#### Issue: "Docker build fails"
**Symptoms:** Build script exits with error
**Common Solutions:**

1. **Clear Docker cache**
   ```bash
   docker system prune -a
   ./scripts/build.sh --clean
   ```

2. **Check Dockerfile syntax**
   ```bash
   docker build --no-cache -t pdf-outline-extractor .
   ```

3. **Verify base image availability**
   ```bash
   docker pull python:3.9-slim
   ```

#### Issue: "Container exits immediately"
**Symptoms:** Docker run command exits without processing
**Debug Steps:**

1. **Check container logs**
   ```bash
   docker logs pdf-extractor-run
   ```

2. **Run interactively**
   ```bash
   docker run -it --entrypoint /bin/bash pdf-outline-extractor
   ```

3. **Verify file permissions**
   ```bash
   ls -la input/ output/
   ```

### Development Issues

#### Issue: "Import errors in development"
**Symptoms:** Python cannot find modules
**Solutions:**

1. **Activate virtual environment**
   ```bash
   source venv/bin/activate
   ```

2. **Set PYTHONPATH**
   ```bash
   export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
   ```

3. **Install in development mode**
   ```bash
   pip install -e .
   ```

#### Issue: "Tests fail"
**Symptoms:** pytest reports failures
**Debug Steps:**

1. **Run tests with verbose output**
   ```bash
   pytest tests/ -v -s
   ```

2. **Run specific failing test**
   ```bash
   pytest tests/unit/test_pdf_parser.py::test_specific_function -v
   ```

3. **Check test fixtures**
   ```bash
   ls tests/fixtures/
   # Ensure test PDFs are present
   ```

## Debug Tools and Techniques

### 1. Enable Debug Logging
```bash
LOG_LEVEL=DEBUG ./scripts/run.sh
tail -f logs/extractor.log
```

### 2. Use Debug Viewer
```bash
python tools/debug_viewer.py input/problem.pdf
# Visual inspection of detected elements
```

### 3. Analyze Font Information
```python
# Add to pdf_parser.py for debugging
def debug_fonts(self, document):
    font_info = {}
    for block in document.text_blocks:
        key = f"{block.font_info.family}_{block.font_info.size}"
        font_info[key] = font_info.get(key, 0) + 1
    
    print("Font distribution:")
    for font, count in sorted(font_info.items()):
        print(f"  {font}: {count} blocks")
```

### 4. Test Individual Components
```python
# Test parser only
from src.extractor.pdf_parser import PDFParser
from src.config.settings import Settings

parser = PDFParser(Settings())
document = parser.parse("input/test.pdf")
print(f"Extracted {len(document.text_blocks)} text blocks")
```

### 5. Validate Output Structure
```bash
python tools/validate_output.py output/document_outline.json
```

## Getting Additional Help

### 1. Check Documentation
- `README.md` - Project overview
- `docs/DEVELOPMENT.md` - Development guide
- `docs/HEURISTICS.md` - Algorithm details

### 2. Review Logs
```bash
# Application logs
tail -f logs/extractor.log

# Docker logs
docker logs pdf-extractor-run

# System logs (if needed)
journalctl -u docker
```

### 3. Community Resources
- PDF processing libraries documentation
- PyMuPDF examples and tutorials
- pdfplumber usage guides

### 4. Performance Profiling
```bash
# Memory usage
python -m memory_profiler src/main.py

# CPU profiling
python -m cProfile src/main.py

# Line-by-line profiling
kernprof -l -v src/main.py
```

Remember: Most issues can be resolved by adjusting the configuration parameters in `src/config/settings.py` or by using the debug tools to understand what the system is detecting in your specific PDF files.