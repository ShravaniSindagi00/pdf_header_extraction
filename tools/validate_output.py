#!/usr/bin/env python3
"""
Output Validation Tool - Validate and analyze extracted PDF outlines.

This tool validates the structure and quality of generated outline JSON files,
providing detailed analysis and suggestions for improvement.
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import jsonschema


@dataclass
class ValidationResult:
    """Results from outline validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    quality_score: float
    suggestions: List[str]
    statistics: Dict[str, Any]


class OutlineValidator:
    """Validator for PDF outline JSON files."""
    
    def __init__(self):
        self.schema = self._get_outline_schema()
    
    def _get_outline_schema(self) -> Dict[str, Any]:
        """Get JSON schema for outline validation."""
        return {
            "type": "object",
            "required": ["document", "outline", "statistics"],
            "properties": {
                "document": {
                    "type": "object",
                    "required": ["filename", "pages", "processed_at", "processing_time"],
                    "properties": {
                        "filename": {"type": "string"},
                        "pages": {"type": "integer", "minimum": 1},
                        "processed_at": {"type": "string"},
                        "processing_time": {"type": "number", "minimum": 0}
                    }
                },
                "outline": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["level", "title", "page", "confidence"],
                        "properties": {
                            "level": {"type": "integer", "minimum": 1, "maximum": 3},
                            "title": {"type": "string", "minLength": 1},
                            "page": {"type": "integer", "minimum": 1},
                            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                            "font_info": {
                                "type": "object",
                                "properties": {
                                    "size": {"type": "number", "minimum": 0},
                                    "family": {"type": "string"},
                                    "color": {"type": "string"}
                                }
                            }
                        }
                    }
                },
                "statistics": {
                    "type": "object",
                    "required": ["total_headings", "h1_count", "h2_count", "h3_count"],
                    "properties": {
                        "total_headings": {"type": "integer", "minimum": 0},
                        "h1_count": {"type": "integer", "minimum": 0},
                        "h2_count": {"type": "integer", "minimum": 0},
                        "h3_count": {"type": "integer", "minimum": 0},
                        "average_confidence": {"type": "number", "minimum": 0, "maximum": 1}
                    }
                }
            }
        }
    
    def validate_file(self, json_path: Path) -> ValidationResult:
        """Validate a single outline JSON file."""
        errors = []
        warnings = []
        suggestions = []
        
        try:
            # Load JSON file
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Schema validation
            try:
                jsonschema.validate(data, self.schema)
            except jsonschema.ValidationError as e:
                errors.append(f"Schema validation failed: {e.message}")
            
            # Content validation
            content_errors, content_warnings, content_suggestions = self._validate_content(data)
            errors.extend(content_errors)
            warnings.extend(content_warnings)
            suggestions.extend(content_suggestions)
            
            # Calculate quality score
            quality_score = self._calculate_quality_score(data)
            
            # Generate statistics
            statistics = self._generate_statistics(data)
            
            return ValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                quality_score=quality_score,
                suggestions=suggestions,
                statistics=statistics
            )
            
        except json.JSONDecodeError as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Invalid JSON format: {e}"],
                warnings=[],
                quality_score=0.0,
                suggestions=["Fix JSON syntax errors"],
                statistics={}
            )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Validation error: {e}"],
                warnings=[],
                quality_score=0.0,
                suggestions=[],
                statistics={}
            )
    
    def _validate_content(self, data: Dict[str, Any]) -> Tuple[List[str], List[str], List[str]]:
        """Validate content beyond schema requirements."""
        errors = []
        warnings = []
        suggestions = []
        
        # Document validation
        document = data.get("document", {})
        outline = data.get("outline", [])
        statistics = data.get("statistics", {})
        
        # Check processing time
        processing_time = document.get("processing_time", 0)
        pages = document.get("pages", 0)
        if pages > 0:
            time_per_page = processing_time / pages
            if time_per_page > 0.5:  # More than 0.5 seconds per page
                warnings.append(f"Slow processing: {time_per_page:.2f}s per page")
                if time_per_page > 1.0:
                    suggestions.append("Consider optimizing processing pipeline for better performance")
        
        # Outline validation
        if not outline:
            warnings.append("No headings detected in document")
            suggestions.append("Check if document contains headings or adjust detection parameters")
        else:
            # Check heading hierarchy
            hierarchy_errors = self._validate_hierarchy(outline)
            errors.extend(hierarchy_errors)
            
            # Check confidence scores
            low_confidence_count = len([h for h in outline if h.get("confidence", 0) < 0.5])
            if low_confidence_count > len(outline) * 0.5:
                warnings.append(f"Many headings have low confidence ({low_confidence_count}/{len(outline)})")
                suggestions.append("Consider adjusting detection thresholds or reviewing document quality")
            
            # Check page distribution
            pages_with_headings = len(set(h.get("page", 0) for h in outline))
            if pages > 0:
                coverage = pages_with_headings / pages
                if coverage < 0.1:
                    warnings.append(f"Low page coverage: headings found on only {coverage:.1%} of pages")
                    suggestions.append("Review heading detection parameters or document structure")
        
        # Statistics validation
        total_headings = statistics.get("total_headings", 0)
        if total_headings != len(outline):
            errors.append(f"Statistics mismatch: total_headings ({total_headings}) != outline length ({len(outline)})")
        
        # Check heading level distribution
        h1_count = statistics.get("h1_count", 0)
        h2_count = statistics.get("h2_count", 0)
        h3_count = statistics.get("h3_count", 0)
        
        if h1_count == 0 and total_headings > 0:
            warnings.append("No H1 headings found - document structure may be unclear")
            suggestions.append("Review font size thresholds or heading detection logic")
        
        if h2_count > h1_count * 10:
            warnings.append("Very high H2 to H1 ratio - possible over-detection")
            suggestions.append("Consider increasing confidence thresholds for H2 headings")
        
        return errors, warnings, suggestions
    
    def _validate_hierarchy(self, outline: List[Dict[str, Any]]) -> List[str]:
        """Validate heading hierarchy structure."""
        errors = []
        
        if not outline:
            return errors
        
        prev_level = 0
        h1_seen = False
        h2_seen = False
        
        for i, heading in enumerate(outline):
            level = heading.get("level", 0)
            
            # Track seen levels
            if level == 1:
                h1_seen = True
            elif level == 2:
                h2_seen = True
            
            # Check for level jumps
            if level > prev_level + 1:
                errors.append(f"Heading {i+1}: Level jump from {prev_level} to {level} - '{heading.get('title', '')[:50]}'")
            
            # Check for orphaned headings
            if level == 2 and not h1_seen:
                errors.append(f"Heading {i+1}: H2 without preceding H1 - '{heading.get('title', '')[:50]}'")
            elif level == 3 and not h2_seen:
                errors.append(f"Heading {i+1}: H3 without preceding H2 - '{heading.get('title', '')[:50]}'")
            
            prev_level = level
        
        return errors
    
    def _calculate_quality_score(self, data: Dict[str, Any]) -> float:
        """Calculate overall quality score for the outline."""
        score = 0.0
        max_score = 100.0
        
        outline = data.get("outline", [])
        statistics = data.get("statistics", {})
        document = data.get("document", {})
        
        if not outline:
            return 0.0
        
        # Confidence score (30 points)
        avg_confidence = statistics.get("average_confidence", 0)
        score += avg_confidence * 30
        
        # Hierarchy quality (25 points)
        hierarchy_errors = self._validate_hierarchy(outline)
        hierarchy_score = max(0, 25 - len(hierarchy_errors) * 5)
        score += hierarchy_score
        
        # Coverage (20 points)
        pages = document.get("pages", 1)
        pages_with_headings = len(set(h.get("page", 0) for h in outline))
        coverage = pages_with_headings / pages
        score += coverage * 20
        
        # Distribution (15 points)
        h1_count = statistics.get("h1_count", 0)
        h2_count = statistics.get("h2_count", 0)
        h3_count = statistics.get("h3_count", 0)
        
        distribution_score = 0
        if h1_count > 0:
            distribution_score += 5  # Has H1s
        if h2_count > 0:
            distribution_score += 5  # Has H2s
        if h1_count > 0 and h2_count / h1_count <= 5:  # Reasonable H2/H1 ratio
            distribution_score += 5
        
        score += distribution_score
        
        # Performance (10 points)
        processing_time = document.get("processing_time", float('inf'))
        if processing_time <= 10:
            score += 10
        elif processing_time <= 20:
            score += 5
        
        return min(score / max_score, 1.0)
    
    def _generate_statistics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate detailed statistics about the outline."""
        outline = data.get("outline", [])
        document = data.get("document", {})
        
        if not outline:
            return {"empty_outline": True}
        
        # Basic counts
        levels = [h.get("level", 0) for h in outline]
        confidences = [h.get("confidence", 0) for h in outline]
        pages = [h.get("page", 0) for h in outline]
        
        # Text analysis
        titles = [h.get("title", "") for h in outline]
        title_lengths = [len(title) for title in titles]
        
        # Font analysis
        font_sizes = []
        font_families = []
        for h in outline:
            font_info = h.get("font_info", {})
            if "size" in font_info:
                font_sizes.append(font_info["size"])
            if "family" in font_info:
                font_families.append(font_info["family"])
        
        stats = {
            "outline_length": len(outline),
            "level_distribution": {
                "h1": levels.count(1),
                "h2": levels.count(2),
                "h3": levels.count(3)
            },
            "confidence_stats": {
                "min": min(confidences) if confidences else 0,
                "max": max(confidences) if confidences else 0,
                "avg": sum(confidences) / len(confidences) if confidences else 0,
                "low_confidence_count": len([c for c in confidences if c < 0.5])
            },
            "page_distribution": {
                "first_heading_page": min(pages) if pages else 0,
                "last_heading_page": max(pages) if pages else 0,
                "pages_with_headings": len(set(pages)),
                "total_pages": document.get("pages", 0)
            },
            "title_analysis": {
                "avg_length": sum(title_lengths) / len(title_lengths) if title_lengths else 0,
                "min_length": min(title_lengths) if title_lengths else 0,
                "max_length": max(title_lengths) if title_lengths else 0,
                "long_titles_count": len([l for l in title_lengths if l > 100])
            }
        }
        
        if font_sizes:
            stats["font_analysis"] = {
                "size_range": f"{min(font_sizes):.1f} - {max(font_sizes):.1f}",
                "avg_size": sum(font_sizes) / len(font_sizes),
                "unique_sizes": len(set(font_sizes))
            }
        
        if font_families:
            from collections import Counter
            family_counts = Counter(font_families)
            stats["font_analysis"]["families"] = dict(family_counts.most_common(5))
        
        return stats
    
    def print_validation_report(self, result: ValidationResult, json_path: Path):
        """Print a detailed validation report."""
        print(f"\n{'='*60}")
        print(f"VALIDATION REPORT: {json_path.name}")
        print(f"{'='*60}")
        
        # Overall status
        status = "✅ VALID" if result.is_valid else "❌ INVALID"
        print(f"Status: {status}")
        print(f"Quality Score: {result.quality_score:.1%}")
        
        # Errors
        if result.errors:
            print(f"\n🚨 ERRORS ({len(result.errors)}):")
            for i, error in enumerate(result.errors, 1):
                print(f"  {i}. {error}")
        
        # Warnings
        if result.warnings:
            print(f"\n⚠️  WARNINGS ({len(result.warnings)}):")
            for i, warning in enumerate(result.warnings, 1):
                print(f"  {i}. {warning}")
        
        # Suggestions
        if result.suggestions:
            print(f"\n💡 SUGGESTIONS ({len(result.suggestions)}):")
            for i, suggestion in enumerate(result.suggestions, 1):
                print(f"  {i}. {suggestion}")
        
        # Statistics
        if result.statistics and not result.statistics.get("empty_outline"):
            print(f"\n📊 STATISTICS:")
            stats = result.statistics
            
            print(f"  Outline Length: {stats.get('outline_length', 0)}")
            
            level_dist = stats.get('level_distribution', {})
            print(f"  Level Distribution: H1={level_dist.get('h1', 0)}, H2={level_dist.get('h2', 0)}, H3={level_dist.get('h3', 0)}")
            
            conf_stats = stats.get('confidence_stats', {})
            print(f"  Confidence: avg={conf_stats.get('avg', 0):.3f}, range={conf_stats.get('min', 0):.3f}-{conf_stats.get('max', 0):.3f}")
            
            page_dist = stats.get('page_distribution', {})
            total_pages = page_dist.get('total_pages', 0)
            pages_with_headings = page_dist.get('pages_with_headings', 0)
            if total_pages > 0:
                coverage = pages_with_headings / total_pages
                print(f"  Page Coverage: {pages_with_headings}/{total_pages} ({coverage:.1%})")
            
            title_analysis = stats.get('title_analysis', {})
            print(f"  Title Length: avg={title_analysis.get('avg_length', 0):.1f}, range={title_analysis.get('min_length', 0)}-{title_analysis.get('max_length', 0)}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="PDF Outline Validation Tool")
    parser.add_argument("files", nargs="+", type=Path, help="JSON outline files to validate")
    parser.add_argument("--quiet", "-q", action="store_true", help="Only show errors and warnings")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument("--output", "-o", type=Path, help="Save validation report to file")
    
    args = parser.parse_args()
    
    validator = OutlineValidator()
    all_results = {}
    
    for json_path in args.files:
        if not json_path.exists():
            print(f"Error: File not found: {json_path}")
            continue
        
        if not json_path.suffix.lower() == '.json':
            print(f"Warning: Not a JSON file: {json_path}")
            continue
        
        result = validator.validate_file(json_path)
        all_results[str(json_path)] = result
        
        if args.json:
            # JSON output
            json_result = {
                "file": str(json_path),
                "valid": result.is_valid,
                "quality_score": result.quality_score,
                "errors": result.errors,
                "warnings": result.warnings,
                "suggestions": result.suggestions,
                "statistics": result.statistics
            }
            print(json.dumps(json_result, indent=2))
        elif not args.quiet:
            # Detailed report
            validator.print_validation_report(result, json_path)
        else:
            # Quiet mode - only errors and warnings
            if result.errors or result.warnings:
                print(f"\n{json_path.name}:")
                for error in result.errors:
                    print(f"  ERROR: {error}")
                for warning in result.warnings:
                    print(f"  WARNING: {warning}")
    
    # Summary
    if len(all_results) > 1 and not args.json:
        print(f"\n{'='*60}")
        print("SUMMARY")
        print(f"{'='*60}")
        
        valid_count = sum(1 for r in all_results.values() if r.is_valid)
        total_count = len(all_results)
        avg_quality = sum(r.quality_score for r in all_results.values()) / total_count
        
        print(f"Files Processed: {total_count}")
        print(f"Valid Files: {valid_count}/{total_count} ({valid_count/total_count:.1%})")
        print(f"Average Quality Score: {avg_quality:.1%}")
        
        # Top issues
        all_errors = []
        all_warnings = []
        for result in all_results.values():
            all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)
        
        if all_errors:
            print(f"\nMost Common Errors:")
            from collections import Counter
            error_counts = Counter(all_errors)
            for error, count in error_counts.most_common(3):
                print(f"  {count}x: {error}")
        
        if all_warnings:
            print(f"\nMost Common Warnings:")
            from collections import Counter
            warning_counts = Counter(all_warnings)
            for warning, count in warning_counts.most_common(3):
                print(f"  {count}x: {warning}")
    
    # Save report if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump({
                "validation_results": {
                    str(path): {
                        "valid": result.is_valid,
                        "quality_score": result.quality_score,
                        "errors": result.errors,
                        "warnings": result.warnings,
                        "suggestions": result.suggestions,
                        "statistics": result.statistics
                    }
                    for path, result in all_results.items()
                },
                "summary": {
                    "total_files": len(all_results),
                    "valid_files": sum(1 for r in all_results.values() if r.is_valid),
                    "average_quality": sum(r.quality_score for r in all_results.values()) / len(all_results) if all_results else 0
                }
            }, f, indent=2)
        print(f"\nValidation report saved to: {args.output}")


if __name__ == "__main__":
    main()