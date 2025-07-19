#!/bin/bash

# Build script for PDF Outline Extractor
# This script builds the Docker image for the application

set -e  # Exit on any error

# Configuration
IMAGE_NAME="pdf-outline-extractor"
IMAGE_TAG="latest"
DOCKERFILE="Dockerfile"

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

# Check if Docker is installed and running
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        print_error "Docker is not running. Please start Docker first."
        exit 1
    fi
    
    print_status "Docker is available and running"
}

# Clean up old images if requested
cleanup_old_images() {
    if [[ "$1" == "--clean" ]]; then
        print_status "Cleaning up old images..."
        
        # Remove old images
        if docker images -q "$IMAGE_NAME" | grep -q .; then
            docker rmi $(docker images -q "$IMAGE_NAME") 2>/dev/null || true
            print_status "Removed old images"
        fi
        
        # Clean up dangling images
        if docker images -f "dangling=true" -q | grep -q .; then
            docker rmi $(docker images -f "dangling=true" -q) 2>/dev/null || true
            print_status "Removed dangling images"
        fi
    fi
}

# Build the Docker image
build_image() {
    print_status "Building Docker image: $IMAGE_NAME:$IMAGE_TAG"
    
    # Build with build args for better caching
    docker build \
        --tag "$IMAGE_NAME:$IMAGE_TAG" \
        --file "$DOCKERFILE" \
        --build-arg BUILDKIT_INLINE_CACHE=1 \
        --progress=plain \
        .
    
    if [ $? -eq 0 ]; then
        print_success "Docker image built successfully"
    else
        print_error "Failed to build Docker image"
        exit 1
    fi
}

# Verify the built image
verify_image() {
    print_status "Verifying built image..."
    
    # Check if image exists
    if docker images "$IMAGE_NAME:$IMAGE_TAG" | grep -q "$IMAGE_NAME"; then
        print_success "Image verification passed"
        
        # Show image details
        echo ""
        print_status "Image details:"
        docker images "$IMAGE_NAME:$IMAGE_TAG" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
        
        # Show image layers (optional)
        if [[ "$1" == "--verbose" ]]; then
            echo ""
            print_status "Image layers:"
            docker history "$IMAGE_NAME:$IMAGE_TAG" --no-trunc
        fi
    else
        print_error "Image verification failed"
        exit 1
    fi
}

# Run basic smoke test
smoke_test() {
    print_status "Running smoke test..."
    
    # Test that the container can start and import modules
    if docker run --rm "$IMAGE_NAME:$IMAGE_TAG" python -c "import src.extractor.pdf_parser; print('Import test passed')"; then
        print_success "Smoke test passed"
    else
        print_error "Smoke test failed"
        exit 1
    fi
}

# Main execution
main() {
    echo "PDF Outline Extractor - Build Script"
    echo "===================================="
    echo ""
    
    # Parse command line arguments
    CLEAN_FLAG=""
    VERBOSE_FLAG=""
    SKIP_TEST_FLAG=""
    
    for arg in "$@"; do
        case $arg in
            --clean)
                CLEAN_FLAG="--clean"
                ;;
            --verbose)
                VERBOSE_FLAG="--verbose"
                ;;
            --skip-test)
                SKIP_TEST_FLAG="--skip-test"
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --clean      Remove old images before building"
                echo "  --verbose    Show detailed build information"
                echo "  --skip-test  Skip smoke test after building"
                echo "  --help       Show this help message"
                echo ""
                exit 0
                ;;
            *)
                print_warning "Unknown option: $arg"
                ;;
        esac
    done
    
    # Execute build steps
    check_docker
    cleanup_old_images "$CLEAN_FLAG"
    build_image
    verify_image "$VERBOSE_FLAG"
    
    if [[ "$SKIP_TEST_FLAG" != "--skip-test" ]]; then
        smoke_test
    fi
    
    echo ""
    print_success "Build completed successfully!"
    echo ""
    print_status "Next steps:"
    echo "  1. Place PDF files in the 'input/' directory"
    echo "  2. Run: ./scripts/run.sh"
    echo "  3. Check results in the 'output/' directory"
    echo ""
    print_status "For testing: ./scripts/test.sh"
    print_status "For help: docker run --rm $IMAGE_NAME:$IMAGE_TAG python src/main.py --help"
}

# Run main function
main "$@"