#!/bin/bash

# Setup script for PDF Outline Extractor development environment
# This script sets up the local development environment

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check system requirements
check_system_requirements() {
    print_status "Checking system requirements..."
    
    # Check Python version
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
        
        if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 9 ]; then
            print_success "Python $PYTHON_VERSION found"
        else
            print_error "Python 3.9+ required, found $PYTHON_VERSION"
            exit 1
        fi
    else
        print_error "Python 3 not found. Please install Python 3.9+"
        exit 1
    fi
    
    # Check pip
    if ! command -v pip3 &> /dev/null; then
        print_error "pip3 not found. Please install pip"
        exit 1
    fi
    
    # Check Docker (optional but recommended)
    if command -v docker &> /dev/null; then
        print_success "Docker found"
        DOCKER_AVAILABLE=true
    else
        print_warning "Docker not found. Docker is recommended for containerized development"
        DOCKER_AVAILABLE=false
    fi
}

# Setup Python virtual environment
setup_virtual_environment() {
    print_status "Setting up Python virtual environment..."
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        print_success "Virtual environment created"
    else
        print_status "Virtual environment already exists"
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    print_success "Virtual environment ready"
}

# Install Python dependencies
install_dependencies() {
    print_status "Installing Python dependencies..."
    
    # Ensure we're in virtual environment
    if [ -z "$VIRTUAL_ENV" ]; then
        print_error "Virtual environment not activated"
        exit 1
    fi
    
    # Install requirements
    pip install -r requirements.txt
    
    print_success "Dependencies installed"
}

# Setup project directories
setup_directories() {
    print_status "Setting up project directories..."
    
    # Create necessary directories
    mkdir -p input
    mkdir -p output
    mkdir -p logs
    mkdir -p coverage
    mkdir -p tests/fixtures
    mkdir -p docs
    
    # Create .gitkeep files for empty directories
    touch input/.gitkeep
    touch logs/.gitkeep
    touch coverage/.gitkeep
    
    print_success "Project directories created"
}

# Setup pre-commit hooks
setup_pre_commit_hooks() {
    print_status "Setting up pre-commit hooks..."
    
    # Check if pre-commit is installed
    if command -v pre-commit &> /dev/null; then
        # Create pre-commit config if it doesn't exist
        if [ ! -f ".pre-commit-config.yaml" ]; then
            cat > .pre-commit-config.yaml << EOF
repos:
  - repo: https://github.com/psf/black
    rev: 23.11.0
    hooks:
      - id: black
        language_version: python3
        
  - repo: https://github.com/pycqa/flake8
    rev: 6.1.0
    hooks:
      - id: flake8
        args: [--max-line-length=100, --ignore=E203,W503]
        
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.1
    hooks:
      - id: mypy
        args: [--ignore-missing-imports, --no-strict-optional]
        additional_dependencies: [types-all]
EOF
        fi
        
        # Install pre-commit hooks
        pre-commit install
        print_success "Pre-commit hooks installed"
    else
        print_warning "pre-commit not found, skipping hook setup"
    fi
}

# Create sample configuration
create_sample_config() {
    print_status "Creating sample configuration..."
    
    # Create sample config file
    cat > config.sample.json << EOF
{
  "MAX_PROCESSING_TIME": 10.0,
  "MIN_HEADING_CONFIDENCE": 0.5,
  "HEADING_SIZE_MULTIPLIERS": {
    "h1": 1.5,
    "h2": 1.3,
    "h3": 1.15
  },
  "LOG_LEVEL": "INFO",
  "INCLUDE_DEBUG_INFO": false,
  "PRETTY_PRINT": true
}
EOF
    
    print_success "Sample configuration created: config.sample.json"
}

# Download sample PDF files
download_sample_files() {
    print_status "Setting up sample PDF files..."
    
    # Create a simple sample PDF using Python (if reportlab is available)
    python3 << EOF
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    
    # Create a simple test PDF
    c = canvas.Canvas("input/sample.pdf", pagesize=letter)
    
    # Add title
    c.setFont("Helvetica-Bold", 18)
    c.drawString(100, 750, "Sample Document")
    
    # Add H1 heading
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, 700, "1. Introduction")
    
    # Add some body text
    c.setFont("Helvetica", 12)
    c.drawString(100, 670, "This is a sample PDF document for testing the outline extractor.")
    
    # Add H2 heading
    c.setFont("Helvetica-Bold", 14)
    c.drawString(100, 640, "1.1 Background")
    
    # Add more body text
    c.setFont("Helvetica", 12)
    c.drawString(100, 610, "This section provides background information.")
    
    # Add another H1
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, 580, "2. Methodology")
    
    c.save()
    print("Sample PDF created successfully")
    
