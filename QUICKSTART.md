# 🚀 Quick Start Guide

Get your PDF Outline Extractor running in **5 minutes**!

## Prerequisites ✅
- Python 3.9+ installed
- Docker installed (recommended)
- 2GB free disk space

## Step 1: Setup (2 minutes)
```bash
# Make scripts executable
chmod +x scripts/*.sh

# Run automated setup
./scripts/setup.sh
```

This will:
- Create Python virtual environment
- Install all dependencies
- Set up project directories
- Create sample configuration

## Step 2: Build (1 minute)
```bash
# Build Docker image
./scripts/build.sh
```

## Step 3: Test (1 minute)
```bash
# Run quick smoke test
./scripts/test.sh --smoke
```

## Step 4: Process Your First PDF (1 minute)
```bash
# Add a PDF to the input directory
cp /path/to/your/document.pdf input/

# Run the extraction
./scripts/run.sh

# Check results
ls output/
cat output/document_outline.json
```

## 🎉 You're Done!

Your PDF outline should now be in `output/document_outline.json` with this structure:

```json
{
  "document": {
    "filename": "document.pdf",
    "pages": 25,
    "processing_time": 3.2
  },
  "outline": [
    {
      "level": 1,
      "title": "Introduction",
      "page": 1,
      "confidence": 0.95
    },
    {
      "level": 2,
      "title": "Background",
      "page": 2,
      "confidence": 0.87
    }
  ],
  "statistics": {
    "total_headings": 15,
    "h1_count": 3,
    "h2_count": 8,
    "h3_count": 4
  }
}
```

## Next Steps 📚

### If you need better accuracy:
```bash
# Use debug mode to see what's being detected
./scripts/run.sh --verbose

# Visual debugging tool
python tools/debug_viewer.py input/your-document.pdf
```

### If processing is too slow:
```bash
# Run performance benchmark
./scripts/benchmark.sh

# Check system resources
docker stats
```

### If you want to customize:
- Edit `src/config/settings.py` for different thresholds
- See `docs/HEURISTICS.md` for tuning guidance
- Check `docs/TROUBLESHOOTING.md` for common issues

## Common First-Time Issues 🔧

**"No headings detected"** → Lower confidence threshold in settings
**"Too many false positives"** → Increase confidence threshold  
**"Wrong heading levels"** → Adjust font size multipliers
**"Docker build fails"** → Run `docker system prune -a` first

## Development Mode 💻

For local development without Docker:
```bash
# Activate virtual environment
source venv/bin/activate

# Run directly
python src/main.py --verbose

# Run tests
pytest tests/ -v
```

**Happy extracting! 🎯**

Need help? Check `docs/TROUBLESHOOTING.md` or review the logs in `logs/extractor.log`.