#!/bin/bash

# Benchmark script for PDF Outline Extractor
# This script runs performance benchmarks and generates detailed reports

set -e  # Exit on any error

# Configuration
IMAGE_NAME="pdf-outline-extractor"
IMAGE_TAG="latest"
BENCHMARK_CONTAINER_NAME="pdf-extractor-benchmark"

# Benchmark directories
BENCHMARK_DIR="$(pwd)/benchmarks"
RESULTS_DIR="$BENCHMARK_DIR/results"
SAMPLE_DIR="$BENCHMARK_DIR/samples"

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

# Setup benchmark environment
setup_benchmark_environment() {
    print_status "Setting up benchmark environment..."
    
    # Create benchmark directories
    mkdir -p "$BENCHMARK_DIR"
    mkdir -p "$RESULTS_DIR"
    mkdir -p "$SAMPLE_DIR"
    
    # Clean up any existing benchmark container
    if docker ps -a --format '{{.Names}}' | grep -q "^${BENCHMARK_CONTAINER_NAME}$"; then
        docker rm -f "$BENCHMARK_CONTAINER_NAME" > /dev/null 2>&1
    fi
    
    print_status "Benchmark environment ready"
}

# Generate test PDFs of various sizes
generate_test_pdfs() {
    print_status "Generating test PDFs..."
    
    # Create test PDFs using Python
    docker run --name "$BENCHMARK_CONTAINER_NAME" --rm \
        -v "$SAMPLE_DIR:/app/samples" \
        "$IMAGE_NAME:$IMAGE_TAG" \
        python -c "
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

def create_test_pdf(filename, pages, headings_per_page=2):
    c = canvas.Canvas(f'/app/samples/{filename}', pagesize=letter)
    
    for page in range(1, pages + 1):
        # Add page content
        c.setFont('Helvetica-Bold', 18)
        c.drawString(100, 750, f'Page {page}')
        
        # Add headings
        y_pos = 700
        for h in range(headings_per_page):
            if h == 0:
                c.setFont('Helvetica-Bold', 16)
                c.drawString(100, y_pos, f'{page}.{h+1} Main Heading')
            else:
                c.setFont('Helvetica-Bold', 14)
                c.drawString(120, y_pos, f'{page}.{h+1}.1 Sub Heading')
            
            # Add body text
            c.setFont('Helvetica', 12)
            c.drawString(100, y_pos - 20, 'This is sample body text for the heading.')
            y_pos -= 60
        
        c.showPage()
    
    c.save()
    print(f'Created {filename} with {pages} pages')

# Generate test files
test_files = [
    ('small_5pages.pdf', 5, 2),
    ('medium_25pages.pdf', 25, 3),
    ('large_50pages.pdf', 50, 4),
    ('xlarge_100pages.pdf', 100, 5),
]

for filename, pages, headings in test_files:
    if not os.path.exists(f'/app/samples/{filename}'):
        create_test_pdf(filename, pages, headings)
"
    
    print_success "Test PDFs generated"
}

