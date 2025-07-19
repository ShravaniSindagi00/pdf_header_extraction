"""
Outline Builder - Construct hierarchical outline structure from detected headings.

This module takes detected headings and builds a coherent outline structure,
handling edge cases and ensuring logical hierarchy.
"""

import logging
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

from models.document import Document
from models.outline import Outline, Heading
from config.settings import Settings

logger = logging.getLogger(__name__)


class OutlineBuilder:
    """
    Builds structured outlines from detected headings with hierarchy validation
    and quality assurance.
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
    
    def build_outline(self, headings: List[Heading]) -> Outline:
        """
        Build a structured outline from detected headings.
        
        Args:
            headings: List of detected headings
            
        Returns:
            Outline object with hierarchical structure
        """
        logger.info(f"Building outline from {len(headings)} headings")
        
        if not headings:
            return Outline(headings=[], hierarchy={})
        
        # Step 1: Sort headings by page and position
        sorted_headings = self._sort_headings(headings)
        
        # Step 2: Validate and fix hierarchy
        validated_headings = self._validate_hierarchy(sorted_headings)
        
        # Step 3: Build hierarchical structure
        hierarchy = self._build_hierarchy(validated_headings)
        
        # Step 4: Calculate quality metrics
        outline = Outline(headings=validated_headings, hierarchy=hierarchy)
        self._calculate_outline_metrics(outline)
        
        logger.info(f"Built outline with {len(validated_headings)} headings, "
                   f"avg confidence: {outline.average_confidence:.2f}")
        
        return outline
    
    def _sort_headings(self, headings: List[Heading]) -> List[Heading]:
        """Sort headings by page number and vertical position."""
        return sorted(headings, key=lambda h: (h.page, h.position[1]))
    
    def _validate_hierarchy(self, headings: List[Heading]) -> List[Heading]:
        """
        Validate and fix heading hierarchy to ensure logical structure.
        
        This method ensures:
        - No orphaned H3s without H2 parents
        - No orphaned H2s without H1 parents
        - Reasonable level progression
        """
        if not headings:
            return []
        
        validated = []
        level_stack = []  # Track current hierarchy levels
        
        for heading in headings:
            # Determine appropriate level based on context
            adjusted_level = self._determine_appropriate_level(
                heading, level_stack, validated
            )
            
            # Create new heading with adjusted level if necessary
            if adjusted_level != heading.level:
                logger.debug(f"Adjusting heading level from {heading.level} to {adjusted_level}: {heading.text[:50]}")
                heading = Heading(
                    text=heading.text,
                    level=adjusted_level,
                    page=heading.page,
                    confidence=heading.confidence * 0.9,  # Slight confidence penalty for adjustment
                    font_info=heading.font_info,
                    position=heading.position
                )
            
            # Update level stack
            self._update_level_stack(level_stack, adjusted_level)
            validated.append(heading)
        
        return validated
    
    def _determine_appropriate_level(self, heading: Heading, level_stack: List[int], 
                                   previous_headings: List[Heading]) -> int:
        """Determine the appropriate level for a heading based on context."""
        target_level = heading.level
        
        # If this is the first heading, it should be H1
        if not previous_headings:
            return 1
        
        # Check if we can use the target level
        if target_level == 1:
            return 1  # H1 is always allowed
        
        elif target_level == 2:
            # H2 requires at least one H1 before it
            if any(h.level == 1 for h in previous_headings):
                return 2
            else:
                return 1  # Promote to H1
        
        elif target_level == 3:
            # H3 requires H2 in the current section
            if level_stack and 2 in level_stack:
                return 3
            elif any(h.level <= 2 for h in previous_headings):
                return 2  # Demote to H2
            else:
                return 1  # Demote to H1
        
        # Default fallback
        return min(target_level, 3)
    
    def _update_level_stack(self, level_stack: List[int], new_level: int) -> None:
        """Update the level stack to track current hierarchy."""
        # Remove levels deeper than the new level
        level_stack[:] = [level for level in level_stack if level < new_level]
        
        # Add the new level
        if new_level not in level_stack:
            level_stack.append(new_level)
    
    def _build_hierarchy(self, headings: List[Heading]) -> Dict:
        """
        Build a hierarchical dictionary structure from headings.
        
        Returns:
            Nested dictionary representing the outline hierarchy
        """
        hierarchy = {}
        stack = [(hierarchy, 0)]  # (current_dict, level)
        
        for heading in headings:
            # Find the appropriate parent level
            while len(stack) > 1 and stack[-1][1] >= heading.level:
                stack.pop()
            
            current_dict = stack[-1][0]
            
            # Create entry for this heading
            heading_entry = {
                'text': heading.text,
                'page': heading.page,
                'confidence': heading.confidence,
                'children': {}
            }
            
            # Add to current level
            heading_key = f"{heading.level}_{len(current_dict)}"
            current_dict[heading_key] = heading_entry
            
            # Push this level onto the stack for potential children
            stack.append((heading_entry['children'], heading.level))
        
        return hierarchy
    
    def _calculate_outline_metrics(self, outline: Outline) -> None:
        """Calculate quality metrics for the outline."""
        if not outline.headings:
            outline.average_confidence = 0.0
            outline.quality_score = 0.0
            return
        
        # Calculate average confidence
        total_confidence = sum(h.confidence for h in outline.headings)
        outline.average_confidence = total_confidence / len(outline.headings)
        
        # Calculate quality score based on various factors
        quality_factors = []
        
        # Factor 1: Confidence score (40% weight)
        quality_factors.append(outline.average_confidence * 0.4)
        
        # Factor 2: Hierarchy balance (30% weight)
        hierarchy_score = self._calculate_hierarchy_balance(outline.headings)
        quality_factors.append(hierarchy_score * 0.3)
        
        # Factor 3: Coverage (20% weight) - how well distributed across pages
        coverage_score = self._calculate_page_coverage(outline.headings)
        quality_factors.append(coverage_score * 0.2)
        
        # Factor 4: Consistency (10% weight) - similar patterns
        consistency_score = self._calculate_consistency(outline.headings)
        quality_factors.append(consistency_score * 0.1)
        
        outline.quality_score = sum(quality_factors)
        
        logger.debug(f"Outline quality metrics - Confidence: {outline.average_confidence:.2f}, "
                    f"Quality: {outline.quality_score:.2f}")
    
    def _calculate_hierarchy_balance(self, headings: List[Heading]) -> float:
        """Calculate how well-balanced the heading hierarchy is."""
        if not headings:
            return 0.0
        
        # Count headings by level
        level_counts = defaultdict(int)
        for heading in headings:
            level_counts[heading.level] += 1
        
        # Ideal ratios: more H1s than H2s, more H2s than H3s
        h1_count = level_counts.get(1, 0)
        h2_count = level_counts.get(2, 0)
        h3_count = level_counts.get(3, 0)
        
        if h1_count == 0:
            return 0.3  # No H1s is problematic
        
        score = 0.5  # Base score
        
        # Bonus for having H1s
        score += 0.3
        
        # Check H2 to H1 ratio
        if h2_count > 0:
            h2_h1_ratio = h2_count / h1_count
            if 1 <= h2_h1_ratio <= 5:  # Reasonable ratio
                score += 0.1
        
        # Check H3 to H2 ratio
        if h3_count > 0 and h2_count > 0:
            h3_h2_ratio = h3_count / h2_count
            if 1 <= h3_h2_ratio <= 3:  # Reasonable ratio
                score += 0.1
        
        return min(score, 1.0)
    
    def _calculate_page_coverage(self, headings: List[Heading]) -> float:
        """Calculate how well headings are distributed across pages."""
        if not headings:
            return 0.0
        
        # Get page range
        pages = [h.page for h in headings]
        min_page, max_page = min(pages), max(pages)
        total_pages = max_page - min_page + 1
        
        if total_pages <= 1:
            return 0.5  # Single page document
        
        # Calculate distribution
        unique_pages = len(set(pages))
        coverage_ratio = unique_pages / total_pages
        
        # Score based on coverage
        if coverage_ratio >= 0.3:  # Good coverage
            return 1.0
        elif coverage_ratio >= 0.2:  # Decent coverage
            return 0.7
        elif coverage_ratio >= 0.1:  # Poor coverage
            return 0.4
        else:
            return 0.2  # Very poor coverage
    
    def _calculate_consistency(self, headings: List[Heading]) -> float:
        """Calculate consistency in heading patterns and formatting."""
        if len(headings) < 2:
            return 1.0
        
        score = 0.0
        
        # Check font consistency within levels
        level_fonts = defaultdict(list)
        for heading in headings:
            level_fonts[heading.level].append(heading.font_info.family)
        
        consistent_levels = 0
        total_levels = len(level_fonts)
        
        for level, fonts in level_fonts.items():
            if len(set(fonts)) == 1:  # All same font
                consistent_levels += 1
        
        if total_levels > 0:
            font_consistency = consistent_levels / total_levels
            score += font_consistency * 0.5
        
        # Check numbering pattern consistency
        numbered_headings = [h for h in headings if self._has_numbering(h.text)]
        if numbered_headings:
            numbering_consistency = len(numbered_headings) / len(headings)
            score += numbering_consistency * 0.3
        
        # Base consistency score
        score += 0.2
        
        return min(score, 1.0)
    
    def _has_numbering(self, text: str) -> bool:
        """Check if heading text has numbering pattern."""
        import re
        numbering_patterns = [
            r'^\d+\.',
            r'^\d+\.\d+',
            r'^[A-Z]\.',
            r'^[IVX]+\.',
            r'^\(\d+\)',
            r'^Chapter\s+\d+',
            r'^Section\s+\d+'
        ]
        
        for pattern in numbering_patterns:
            if re.match(pattern, text.strip()):
                return True
        return False
    
    def get_outline_summary(self, outline: Outline) -> Dict:
        """Generate a summary of the outline structure."""
        if not outline.headings:
            return {
                'total_headings': 0,
                'levels': {},
                'pages_covered': 0,
                'quality_score': 0.0
            }
        
        level_counts = defaultdict(int)
        pages = set()
        
        for heading in outline.headings:
            level_counts[f'h{heading.level}'] += 1
            pages.add(heading.page)
        
        return {
            'total_headings': len(outline.headings),
            'levels': dict(level_counts),
            'pages_covered': len(pages),
            'quality_score': outline.quality_score,
            'average_confidence': outline.average_confidence
        }