#!/usr/bin/env python3
"""
Benchmark Tool - Performance measurement for PDF outline extraction.

This tool measures processing time, memory usage, and accuracy metrics
for different document types and sizes.
"""

import sys
import time
import psutil
import argparse
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import matplotlib.pyplot as plt
import pandas as pd

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from extractor.pdf_parser import PDFParser
from extractor.heading_detector import HeadingDetector
from extractor.outline_builder import OutlineBuilder
from config.settings import Settings
from models.document import Document


@dataclass
class BenchmarkResult:
    """Results from a single benchmark run."""
    filename: str
    file_size_mb: float
    page_count: int
    processing_time: float
    memory_peak_mb: float
    memory_avg_mb: float
    headings_found: int
    h1_count: int
    h2_count: int
    h3_count: int
    avg_confidence: float
    quality_score: float
    success: bool
    error_message: Optional[str] = None


class MemoryMonitor:
    """Monitor memory usage during processing."""
    
    def __init__(self):
        self.process = psutil.Process()
        self.samples = []
        self.monitoring = False
    
    def start(self):
        """Start monitoring memory usage."""
        self.samples = []
        self.monitoring = True
        self._sample_memory()
    
    def stop(self):
        """Stop monitoring and return statistics."""
        self.monitoring = False
        if not self.samples:
            return 0, 0
        
        peak_mb = max(self.samples)
        avg_mb = sum(self.samples) / len(self.samples)
        return peak_mb, avg_mb
    
    def _sample_memory(self):
        """Sample current memory usage."""
        if self.monitoring:
            try:
                memory_mb = self.process.memory_info().rss / 1024 / 1024
                self.samples.append(memory_mb)
            except psutil.NoSuchProcess:
                pass