# Run performance benchmark
run_performance_benchmark() {
    local test_file="$1"
    local test_name="$2"
    
    print_status "Running benchmark: $test_name"
    
    # Create temporary directories for this test
    local temp_input="/tmp/benchmark_input_$$"
    local temp_output="/tmp/benchmark_output_$$"
    
    mkdir -p "$temp_input" "$temp_output"
    
    # Copy test file
    cp "$SAMPLE_DIR/$test_file" "$temp_input/"
    
    # Run benchmark with time measurement
    local start_time=$(date +%s.%N)
    
    docker run --name "$BENCHMARK_CONTAINER_NAME" --rm \
        -v "$temp_input:/app/input:ro" \
        -v "$temp_output:/app/output" \
        "$IMAGE_NAME:$IMAGE_TAG" \
        python src/main.py --benchmark > "$RESULTS_DIR/${test_name}_output.log" 2>&1
    
    local end_time=$(date +%s.%N)
    local duration=$(echo "$end_time - $start_time" | bc)
    
    # Extract metrics from output
    local output_file=$(find "$temp_output" -name "*.json" | head -1)
    local headings_count=0
    local processing_time=0
    
    if [ -f "$output_file" ]; then
        headings_count=$(python3 -c "
import json
with open('$output_file', 'r') as f:
    data = json.load(f)
    print(data.get('statistics', {}).get('total_headings', 0))
" 2>/dev/null || echo "0")
        
        processing_time=$(python3 -c "
import json
with open('$output_file', 'r') as f:
    data = json.load(f)
    print(data.get('document', {}).get('processing_time', 0))
" 2>/dev/null || echo "0")
    fi
    
    # Get file size
    local file_size=$(stat -f%z "$SAMPLE_DIR/$test_file" 2>/dev/null || stat -c%s "$SAMPLE_DIR/$test_file" 2>/dev/null || echo "0")
    local file_size_mb=$(echo "scale=2; $file_size / 1024 / 1024" | bc)
    
    # Save benchmark results
    cat >> "$RESULTS_DIR/benchmark_results.csv" << EOF
$test_name,$test_file,$file_size_mb,$duration,$processing_time,$headings_count
EOF
    
    print_success "Benchmark completed: $test_name (${duration}s)"
    
    # Clean up
    rm -rf "$temp_input" "$temp_output"
}

# Run memory benchmark
run_memory_benchmark() {
    print_status "Running memory usage benchmark..."
    
    # Run with memory monitoring
    docker run --name "$BENCHMARK_CONTAINER_NAME" --rm \
        -v "$SAMPLE_DIR:/app/input:ro" \
        -v "$RESULTS_DIR:/app/output" \
        --memory=1g \
        "$IMAGE_NAME:$IMAGE_TAG" \
        /bin/bash -c "
            python -c '
import psutil
import time
import json
import subprocess
import os

def monitor_memory():
    process = subprocess.Popen([\"python\", \"src/main.py\"], 
                              stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE)
    
    max_memory = 0
    memory_samples = []
    
    while process.poll() is None:
        try:
            proc = psutil.Process(process.pid)
            memory_mb = proc.memory_info().rss / 1024 / 1024
            max_memory = max(max_memory, memory_mb)
            memory_samples.append(memory_mb)
            time.sleep(0.1)
        except psutil.NoSuchProcess:
            break
    
    process.wait()
    
    results = {
        \"max_memory_mb\": max_memory,
        \"avg_memory_mb\": sum(memory_samples) / len(memory_samples) if memory_samples else 0,
        \"samples\": len(memory_samples)
    }
    
    with open(\"/app/output/memory_benchmark.json\", \"w\") as f:
        json.dump(results, f, indent=2)
    
    print(f\"Max memory usage: {max_memory:.2f} MB\")

monitor_memory()
'"
    
    print_success "Memory benchmark completed"
}

# Run concurrent processing benchmark
run_concurrency_benchmark() {
    print_status "Running concurrency benchmark..."
    
    # Test different batch sizes
    for batch_size in 1 2 5; do
        print_status "Testing batch size: $batch_size"
        
        local start_time=$(date +%s.%N)
        
        docker run --name "$BENCHMARK_CONTAINER_NAME" --rm \
            -v "$SAMPLE_DIR:/app/input:ro" \
            -v "$RESULTS_DIR:/app/output" \
            -e BATCH_SIZE=$batch_size \
            "$IMAGE_NAME:$IMAGE_TAG" \
            python src/main.py > "$RESULTS_DIR/concurrency_batch${batch_size}.log" 2>&1
        
        local end_time=$(date +%s.%N)
        local duration=$(echo "$end_time - $start_time" | bc)
        
        echo "batch_size_${batch_size},$duration" >> "$RESULTS_DIR/concurrency_results.csv"
        
        print_status "Batch size $batch_size completed in ${duration}s"
    done
    
    print_success "Concurrency benchmark completed"
}

# Generate benchmark report
generate_benchmark_report() {
    print_status "Generating benchmark report..."
    
    local report_file="$RESULTS_DIR/benchmark_report.html"
    
    # Create HTML report
    cat > "$report_file" << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>PDF Outline Extractor - Benchmark Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
        th { background-color: #f2f2f2; }
        .metric { background-color: #e8f4f8; }
        .good { color: green; font-weight: bold; }
        .warning { color: orange; font-weight: bold; }
        .error { color: red; font-weight: bold; }
    </style>
</head>
<body>
    <h1>PDF Outline Extractor - Benchmark Report</h1>
    <p>Generated: <span id="timestamp"></span></p>
    
    <h2>Performance Benchmarks</h2>
    <table>
        <tr>
            <th>Test Name</th>
            <th>File</th>
            <th>File Size (MB)</th>
            <th>Total Time (s)</th>
            <th>Processing Time (s)</th>
            <th>Headings Found</th>
            <th>Performance</th>
        </tr>
EOF
    
    # Add benchmark data
    if [ -f "$RESULTS_DIR/benchmark_results.csv" ]; then
        while IFS=',' read -r test_name file_name file_size total_time proc_time headings; do
            local performance_class="good"
            if (( $(echo "$proc_time > 10" | bc -l) )); then
                performance_class="error"
            elif (( $(echo "$proc_time > 5" | bc -l) )); then
                performance_class="warning"
            fi
            
            cat >> "$report_file" << EOF
        <tr>
            <td>$test_name</td>
            <td>$file_name</td>
            <td>$file_size</td>
            <td>$total_time</td>
            <td class="$performance_class">$proc_time</td>
            <td>$headings</td>
            <td class="$performance_class">$(if (( $(echo "$proc_time <= 10" | bc -l) )); then echo "PASS"; else echo "FAIL"; fi)</td>
        </tr>
EOF
        done < "$RESULTS_DIR/benchmark_results.csv"
    fi
    
    cat >> "$report_file" << 'EOF'
    </table>
    
    <h2>Memory Usage</h2>
    <div id="memory-info">Loading memory benchmark data...</div>
    
    <h2>Concurrency Performance</h2>
    <div id="concurrency-info">Loading concurrency benchmark data...</div>
    
    <script>
        document.getElementById('timestamp').textContent = new Date().toLocaleString();
        
        // Load memory data
        fetch('memory_benchmark.json')
            .then(response => response.json())
            .then(data => {
                document.getElementById('memory-info').innerHTML = 
                    `<p>Maximum Memory Usage: ${data.max_memory_mb.toFixed(2)} MB</p>
                     <p>Average Memory Usage: ${data.avg_memory_mb.toFixed(2)} MB</p>`;
            })
            .catch(() => {
                document.getElementById('memory-info').innerHTML = '<p>Memory benchmark data not available</p>';
            });
    </script>
</body>
</html>
EOF
    
    print_success "Benchmark report generated: $report_file"
}

# Show benchmark summary
show_benchmark_summary() {
    print_status "Benchmark Summary:"
    echo ""
    
    if [ -f "$RESULTS_DIR/benchmark_results.csv" ]; then
        echo "Performance Results:"
        printf "%-20s %-15s %-10s %-12s %-10s\n" "Test" "File Size (MB)" "Time (s)" "Headings" "Status"
        echo "--------------------------------------------------------------------------------"
        
        while IFS=',' read -r test_name file_name file_size total_time proc_time headings; do
            local status="PASS"
            if (( $(echo "$proc_time > 10" | bc -l) )); then
                status="FAIL"
            fi
            
            printf "%-20s %-15s %-10s %-12s %-10s\n" "$test_name" "$file_size" "$proc_time" "$headings" "$status"
        done < "$RESULTS_DIR/benchmark_results.csv"
    else
        print_warning "No benchmark results found"
    fi
    
    echo ""
    print_status "Detailed results available in: $RESULTS_DIR/"
}

# Show usage information
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --performance    Run performance benchmarks only"
    echo "  --memory         Run memory benchmarks only"
    echo "  --concurrency    Run concurrency benchmarks only"
    echo "  --generate-pdfs  Generate test PDFs only"
    echo "  --all            Run all benchmarks (default)"
    echo "  --help           Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0               # Run all benchmarks"
    echo "  $0 --performance # Run performance tests only"
    echo "  $0 --memory      # Run memory tests only"
    echo ""
}

# Main execution
main() {
    echo "PDF Outline Extractor - Benchmark Script"
    echo "========================================"
    echo ""
    
    # Parse command line arguments
    RUN_PERFORMANCE=false
    RUN_MEMORY=false
    RUN_CONCURRENCY=false
    GENERATE_PDFS=false
    RUN_ALL=true
    
    for arg in "$@"; do
        case $arg in
            --performance)
                RUN_PERFORMANCE=true
                RUN_ALL=false
                ;;
            --memory)
                RUN_MEMORY=true
                RUN_ALL=false
                ;;
            --concurrency)
                RUN_CONCURRENCY=true
                RUN_ALL=false
                ;;
            --generate-pdfs)
                GENERATE_PDFS=true
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
    
    # Execute benchmark steps
    check_prerequisites
    setup_benchmark_environment
    
    # Generate test PDFs if needed
    if [ "$RUN_ALL" = "true" ] || [ "$GENERATE_PDFS" = "true" ]; then
        generate_test_pdfs
    fi
    
    # Initialize results files
    echo "test_name,file_name,file_size_mb,total_time,processing_time,headings_count" > "$RESULTS_DIR/benchmark_results.csv"
    echo "test_type,duration" > "$RESULTS_DIR/concurrency_results.csv"
    
    # Run selected benchmarks
    if [ "$RUN_ALL" = "true" ] || [ "$RUN_PERFORMANCE" = "true" ]; then
        run_performance_benchmark "small_5pages.pdf" "small_document"
        run_performance_benchmark "medium_25pages.pdf" "medium_document"
        run_performance_benchmark "large_50pages.pdf" "large_document"
        run_performance_benchmark "xlarge_100pages.pdf" "xlarge_document"
    fi
    
    if [ "$RUN_ALL" = "true" ] || [ "$RUN_MEMORY" = "true" ]; then
        run_memory_benchmark
    fi
    
    if [ "$RUN_ALL" = "true" ] || [ "$RUN_CONCURRENCY" = "true" ]; then
        run_concurrency_benchmark
    fi
    
    # Generate report and summary
    generate_benchmark_report
    show_benchmark_summary
    
    echo ""
    print_success "Benchmark completed successfully!"
    echo ""
    print_status "Results available in:"
    echo "  - HTML Report: $RESULTS_DIR/benchmark_report.html"
    echo "  - CSV Data: $RESULTS_DIR/benchmark_results.csv"
    echo "  - Logs: $RESULTS_DIR/*.log"
    echo ""
}

# Run main function
main "$@"