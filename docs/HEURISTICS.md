# Heading Detection Heuristics

## Overview

The PDF Outline Extractor uses a sophisticated multi-heuristic approach to detect headings across diverse PDF layouts. This document explains the algorithms, scoring mechanisms, and tuning strategies.

## Core Detection Algorithm

### Scoring Framework
Each potential heading receives a confidence score (0-1) based on multiple weighted heuristics:

```
Final Score = Σ(Heuristic Score × Weight)

Where weights sum to 1.0:
- Font Size: 30%
- Font Style: 20% 
- Position: 15%
- Numbering: 15%
- Keywords: 10%
- Length: 10%
```

### Minimum Thresholds
- **Minimum Confidence**: 0.5 (configurable)
- **Maximum Length**: 200 characters
- **Minimum Length**: 3 characters

## Individual Heuristics

### 1. Font Size Analysis (30% Weight)

**Principle**: Headings typically use larger fonts than body text.

**Algorithm**:
```python
def calculate_font_size_score(block, document):
    size_ratio = block.font_size / document.avg_font_size
    
    if size_ratio >= 2.0:    return 1.0  # Very large
    elif size_ratio >= 1.5:  return 0.8  # Large (H1)
    elif size_ratio >= 1.3:  return 0.6  # Medium (H2)
    elif size_ratio >= 1.15: return 0.4  # Small (H3)
    else:                    return 0.1  # Too small
```

**Tuning Parameters**:
```python
HEADING_SIZE_MULTIPLIERS = {
    'h1': 1.5,   # 50% larger than average
    'h2': 1.3,   # 30% larger than average
    'h3': 1.15   # 15% larger than average
}
```

**Common Adjustments**:
- **Academic papers**: Lower thresholds (1.2, 1.1, 1.05)
- **Marketing materials**: Higher thresholds (1.8, 1.5, 1.3)
- **Technical manuals**: Standard thresholds work well

### 2. Font Style Analysis (20% Weight)

**Principle**: Headings often use bold, italic, or different font families.

**Scoring Factors**:
```python
def calculate_font_style_score(block, document):
    score = 0.0
    
    # Bold text (PyMuPDF flag 16)
    if block.font_info.flags & 16:
        score += 0.6
    
    # Different font family from body text
    if block.font_info.family != document.primary_font:
        score += 0.3
    
    # All caps (but not too long)
    if block.text.isupper() and len(block.text) < 50:
        score += 0.2
    
    return min(score, 1.0)
```

**Font Family Detection**:
- Identifies most common font as "body text"
- Scores deviations from primary font
- Handles font name variations and subsets

### 3. Position Analysis (15% Weight)

**Principle**: Headings are typically left-aligned with whitespace around them.

**Scoring Components**:
```python
def calculate_position_score(block, document):
    score = 0.0
    
    # Left alignment (within margin)
    if block.x < LEFT_MARGIN_THRESHOLD:  # Default: 100px
        score += 0.4
    
    # Top of page positioning
    if block.y < TOP_MARGIN_THRESHOLD:   # Default: 150px
        score += 0.3
    
    # Isolated text (whitespace around)
    if has_whitespace_around(block, document):
        score += 0.3
    
    return min(score, 1.0)
```

**Whitespace Detection**:
- Analyzes surrounding text blocks
- Considers vertical spacing between elements
- Accounts for different page layouts

### 4. Numbering Pattern Analysis (15% Weight)

**Principle**: Many headings follow numbering conventions.

**Supported Patterns**:
```python
NUMBERING_PATTERNS = [
    (r'^\d+\.\s+',        0.8),  # "1. Title"
    (r'^\d+\.\d+\s+',     0.7),  # "1.1 Title"  
    (r'^\d+\.\d+\.\d+\s+', 0.6), # "1.1.1 Title"
    (r'^[A-Z]\.\s+',      0.6),  # "A. Title"
    (r'^[IVX]+\.\s+',     0.7),  # "I. Title" (Roman)
    (r'^\(\d+\)\s+',      0.5),  # "(1) Title"
    (r'^Chapter\s+\d+',   0.9),  # "Chapter 1"
    (r'^Section\s+\d+',   0.8),  # "Section 1"
]
```

**Pattern Matching**:
- Uses regex for flexible matching
- Scores based on pattern reliability
- Handles variations in spacing and formatting

### 5. Keyword Analysis (10% Weight)

**Principle**: Certain words commonly appear in headings.

**Keyword Categories**:
```python
HEADING_KEYWORDS = {
    # High confidence keywords
    'abstract': 0.4,
    'introduction': 0.3,
    'conclusion': 0.3,
    'references': 0.4,
    'appendix': 0.4,
    'chapter': 0.4,
    
    # Medium confidence keywords  
    'summary': 0.3,
    'overview': 0.3,
    'methodology': 0.3,
    'results': 0.3,
    'discussion': 0.3,
    
    # Lower confidence keywords
    'background': 0.2,
    'section': 0.2,
}
```

**Matching Strategy**:
- Case-insensitive substring matching
- Cumulative scoring for multiple keywords
- Domain-specific keyword sets possible

### 6. Length Analysis (10% Weight)

**Principle**: Headings have characteristic length distributions.

**Length Scoring**:
```python
def calculate_length_score(block):
    length = len(block.text.strip())
    
    if length <= 10:     return 0.3  # Very short
    elif length <= 30:   return 1.0  # Ideal length
    elif length <= 60:   return 0.7  # Acceptable
    elif length <= 100:  return 0.4  # Long but possible
    else:                return 0.1  # Too long
```

## Level Classification (H1, H2, H3)

