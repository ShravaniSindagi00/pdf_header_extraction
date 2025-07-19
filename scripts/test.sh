#!/bin/bash

# Test script for PDF Outline Extractor
# This script runs the complete test suite including unit tests, integration tests, and benchmarks

set -e  # Exit on any error

# Configuration
IMAGE_NAME="pdf-outline-extractor"
IMAGE_TAG="latest"
TEST_CONTAINER_NAME="pdf-extractor-test"

# Test directories
TEST_DIR="$(pwd)/tests"
FIXTURES_DIR="$TEST_DIR/fixtures"
COVERAGE_DIR="$(pwd)/coverage"

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

# Setup test environment
setup_test_environment() {
    print_status "Setting up test environment..."
    
    # Create coverage directory
    mkdir -p "$COVERAGE_DIR"
    
    # Clean up any existing test container
    if docker ps -a --format '{{.Names}}' | grep -q "^${TEST_CONTAINER_NAME}$"; then
        docker rm -f "$TEST_CONTAINER_NAME" > /dev/null 2>&1
    fi
    
    print_status "Test environment ready"
}

# Run unit tests
run_unit_tests() {
    print_status "Running unit tests..."
    
    docker run --name "$TEST_CONTAINER_NAME" --rm \
        -v "$(pwd):/app" \
        -w /app \
        "$IMAGE_NAME:$IMAGE_TAG" \
        pytest tests/unit/ -v --tb=short --color=yes
    
    if [ $? -eq 0 ]; then
        print_success "Unit tests passed"
    else
        print_error "Unit tests failed"
        return 1
    fi
}

# Run integration tests
run_integration_tests() {
    print_status "Running integration tests..."
    
    # Ensure test fixtures exist
    if [ ! -d "$FIXTURES_DIR" ]; then
        print_warning "Test fixtures directory not found: $FIXTURES_DIR"
        print_status "Skipping integration tests"
        return 0
    fi
    
    docker run --name "$TEST_CONTAINER_NAME" --rm \
        -v "$(pwd):/app" \
        -w /app \
        "$IMAGE_NAME:$IMAGE_TAG" \
        pytest tests/integration/ -v --tb=short --color=yes
    
    if [ $? -eq 0 ]; then
        print_success "Integration tests passed"
    else
        print_error "Integration tests failed"
        return 1
    fi
}

# Run tests with coverage
run_tests_with_coverage() {
    print_status "Running tests with coverage analysis..."
    
    docker run --name "$TEST_CONTAINER_NAME" --rm \
        -v "$(pwd):/app" \
        -w /app \
        "$IMAGE_NAME:$IMAGE_TAG" \
        pytest tests/ \
        --cov=src \
        --cov-report=html:coverage/html \
        --cov-report=term-missing \
        --cov-report=xml:coverage/coverage.xml \
        --cov-fail-under=70 \
        -v
    
    if [ $? -eq 0 ]; then
        print_success "Coverage tests passed"
        
        # Show coverage summary
        if [ -f "coverage/coverage.xml" ]; then
            print_status "Coverage report generated: coverage/html/index.html"
        fi
    else
        print_error "Coverage tests failed"
        return 1
    fi
}

# Run performance benchmarks
run_benchmarks() {
    print_status "Running performance benchmarks..."
    
    # Check if benchmark fixtures exist
    if [ ! -f "$FIXTURES_DIR/sample_simple.pdf" ]; then
        print_warning "Benchmark fixtures not found, skipping performance tests"
        return 0
    fi
    
    docker run --name "$TEST_CONTAINER_NAME" --rm \
        -v "$(pwd):/app" \
        -w /app \
        "$IMAGE_NAME:$IMAGE_TAG" \
        pytest tests/ -k "benchmark" --benchmark-only --benchmark-sort=mean -v
    
    if [ $? -eq 0 ]; then
        print_success "Benchmark tests completed"
    else
        print_warning "Some benchmark tests failed"
    fi
}

# Run linting and code quality checks
run_code_quality_checks() {
    print_status "Running code quality checks..."
    
    # Run flake8 for style checking
    print_status "Running flake8..."
    docker run --name "$TEST_CONTAINER_NAME" --rm \
        -v "$(pwd):/app" \
        -w /app \
        "$IMAGE_NAME:$IMAGE_TAG" \
        flake8 src/ --max-line-length=100 --ignore=E203,W503
    
    if [ $? -eq 0 ]; then
        print_success "Flake8 checks passed"
    else
        print_warning "Flake8 found style issues"
    fi
    
    # Run mypy for type checking
    print_status "Running mypy..."
    docker run --name "$TEST_CONTAINER_NAME" --rm \
        -v "$(pwd):/app" \
        -w /app \
        "$IMAGE_NAME:$IMAGE_TAG" \
        mypy src/ --ignore-missing-imports --no-strict-optional
    
    if [ $? -eq 0 ]; then
        print_success "MyPy type checks passed"
    else
        print_warning "MyPy found type issues"
    fi
}

# Run smoke tests on sample PDFs
run_smoke_tests() {
    print_status "Running smoke tests..."
    
    # Create temporary test input/output directories
    TEMP_INPUT="/tmp/pdf_extractor_test_input"
    TEMP_OUTPUT="/tmp/pdf_extractor_test_output"
    
    mkdir -p "$TEMP_INPUT" "$TEMP_OUTPUT"
    
    # Copy test fixtures if available
    if [ -f "$FIXTURES_DIR/sample_simple.pdf" ]; then
        cp "$FIXTURES_DIR/sample_simple.pdf" "$TEMP_INPUT/"
        
        # Run extraction on test file
        docker run --name "$TEST_CONTAINER_NAME" --rm \
            -v "$TEMP_INPUT:/app/input:ro" \
            -v "$TEMP_OUTPUT:/app/output" \
            "$IMAGE_NAME:$IMAGE_TAG" \
            python src/main.py
        
        # Check if output was generated
        if [ -f "$TEMP_OUTPUT/sample_simple_outline.json" ]; then
            print_success "Smoke test passed - output generated"
        else
            print_error "Smoke test failed - no output generated"
            return 1
        fi
    else
        print_warning "No test fixtures available for smoke test"
    fi
    
    # Clean up
    rm -rf "$TEMP_INPUT" "$TEMP_OUTPUT"
}

