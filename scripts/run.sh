#!/bin/bash

# Run script for PDF Outline Extractor
# This script runs the PDF extraction process using Docker

set -e  # Exit on any error

# Configuration
IMAGE_NAME="pdf-outline-extractor"
IMAGE_TAG="latest"
CONTAINER_NAME="pdf-extractor-run"

# Directories
INPUT_DIR="$(pwd)/input"
OUTPUT_DIR="$(pwd)/output"
LOGS_DIR="$(pwd)/logs"

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

# Check prerequisites
check_prerequisites() {
    # Check if Docker is available
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        print_error "Docker is not running. Please start Docker first."
        exit 1
    fi
    
    # Check if image exists
    if ! docker images "$IMAGE_NAME:$IMAGE_TAG" | grep -q "$IMAGE_NAME"; then
        print_error "Docker image '$IMAGE_NAME:$IMAGE_TAG' not found."
        print_status "Please build the image first: ./scripts/build.sh"
        exit 1
    fi
    
    print_status "Prerequisites check passed"
}

# Setup directories
setup_directories() {
    print_status "Setting up directories..."
    
    # Create directories if they don't exist
    mkdir -p "$INPUT_DIR"
    mkdir -p "$OUTPUT_DIR"
    mkdir -p "$LOGS_DIR"
    
    # Set proper permissions
    chmod 755 "$INPUT_DIR" "$OUTPUT_DIR" "$LOGS_DIR"
    
    print_status "Directories ready"
}

# Check input files
check_input_files() {
    print_status "Checking input files..."
    
    # Count PDF files
    PDF_COUNT=$(find "$INPUT_DIR" -name "*.pdf" -type f | wc -l)
    
    if [ "$PDF_COUNT" -eq 0 ]; then
        print_warning "No PDF files found in input directory: $INPUT_DIR"
        print_status "Please add PDF files to process and run again."
        exit 1
    fi
    
    print_status "Found $PDF_COUNT PDF file(s) to process"
    
    # List files if verbose
    if [[ "$1" == "--verbose" ]]; then
        echo ""
        print_status "Input files:"
        find "$INPUT_DIR" -name "*.pdf" -type f -exec basename {} \; | sort
        echo ""
    fi
}

# Clean up any existing container
cleanup_container() {
    if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        print_status "Removing existing container..."
        docker rm -f "$CONTAINER_NAME" > /dev/null 2>&1
    fi
}

# Run the extraction process
run_extraction() {
    print_status "Starting PDF outline extraction..."
    
    # Prepare Docker run command
    DOCKER_CMD="docker run"
    DOCKER_CMD="$DOCKER_CMD --name $CONTAINER_NAME"
    DOCKER_CMD="$DOCKER_CMD --rm"
    DOCKER_CMD="$DOCKER_CMD -v $INPUT_DIR:/app/input:ro"
    DOCKER_CMD="$DOCKER_CMD -v $OUTPUT_DIR:/app/output"
    DOCKER_CMD="$DOCKER_CMD -v $LOGS_DIR:/app/logs"
    
    # Add environment variables
    DOCKER_CMD="$DOCKER_CMD -e LOG_LEVEL=${LOG_LEVEL:-INFO}"
    DOCKER_CMD="$DOCKER_CMD -e MAX_PROCESSING_TIME=${MAX_PROCESSING_TIME:-10}"
    DOCKER_CMD="$DOCKER_CMD -e BATCH_SIZE=${BATCH_SIZE:-5}"
    
    # Add interactive flag if running in terminal
    if [ -t 0 ]; then
        DOCKER_CMD="$DOCKER_CMD -it"
    fi
    
    # Add image and command
    DOCKER_CMD="$DOCKER_CMD $IMAGE_NAME:$IMAGE_TAG"
    
    # Add application arguments
    if [[ "$VERBOSE_FLAG" == "--verbose" ]]; then
        DOCKER_CMD="$DOCKER_CMD python src/main.py --verbose"
    elif [[ "$BENCHMARK_FLAG" == "--benchmark" ]]; then
        DOCKER_CMD="$DOCKER_CMD python src/main.py --benchmark"
    else
        DOCKER_CMD="$DOCKER_CMD python src/main.py"
    fi
    
    # Execute the command
    echo ""
    print_status "Executing: $DOCKER_CMD"
    echo ""
    
    eval $DOCKER_CMD
    
    if [ $? -eq 0 ]; then
        print_success "Extraction completed successfully"
    else
        print_error "Extraction failed"
        exit 1
    fi
}