### Font Size Hierarchy
After scoring, headings are classified into levels based on font size:

```python
def classify_heading_levels(scored_candidates, document):
    # Group by font size
    size_groups = group_by_font_size(scored_candidates)
    
    # Assign levels by size (largest = H1)
    sorted_sizes = sorted(size_groups.keys(), reverse=True)
    
    for i, font_size in enumerate(sorted_sizes[:3]):
        level = i + 1  # H1, H2, H3
        for block, confidence in size_groups[font_size]:
            create_heading(block, level, confidence)
```

### Hierarchy Validation
The system validates and corrects heading hierarchy:

```python
def validate_hierarchy(headings):
    validated = []
    level_stack = []
    
    for heading in headings:
        # Ensure logical progression (no orphaned H3s)
        appropriate_level = determine_appropriate_level(
            heading, level_stack, validated
        )
        
        if appropriate_level != heading.level:
            # Adjust level and reduce confidence slightly
            heading.level = appropriate_level
            heading.confidence *= 0.9
        
        validated.append(heading)
    
    return validated
```

## Adaptive Mechanisms

### Document-Specific Adaptation

**Font Size Normalization**:
- Calculates document-wide font statistics
- Adapts thresholds to document characteristics
- Handles documents with unusual base font sizes

**Layout Detection**:
- Identifies single vs. multi-column layouts
- Adjusts position scoring accordingly
- Handles academic vs. business document styles

### Quality Feedback Loop

**Confidence Adjustment**:
```python
def adjust_final_confidence(headings, document):
    for heading in headings:
        # Boost for clear numbering
        if has_clear_numbering(heading.text):
            heading.confidence = min(heading.confidence + 0.1, 1.0)
        
        # Penalize very long headings
        if len(heading.text) > 80:
            heading.confidence *= 0.8
        
        # Boost for consistent font usage
        if is_consistent_with_level(heading, headings):
            heading.confidence *= 1.1
```

## Tuning Strategies

### For Different Document Types

**Academic Papers**:
```python
# Lower font size thresholds
HEADING_SIZE_MULTIPLIERS = {'h1': 1.3, 'h2': 1.2, 'h3': 1.1}

# Increase keyword weight
KEYWORD_WEIGHT = 0.15  # Instead of 0.10

# Academic-specific keywords
KEYWORDS.update({
    'methodology': 0.4,
    'literature review': 0.4,
    'experimental setup': 0.3
})
```

**Business Reports**:
```python
# Higher font size thresholds
HEADING_SIZE_MULTIPLIERS = {'h1': 1.6, 'h2': 1.4, 'h3': 1.2}

# Increase numbering weight
NUMBERING_WEIGHT = 0.20  # Instead of 0.15

# Business-specific patterns
NUMBERING_PATTERNS.append((r'^Executive Summary', 0.9))
```

**Technical Manuals**:
```python
# Standard thresholds work well
# Increase position weight for structured layouts
POSITION_WEIGHT = 0.20  # Instead of 0.15

# Technical keywords
KEYWORDS.update({
    'installation': 0.3,
    'configuration': 0.3,
    'troubleshooting': 0.3
})
```

### Performance vs. Accuracy Trade-offs

**High Performance Mode**:
```python
# Reduce detailed font analysis
ENABLE_DETAILED_FONT_ANALYSIS = False

# Increase minimum confidence to reduce false positives
MIN_HEADING_CONFIDENCE = 0.7

# Process fewer pages in detail
MAX_DETAILED_PAGES = 5
```

**High Accuracy Mode**:
```python
# Enable all analysis features
ENABLE_DETAILED_FONT_ANALYSIS = True
ENABLE_POSITION_ANALYSIS = True
ENABLE_CONTEXT_ANALYSIS = True

# Lower confidence threshold to catch more headings
MIN_HEADING_CONFIDENCE = 0.3

# More sophisticated validation
STRICT_HIERARCHY_VALIDATION = True
```

## Debugging Heuristics

### Analyzing Detection Issues

**Font Size Problems**:
```python
# Debug font size distribution
def debug_font_sizes(document):
    sizes = [block.font_info.size for block in document.text_blocks]
    print(f"Font sizes: min={min(sizes)}, max={max(sizes)}, avg={np.mean(sizes)}")
    print(f"Size distribution: {Counter(sizes).most_common(10)}")
```

**Position Analysis**:
```python
# Debug text positioning
def debug_positions(document):
    for block in document.text_blocks[:10]:  # First 10 blocks
        print(f"Text: '{block.text[:30]}...' Position: ({block.x}, {block.y})")
```

**Heuristic Scoring**:
```python
# Debug individual heuristic scores
def debug_scoring(candidate, document):
    scores = {
        'font_size': calculate_font_size_score(candidate, document),
        'font_style': calculate_font_style_score(candidate, document),
        'position': calculate_position_score(candidate, document),
        'numbering': calculate_numbering_score(candidate),
        'keywords': calculate_keyword_score(candidate),
        'length': calculate_length_score(candidate)
    }
    
    print(f"Text: '{candidate.text}'")
    for heuristic, score in scores.items():
        print(f"  {heuristic}: {score:.3f}")
```

## Future Enhancements

### Machine Learning Integration
- Train models on labeled heading data
- Use ML confidence scores as additional heuristic
- Adapt to specific document domains automatically

### Advanced Layout Analysis
- Column detection and handling
- Table of contents extraction
- Cross-reference validation

### Context-Aware Detection
- Analyze heading relationships
- Use document structure patterns
- Improve hierarchy validation

The heuristic system is designed to be extensible and tunable. By understanding these mechanisms, you can adapt the system to work effectively with your specific document types and requirements.