class PDFBenchmark:
    """PDF processing benchmark suite."""
    
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings()
        self.results: List[BenchmarkResult] = []
        
        # Initialize components
        self.parser = PDFParser(self.settings)
        self.detector = HeadingDetector(self.settings)
        self.builder = OutlineBuilder(self.settings)
    
    def benchmark_file(self, pdf_path: Path) -> BenchmarkResult:
        """Benchmark processing of a single PDF file."""
        print(f"Benchmarking: {pdf_path.name}")
        
        # Get file size
        file_size_mb = pdf_path.stat().st_size / (1024 * 1024)
        
        # Setup memory monitoring
        memory_monitor = MemoryMonitor()
        
        try:
            # Start timing and memory monitoring
            start_time = time.time()
            memory_monitor.start()
            
            # Parse PDF
            document = self.parser.parse(pdf_path)
            
            # Detect headings
            headings = self.detector.detect_headings(document)
            
            # Build outline
            outline = self.builder.build_outline(headings)
            document.outline = outline
            
            # Stop monitoring
            processing_time = time.time() - start_time
            memory_peak, memory_avg = memory_monitor.stop()
            
            # Calculate statistics
            h1_count = len([h for h in headings if h.level == 1])
            h2_count = len([h for h in headings if h.level == 2])
            h3_count = len([h for h in headings if h.level == 3])
            
            avg_confidence = sum(h.confidence for h in headings) / len(headings) if headings else 0
            quality_score = outline.quality_score if outline else 0
            
            result = BenchmarkResult(
                filename=pdf_path.name,
                file_size_mb=file_size_mb,
                page_count=document.page_count,
                processing_time=processing_time,
                memory_peak_mb=memory_peak,
                memory_avg_mb=memory_avg,
                headings_found=len(headings),
                h1_count=h1_count,
                h2_count=h2_count,
                h3_count=h3_count,
                avg_confidence=avg_confidence,
                quality_score=quality_score,
                success=True
            )
            
            print(f"  ✓ Processed in {processing_time:.2f}s, found {len(headings)} headings")
            return result
            
        except Exception as e:
            memory_monitor.stop()
            processing_time = time.time() - start_time
            
            result = BenchmarkResult(
                filename=pdf_path.name,
                file_size_mb=file_size_mb,
                page_count=0,
                processing_time=processing_time,
                memory_peak_mb=0,
                memory_avg_mb=0,
                headings_found=0,
                h1_count=0,
                h2_count=0,
                h3_count=0,
                avg_confidence=0,
                quality_score=0,
                success=False,
                error_message=str(e)
            )
            
            print(f"  ✗ Failed: {str(e)}")
            return result
    
    def benchmark_directory(self, input_dir: Path) -> List[BenchmarkResult]:
        """Benchmark all PDF files in a directory."""
        pdf_files = list(input_dir.glob("*.pdf"))
        
        if not pdf_files:
            print(f"No PDF files found in {input_dir}")
            return []
        
        print(f"Found {len(pdf_files)} PDF files to benchmark")
        
        results = []
        for pdf_file in pdf_files:
            result = self.benchmark_file(pdf_file)
            results.append(result)
            self.results.append(result)
        
        return results
    
    def generate_report(self, output_path: Path):
        """Generate comprehensive benchmark report."""
        if not self.results:
            print("No benchmark results to report")
            return
        
        # Create report directory
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Generate summary statistics
        self._generate_summary_report(output_path)
        
        # Generate detailed CSV
        self._generate_csv_report(output_path)
        
        # Generate visualizations
        self._generate_charts(output_path)
        
        # Generate HTML report
        self._generate_html_report(output_path)
        
        print(f"Benchmark report generated in: {output_path}")
    
    def _generate_summary_report(self, output_path: Path):
        """Generate summary statistics."""
        successful_results = [r for r in self.results if r.success]
        
        if not successful_results:
            return
        
        summary = {
            "total_files": len(self.results),
            "successful_files": len(successful_results),
            "failed_files": len(self.results) - len(successful_results),
            "total_pages": sum(r.page_count for r in successful_results),
            "total_processing_time": sum(r.processing_time for r in successful_results),
            "total_headings_found": sum(r.headings_found for r in successful_results),
            "performance_metrics": {
                "avg_processing_time": sum(r.processing_time for r in successful_results) / len(successful_results),
                "avg_pages_per_second": sum(r.page_count / max(r.processing_time, 0.1) for r in successful_results) / len(successful_results),
                "avg_memory_usage_mb": sum(r.memory_peak_mb for r in successful_results) / len(successful_results),
                "avg_headings_per_page": sum(r.headings_found / max(r.page_count, 1) for r in successful_results) / len(successful_results),
            },
            "quality_metrics": {
                "avg_confidence": sum(r.avg_confidence for r in successful_results) / len(successful_results),
                "avg_quality_score": sum(r.quality_score for r in successful_results) / len(successful_results),
            },
            "performance_targets": {
                "target_time_50_pages": 10.0,
                "files_meeting_target": len([r for r in successful_results if r.page_count <= 50 and r.processing_time <= 10.0]),
                "target_compliance_rate": len([r for r in successful_results if r.page_count <= 50 and r.processing_time <= 10.0]) / max(len([r for r in successful_results if r.page_count <= 50]), 1)
            }
        }
        
        with open(output_path / "summary.json", "w") as f:
            json.dump(summary, f, indent=2)
    
    def _generate_csv_report(self, output_path: Path):
        """Generate detailed CSV report."""
        data = []
        for result in self.results:
            data.append({
                "filename": result.filename,
                "file_size_mb": result.file_size_mb,
                "page_count": result.page_count,
                "processing_time": result.processing_time,
                "memory_peak_mb": result.memory_peak_mb,
                "memory_avg_mb": result.memory_avg_mb,
                "headings_found": result.headings_found,
                "h1_count": result.h1_count,
                "h2_count": result.h2_count,
                "h3_count": result.h3_count,
                "avg_confidence": result.avg_confidence,
                "quality_score": result.quality_score,
                "success": result.success,
                "error_message": result.error_message or "",
                "pages_per_second": result.page_count / max(result.processing_time, 0.1) if result.success else 0,
                "headings_per_page": result.headings_found / max(result.page_count, 1) if result.success else 0,
                "meets_performance_target": result.page_count <= 50 and result.processing_time <= 10.0 if result.success else False
            })
        
        df = pd.DataFrame(data)
        df.to_csv(output_path / "detailed_results.csv", index=False)
    
    def _generate_charts(self, output_path: Path):
        """Generate performance visualization charts."""
        successful_results = [r for r in self.results if r.success]
        
        if not successful_results:
            return
        
        # Create subplots
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
        
        # Processing time vs page count
        page_counts = [r.page_count for r in successful_results]
        processing_times = [r.processing_time for r in successful_results]
        
        ax1.scatter(page_counts, processing_times, alpha=0.7)
        ax1.plot([0, max(page_counts)], [0, max(page_counts) * 0.2], 'r--', label='Target (0.2s/page)')
        ax1.set_xlabel('Page Count')
        ax1.set_ylabel('Processing Time (s)')
        ax1.set_title('Processing Time vs Page Count')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Memory usage distribution
        memory_usage = [r.memory_peak_mb for r in successful_results]
        ax2.hist(memory_usage, bins=20, alpha=0.7, edgecolor='black')
        ax2.set_xlabel('Peak Memory Usage (MB)')
        ax2.set_ylabel('Frequency')
        ax2.set_title('Memory Usage Distribution')
        ax2.grid(True, alpha=0.3)
        
        # Headings detection accuracy
        headings_per_page = [r.headings_found / max(r.page_count, 1) for r in successful_results]
        ax3.hist(headings_per_page, bins=20, alpha=0.7, edgecolor='black')
        ax3.set_xlabel('Headings per Page')
        ax3.set_ylabel('Frequency')
        ax3.set_title('Heading Detection Rate')
        ax3.grid(True, alpha=0.3)
        
        # Confidence scores
        confidences = [r.avg_confidence for r in successful_results if r.avg_confidence > 0]
        ax4.hist(confidences, bins=20, alpha=0.7, edgecolor='black')
        ax4.set_xlabel('Average Confidence Score')
        ax4.set_ylabel('Frequency')
        ax4.set_title('Confidence Score Distribution')
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_path / "performance_charts.png", dpi=300, bbox_inches='tight')
        plt.close()
    
    def _generate_html_report(self, output_path: Path):
        """Generate HTML benchmark report."""
        successful_results = [r for r in self.results if r.success]
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>PDF Outline Extractor - Benchmark Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .metric {{ background-color: #e8f4f8; }}
        .good {{ color: green; font-weight: bold; }}
        .warning {{ color: orange; font-weight: bold; }}
        .error {{ color: red; font-weight: bold; }}
        .chart {{ text-align: center; margin: 20px 0; }}
    </style>
</head>
<body>
    <h1>PDF Outline Extractor - Benchmark Report</h1>
    <p>Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}</p>
    
    <h2>Summary Statistics</h2>
    <table>
        <tr><th>Metric</th><th>Value</th></tr>
        <tr><td>Total Files Processed</td><td>{len(self.results)}</td></tr>
        <tr><td>Successful Extractions</td><td class="good">{len(successful_results)}</td></tr>
        <tr><td>Failed Extractions</td><td class="{'error' if len(self.results) - len(successful_results) > 0 else 'good'}">{len(self.results) - len(successful_results)}</td></tr>
        <tr><td>Total Pages Processed</td><td>{sum(r.page_count for r in successful_results)}</td></tr>
        <tr><td>Total Processing Time</td><td>{sum(r.processing_time for r in successful_results):.2f}s</td></tr>
        <tr><td>Total Headings Found</td><td>{sum(r.headings_found for r in successful_results)}</td></tr>
    </table>
    
    <h2>Performance Metrics</h2>
    <table>
        <tr><th>Metric</th><th>Value</th><th>Target</th><th>Status</th></tr>
"""
        
        if successful_results:
            avg_time = sum(r.processing_time for r in successful_results) / len(successful_results)
            avg_pages_per_sec = sum(r.page_count / max(r.processing_time, 0.1) for r in successful_results) / len(successful_results)
            avg_memory = sum(r.memory_peak_mb for r in successful_results) / len(successful_results)
            
            target_compliance = len([r for r in successful_results if r.page_count <= 50 and r.processing_time <= 10.0])
            target_eligible = len([r for r in successful_results if r.page_count <= 50])
            
            html_content += f"""
        <tr><td>Average Processing Time</td><td>{avg_time:.2f}s</td><td>≤10s for 50 pages</td><td class="{'good' if avg_time <= 10 else 'warning'}">{'PASS' if avg_time <= 10 else 'REVIEW'}</td></tr>
        <tr><td>Average Pages/Second</td><td>{avg_pages_per_sec:.1f}</td><td>≥5 pages/sec</td><td class="{'good' if avg_pages_per_sec >= 5 else 'warning'}">{'PASS' if avg_pages_per_sec >= 5 else 'REVIEW'}</td></tr>
        <tr><td>Average Memory Usage</td><td>{avg_memory:.1f} MB</td><td>≤100 MB</td><td class="{'good' if avg_memory <= 100 else 'warning'}">{'PASS' if avg_memory <= 100 else 'REVIEW'}</td></tr>
        <tr><td>Performance Target Compliance</td><td>{target_compliance}/{target_eligible}</td><td>≥80%</td><td class="{'good' if target_compliance/max(target_eligible,1) >= 0.8 else 'warning'}">{'PASS' if target_compliance/max(target_eligible,1) >= 0.8 else 'REVIEW'}</td></tr>
"""
        
        html_content += """
    </table>
    
    <div class="chart">
        <h2>Performance Visualization</h2>
        <img src="performance_charts.png" alt="Performance Charts" style="max-width: 100%;">
    </div>
    
    <h2>Detailed Results</h2>
    <table>
        <tr>
            <th>File</th>
            <th>Size (MB)</th>
            <th>Pages</th>
            <th>Time (s)</th>
            <th>Memory (MB)</th>
            <th>Headings</th>
            <th>Confidence</th>
            <th>Status</th>
        </tr>
"""
        
        for result in self.results:
            status_class = "good" if result.success else "error"
            status_text = "SUCCESS" if result.success else "FAILED"
            
            html_content += f"""
        <tr>
            <td>{result.filename}</td>
            <td>{result.file_size_mb:.2f}</td>
            <td>{result.page_count}</td>
            <td>{result.processing_time:.2f}</td>
            <td>{result.memory_peak_mb:.1f}</td>
            <td>{result.headings_found}</td>
            <td>{result.avg_confidence:.3f}</td>
            <td class="{status_class}">{status_text}</td>
        </tr>
"""
        
        html_content += """
    </table>
    
    <h2>Recommendations</h2>
    <ul>
"""
        
        # Add recommendations based on results
        if successful_results:
            avg_time = sum(r.processing_time for r in successful_results) / len(successful_results)
            if avg_time > 10:
                html_content += "<li>Consider optimizing processing pipeline - average time exceeds target</li>"
            
            avg_memory = sum(r.memory_peak_mb for r in successful_results) / len(successful_results)
            if avg_memory > 100:
                html_content += "<li>Memory usage is high - consider implementing memory optimization</li>"
            
            low_confidence_count = len([r for r in successful_results if r.avg_confidence < 0.7])
            if low_confidence_count > len(successful_results) * 0.3:
                html_content += "<li>Many documents have low confidence scores - consider tuning detection parameters</li>"
        
        html_content += """
    </ul>
</body>
</html>
"""
        
        with open(output_path / "benchmark_report.html", "w") as f:
            f.write(html_content)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="PDF Outline Extractor Benchmark Tool")
    parser.add_argument("--input", "-i", type=Path, default=Path("input"), 
                       help="Input directory containing PDF files")
    parser.add_argument("--output", "-o", type=Path, default=Path("benchmarks/results"),
                       help="Output directory for benchmark results")
    parser.add_argument("--document", "-d", type=Path,
                       help="Benchmark a single document")
    parser.add_argument("--config", "-c", type=Path,
                       help="Configuration file path")
    parser.add_argument("--iterations", "-n", type=int, default=1,
                       help="Number of iterations per document")
    
    args = parser.parse_args()
    
    # Load settings
    settings = Settings.load(args.config) if args.config else Settings()
    
    # Create benchmark instance
    benchmark = PDFBenchmark(settings)
    
    print("PDF Outline Extractor - Benchmark Tool")
    print("=" * 50)
    
    if args.document:
        # Benchmark single document
        if not args.document.exists():
            print(f"Error: Document not found: {args.document}")
            sys.exit(1)
        
        print(f"Benchmarking single document: {args.document}")
        
        # Run multiple iterations if requested
        for i in range(args.iterations):
            if args.iterations > 1:
                print(f"Iteration {i+1}/{args.iterations}")
            benchmark.benchmark_file(args.document)
    
    else:
        # Benchmark directory
        if not args.input.exists():
            print(f"Error: Input directory not found: {args.input}")
            sys.exit(1)
        
        print(f"Benchmarking directory: {args.input}")
        benchmark.benchmark_directory(args.input)
    
    # Generate report
    if benchmark.results:
        benchmark.generate_report(args.output)
        print(f"\nBenchmark completed!")
        print(f"Results saved to: {args.output}")
        print(f"View HTML report: {args.output}/benchmark_report.html")
    else:
        print("No results to report")


if __name__ == "__main__":
    main()