except ImportError:
    print("reportlab not available, skipping sample PDF creation")
except Exception as e:
    print(f"Error creating sample PDF: {e}")
EOF
    
    if [ -f "input/sample.pdf" ]; then
        print_success "Sample PDF created: input/sample.pdf"
    else
        print_warning "Could not create sample PDF (reportlab may not be installed)"
    fi
}

# Setup development tools
setup_development_tools() {
    print_status "Setting up development tools..."
    
    # Create useful shell aliases
    cat > .dev_aliases << EOF
# PDF Outline Extractor Development Aliases
alias activate='source venv/bin/activate'
alias run-extractor='python src/main.py'
alias run-tests='pytest tests/'
alias run-coverage='pytest tests/ --cov=src --cov-report=html'
alias lint='flake8 src/ && mypy src/'
alias format='black src/ tests/'
alias debug='python tools/debug_viewer.py'
EOF
    
    print_status "Development aliases created: .dev_aliases"
    print_status "To use aliases: source .dev_aliases"
}

# Verify installation
verify_installation() {
    print_status "Verifying installation..."
    
    # Test imports
    python3 -c "
import sys
sys.path.insert(0, 'src')

try:
    from extractor.pdf_parser import PDFParser
    from extractor.heading_detector import HeadingDetector
    from extractor.outline_builder import OutlineBuilder
    print('✓ Core modules import successfully')
except ImportError as e:
    print(f'✗ Import error: {e}')
    sys.exit(1)

try:
    import fitz
    import pdfplumber
    print('✓ PDF processing libraries available')
except ImportError as e:
    print(f'✗ PDF library error: {e}')
    sys.exit(1)
"
    
    if [ $? -eq 0 ]; then
        print_success "Installation verification passed"
    else
        print_error "Installation verification failed"
        exit 1
    fi
}

# Show next steps
show_next_steps() {
    echo ""
    print_success "Development environment setup completed!"
    echo ""
    print_status "Next steps:"
    echo "  1. Activate virtual environment: source venv/bin/activate"
    echo "  2. Load development aliases: source .dev_aliases"
    echo "  3. Place PDF files in input/ directory"
    echo "  4. Run extraction: python src/main.py"
    echo "  5. Run tests: pytest tests/"
    echo ""
    print_status "Useful commands:"
    echo "  - Format code: black src/ tests/"
    echo "  - Run linting: flake8 src/"
    echo "  - Type checking: mypy src/"
    echo "  - Coverage report: pytest tests/ --cov=src --cov-report=html"
    echo ""
    if [ "$DOCKER_AVAILABLE" = "true" ]; then
        print_status "Docker commands:"
        echo "  - Build image: ./scripts/build.sh"
        echo "  - Run extraction: ./scripts/run.sh"
        echo "  - Run tests: ./scripts/test.sh"
        echo ""
    fi
    print_status "Documentation:"
    echo "  - README.md - Project overview and usage"
    echo "  - docs/DEVELOPMENT.md - Development guide"
    echo "  - docs/TROUBLESHOOTING.md - Common issues"
    echo ""
}

# Show usage information
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --skip-venv      Skip virtual environment setup"
    echo "  --skip-samples   Skip sample file creation"
    echo "  --skip-hooks     Skip pre-commit hooks setup"
    echo "  --help           Show this help message"
    echo ""
}

# Main execution
main() {
    echo "PDF Outline Extractor - Development Setup"
    echo "========================================"
    echo ""
    
    # Parse command line arguments
    SKIP_VENV=false
    SKIP_SAMPLES=false
    SKIP_HOOKS=false
    
    for arg in "$@"; do
        case $arg in
            --skip-venv)
                SKIP_VENV=true
                ;;
            --skip-samples)
                SKIP_SAMPLES=true
                ;;
            --skip-hooks)
                SKIP_HOOKS=true
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                print_warning "Unknown option: $arg"
                ;;
        esac
    done
    
    # Execute setup steps
    check_system_requirements
    
    if [ "$SKIP_VENV" = "false" ]; then
        setup_virtual_environment
        install_dependencies
    fi
    
    setup_directories
    create_sample_config
    
    if [ "$SKIP_SAMPLES" = "false" ]; then
        download_sample_files
    fi
    
    if [ "$SKIP_HOOKS" = "false" ]; then
        setup_pre_commit_hooks
    fi
    
    setup_development_tools
    verify_installation
    show_next_steps
}

# Run main function
main "$@"