# Show results summary
show_results() {
    print_status "Processing results:"
    echo ""
    
    # Count output files
    JSON_COUNT=$(find "$OUTPUT_DIR" -name "*_outline.json" -type f | wc -l)
    
    if [ "$JSON_COUNT" -gt 0 ]; then
        print_success "Generated $JSON_COUNT outline file(s)"
        
        # List output files
        echo ""
        print_status "Output files:"
        find "$OUTPUT_DIR" -name "*_outline.json" -type f -exec basename {} \; | sort
        
        # Show file sizes
        if [[ "$VERBOSE_FLAG" == "--verbose" ]]; then
            echo ""
            print_status "File details:"
            find "$OUTPUT_DIR" -name "*_outline.json" -type f -exec ls -lh {} \; | awk '{print $5, $9}' | sort
        fi
    else
        print_warning "No output files generated"
    fi
    
    # Check for log files
    if [ -f "$LOGS_DIR/extractor.log" ]; then
        LOG_SIZE=$(stat -f%z "$LOGS_DIR/extractor.log" 2>/dev/null || stat -c%s "$LOGS_DIR/extractor.log" 2>/dev/null || echo "0")
        if [ "$LOG_SIZE" -gt 0 ]; then
            print_status "Log file available: logs/extractor.log"
        fi
    fi
}

# Show usage information
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --verbose     Enable verbose output and detailed logging"
    echo "  --benchmark   Run in benchmark mode with performance metrics"
    echo "  --clean       Clean output directory before processing"
    echo "  --help        Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  LOG_LEVEL              Logging level (DEBUG, INFO, WARNING, ERROR)"
    echo "  MAX_PROCESSING_TIME    Maximum processing time per document (seconds)"
    echo "  BATCH_SIZE            Number of documents to process concurrently"
    echo ""
    echo "Examples:"
    echo "  $0                    # Process all PDFs in input/ directory"
    echo "  $0 --verbose          # Process with detailed output"
    echo "  $0 --benchmark        # Process with performance metrics"
    echo "  LOG_LEVEL=DEBUG $0    # Process with debug logging"
    echo ""
}

# Main execution
main() {
    echo "PDF Outline Extractor - Run Script"
    echo "=================================="
    echo ""
    
    # Parse command line arguments
    VERBOSE_FLAG=""
    BENCHMARK_FLAG=""
    CLEAN_FLAG=""
    
    for arg in "$@"; do
        case $arg in
            --verbose)
                VERBOSE_FLAG="--verbose"
                ;;
            --benchmark)
                BENCHMARK_FLAG="--benchmark"
                ;;
            --clean)
                CLEAN_FLAG="--clean"
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
    
    # Clean output directory if requested
    if [[ "$CLEAN_FLAG" == "--clean" ]]; then
        print_status "Cleaning output directory..."
        rm -f "$OUTPUT_DIR"/*.json
        rm -f "$LOGS_DIR"/*.log
    fi
    
    # Execute run steps
    check_prerequisites
    setup_directories
    check_input_files "$VERBOSE_FLAG"
    cleanup_container
    run_extraction
    show_results
    
    echo ""
    print_success "Run completed successfully!"
    echo ""
    print_status "Next steps:"
    echo "  1. Check output files in: $OUTPUT_DIR"
    echo "  2. Review logs in: $LOGS_DIR"
    echo "  3. For debugging: ./tools/debug_viewer.py <pdf_file>"
    echo ""
}

# Run main function
main "$@"