# Generate test report
generate_test_report() {
    print_status "Generating test report..."
    
    REPORT_FILE="test_report.txt"
    
    {
        echo "PDF Outline Extractor - Test Report"
        echo "=================================="
        echo "Generated: $(date)"
        echo ""
        
        echo "Test Environment:"
        echo "- Docker Image: $IMAGE_NAME:$IMAGE_TAG"
        echo "- Test Directory: $TEST_DIR"
        echo ""
        
        echo "Test Results:"
        if [ "$UNIT_TESTS_PASSED" = "true" ]; then
            echo "✓ Unit Tests: PASSED"
        else
            echo "✗ Unit Tests: FAILED"
        fi
        
        if [ "$INTEGRATION_TESTS_PASSED" = "true" ]; then
            echo "✓ Integration Tests: PASSED"
        else
            echo "✗ Integration Tests: FAILED"
        fi
        
        if [ "$SMOKE_TESTS_PASSED" = "true" ]; then
            echo "✓ Smoke Tests: PASSED"
        else
            echo "✗ Smoke Tests: FAILED"
        fi
        
        echo ""
        echo "Coverage Information:"
        if [ -f "coverage/coverage.xml" ]; then
            echo "- Coverage report: coverage/html/index.html"
        else
            echo "- No coverage data available"
        fi
        
    } > "$REPORT_FILE"
    
    print_status "Test report saved: $REPORT_FILE"
}

# Show usage information
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --unit           Run only unit tests"
    echo "  --integration    Run only integration tests"
    echo "  --coverage       Run tests with coverage analysis"
    echo "  --benchmark      Run performance benchmarks"
    echo "  --quality        Run code quality checks"
    echo "  --smoke          Run smoke tests only"
    echo "  --all            Run all tests (default)"
    echo "  --help           Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0               # Run all tests"
    echo "  $0 --unit        # Run only unit tests"
    echo "  $0 --coverage    # Run tests with coverage"
    echo "  $0 --benchmark   # Run performance benchmarks"
    echo ""
}

# Main execution
main() {
    echo "PDF Outline Extractor - Test Script"
    echo "==================================="
    echo ""
    
    # Parse command line arguments
    RUN_UNIT=false
    RUN_INTEGRATION=false
    RUN_COVERAGE=false
    RUN_BENCHMARK=false
    RUN_QUALITY=false
    RUN_SMOKE=false
    RUN_ALL=true
    
    for arg in "$@"; do
        case $arg in
            --unit)
                RUN_UNIT=true
                RUN_ALL=false
                ;;
            --integration)
                RUN_INTEGRATION=true
                RUN_ALL=false
                ;;
            --coverage)
                RUN_COVERAGE=true
                RUN_ALL=false
                ;;
            --benchmark)
                RUN_BENCHMARK=true
                RUN_ALL=false
                ;;
            --quality)
                RUN_QUALITY=true
                RUN_ALL=false
                ;;
            --smoke)
                RUN_SMOKE=true
                RUN_ALL=false
                ;;
            --all)
                RUN_ALL=true
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
    
    # Initialize test results
    UNIT_TESTS_PASSED=false
    INTEGRATION_TESTS_PASSED=false
    SMOKE_TESTS_PASSED=false
    
    # Execute test steps
    check_prerequisites
    setup_test_environment
    
    # Run selected tests
    if [ "$RUN_ALL" = "true" ] || [ "$RUN_UNIT" = "true" ]; then
        if run_unit_tests; then
            UNIT_TESTS_PASSED=true
        fi
    fi
    
    if [ "$RUN_ALL" = "true" ] || [ "$RUN_INTEGRATION" = "true" ]; then
        if run_integration_tests; then
            INTEGRATION_TESTS_PASSED=true
        fi
    fi
    
    if [ "$RUN_ALL" = "true" ] || [ "$RUN_SMOKE" = "true" ]; then
        if run_smoke_tests; then
            SMOKE_TESTS_PASSED=true
        fi
    fi
    
    if [ "$RUN_COVERAGE" = "true" ]; then
        run_tests_with_coverage
    fi
    
    if [ "$RUN_ALL" = "true" ] || [ "$RUN_BENCHMARK" = "true" ]; then
        run_benchmarks
    fi
    
    if [ "$RUN_ALL" = "true" ] || [ "$RUN_QUALITY" = "true" ]; then
        run_code_quality_checks
    fi
    
    # Generate report
    generate_test_report
    
    echo ""
    if [ "$UNIT_TESTS_PASSED" = "true" ] && [ "$INTEGRATION_TESTS_PASSED" = "true" ] && [ "$SMOKE_TESTS_PASSED" = "true" ]; then
        print_success "All tests completed successfully!"
    else
        print_warning "Some tests failed - check the output above"
    fi
    
    echo ""
    print_status "Test artifacts:"
    echo "  - Test report: test_report.txt"
    if [ -d "coverage" ]; then
        echo "  - Coverage report: coverage/html/index.html"
    fi
    echo ""
}

# Run main function
main "$@"