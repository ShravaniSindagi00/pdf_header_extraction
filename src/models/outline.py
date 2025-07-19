"""
Outline data models for representing hierarchical document structure.

This module defines data structures for headings and outline hierarchies
extracted from PDF documents.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from .document import FontInfo


@dataclass
class Heading:
    """
    Represents a detected heading with metadata and confidence information.
    """
    text: str
    level: int  # 1=H1, 2=H2, 3=H3
    page: int
    confidence: float
    font_info: FontInfo
    position: Tuple[float, float]  # (x, y) coordinates
    
    # Optional metadata
    numbering: Optional[str] = None  # e.g., "1.1", "A.", "Chapter 1"
    parent_heading: Optional['Heading'] = None
    children: List['Heading'] = field(default_factory=list)
    
    def __post_init__(self):
        """Post-initialization processing."""
        # Clean up text
        self.text = self.text.strip()
        
        # Ensure level is valid
        if self.level < 1:
            self.level = 1
        elif self.level > 3:
            self.level = 3
        
        # Ensure confidence is in valid range
        if self.confidence < 0:
            self.confidence = 0.0
        elif self.confidence > 1:
            self.confidence = 1.0
    
    @property
    def is_h1(self) -> bool:
        """Check if this is an H1 heading."""
        return self.level == 1
    
    @property
    def is_h2(self) -> bool:
        """Check if this is an H2 heading."""
        return self.level == 2
    
    @property
    def is_h3(self) -> bool:
        """Check if this is an H3 heading."""
        return self.level == 3
    
    @property
    def has_numbering(self) -> bool:
        """Check if heading has numbering pattern."""
        return self.numbering is not None
    
    @property
    def has_children(self) -> bool:
        """Check if heading has child headings."""
        return len(self.children) > 0
    
    @property
    def depth(self) -> int:
        """Get the depth of this heading in the hierarchy."""
        depth = 0
        current = self.parent_heading
        while current is not None:
            depth += 1
            current = current.parent_heading
        return depth
    
    def add_child(self, child: 'Heading') -> None:
        """
        Add a child heading.
        
        Args:
            child: Child heading to add
        """
        child.parent_heading = self
        self.children.append(child)
    
    def remove_child(self, child: 'Heading') -> None:
        """
        Remove a child heading.
        
        Args:
            child: Child heading to remove
        """
        if child in self.children:
            child.parent_heading = None
            self.children.remove(child)
    
    def get_all_descendants(self) -> List['Heading']:
        """
        Get all descendant headings (children, grandchildren, etc.).
        
        Returns:
            List of all descendant headings
        """
        descendants = []
        for child in self.children:
            descendants.append(child)
            descendants.extend(child.get_all_descendants())
        return descendants
    
    def get_path(self) -> List['Heading']:
        """
        Get the path from root to this heading.
        
        Returns:
            List of headings from root to this heading
        """
        path = []
        current = self
        while current is not None:
            path.insert(0, current)
            current = current.parent_heading
        return path
    
    def get_path_text(self, separator: str = " > ") -> str:
        """
        Get the text path from root to this heading.
        
        Args:
            separator: Separator between heading texts
            
        Returns:
            String representation of the path
        """
        path = self.get_path()
        return separator.join(heading.text for heading in path)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert heading to dictionary representation."""
        return {
            'text': self.text,
            'level': self.level,
            'page': self.page,
            'confidence': self.confidence,
            'font_info': self.font_info.to_dict(),
            'position': {
                'x': self.position[0],
                'y': self.position[1]
            },
            'numbering': self.numbering,
            'has_children': self.has_children,
            'child_count': len(self.children)
        }
    
    def __str__(self) -> str:
        """String representation of the heading."""
        level_prefix = "H" + str(self.level)
        confidence_str = f"{self.confidence:.2f}"
        return f"{level_prefix}: {self.text} (page {self.page}, confidence {confidence_str})"
    
    def __repr__(self) -> str:
        """Detailed string representation."""
        return (f"Heading(text='{self.text[:30]}...', level={self.level}, "
                f"page={self.page}, confidence={self.confidence:.2f})")


@dataclass
class Outline:
    """
    Represents the complete outline structure of a document.
    """
    headings: List[Heading]
    hierarchy: Dict[str, Any] = field(default_factory=dict)
    
    # Quality metrics
    average_confidence: float = 0.0
    quality_score: float = 0.0
    
    # Statistics
    total_headings: int = 0
    h1_count: int = 0
    h2_count: int = 0
    h3_count: int = 0
    
    def __post_init__(self):
        """Post-initialization processing."""
        self._calculate_statistics()
    
    def _calculate_statistics(self) -> None:
        """Calculate outline statistics."""
        self.total_headings = len(self.headings)
        
        if self.headings:
            # Count by level
            self.h1_count = len([h for h in self.headings if h.level == 1])
            self.h2_count = len([h for h in self.headings if h.level == 2])
            self.h3_count = len([h for h in self.headings if h.level == 3])
            
            # Calculate average confidence
            total_confidence = sum(h.confidence for h in self.headings)
            self.average_confidence = total_confidence / len(self.headings)
    
    @property
    def is_empty(self) -> bool:
        """Check if outline is empty."""
        return len(self.headings) == 0
    
    @property
    def has_h1_headings(self) -> bool:
        """Check if outline has H1 headings."""
        return self.h1_count > 0
    
    @property
    def has_hierarchy(self) -> bool:
        """Check if outline has hierarchical structure."""
        return len(set(h.level for h in self.headings)) > 1
    
    @property
    def max_depth(self) -> int:
        """Get maximum depth of the outline."""
        if not self.headings:
            return 0
        return max(h.level for h in self.headings)
    
    def get_headings_by_level(self, level: int) -> List[Heading]:
        """
        Get all headings of a specific level.
        
        Args:
            level: Heading level (1, 2, or 3)
            
        Returns:
            List of headings at the specified level
        """
        return [h for h in self.headings if h.level == level]
    
    def get_headings_on_page(self, page: int) -> List[Heading]:
        """
        Get all headings on a specific page.
        
        Args:
            page: Page number
            
        Returns:
            List of headings on the specified page
        """
        return [h for h in self.headings if h.page == page]
    
    def get_page_range(self) -> Tuple[int, int]:
        """
        Get the range of pages covered by headings.
        
        Returns:
            Tuple of (min_page, max_page)
        """
        if not self.headings:
            return (0, 0)
        
        pages = [h.page for h in self.headings]
        return (min(pages), max(pages))
    
    def get_high_confidence_headings(self, threshold: float = 0.8) -> List[Heading]:
        """
        Get headings with high confidence scores.
        
        Args:
            threshold: Minimum confidence threshold
            
        Returns:
            List of high-confidence headings
        """
        return [h for h in self.headings if h.confidence >= threshold]
    
    def get_low_confidence_headings(self, threshold: float = 0.5) -> List[Heading]:
        """
        Get headings with low confidence scores.
        
        Args:
            threshold: Maximum confidence threshold
            
        Returns:
            List of low-confidence headings
        """
        return [h for h in self.headings if h.confidence < threshold]
    
    def build_tree_structure(self) -> List[Heading]:
        """
        Build a tree structure from flat heading list.
        
        Returns:
            List of root headings with children populated
        """
        if not self.headings:
            return []
        
        # Create a copy of headings to avoid modifying original
        headings = [h for h in self.headings]
        
        # Clear existing parent-child relationships
        for heading in headings:
            heading.parent_heading = None
            heading.children = []
        
        # Build tree structure
        root_headings = []
        stack = []  # Stack of potential parents
        
        for heading in headings:
            # Find appropriate parent
            while stack and stack[-1].level >= heading.level:
                stack.pop()
            
            if stack:
                # Add as child to the last heading in stack
                parent = stack[-1]
                parent.add_child(heading)
            else:
                # This is a root heading
                root_headings.append(heading)
            
            # Add to stack as potential parent for next headings
            stack.append(heading)
        
        return root_headings
    
    def get_table_of_contents(self, max_level: int = 3, include_page_numbers: bool = True) -> List[str]:
        """
        Generate a table of contents from the outline.
        
        Args:
            max_level: Maximum heading level to include
            include_page_numbers: Whether to include page numbers
            
        Returns:
            List of formatted TOC entries
        """
        toc_entries = []
        
        for heading in self.headings:
            if heading.level > max_level:
                continue
            
            # Create indentation based on level
            indent = "  " * (heading.level - 1)
            
            # Format entry
            if include_page_numbers:
                entry = f"{indent}{heading.text} ... {heading.page}"
            else:
                entry = f"{indent}{heading.text}"
            
            toc_entries.append(entry)
        
        return toc_entries
    
    def validate_structure(self) -> List[str]:
        """
        Validate the outline structure and return any issues found.
        
        Returns:
            List of validation issues (empty if no issues)
        """
        issues = []
        
        if self.is_empty:
            issues.append("Outline is empty")
            return issues
        
        # Check for H1 headings
        if not self.has_h1_headings:
            issues.append("No H1 headings found")
        
        # Check hierarchy consistency
        prev_level = 0
        for i, heading in enumerate(self.headings):
            if heading.level > prev_level + 1:
                issues.append(f"Heading level jump at position {i}: {heading.text[:50]}")
            prev_level = heading.level
        
        # Check for very low confidence headings
        low_confidence = self.get_low_confidence_headings(0.3)
        if len(low_confidence) > len(self.headings) * 0.5:
            issues.append("More than 50% of headings have low confidence")
        
        # Check for reasonable heading distribution
        if self.total_headings > 0:
            min_page, max_page = self.get_page_range()
            page_span = max_page - min_page + 1
            if page_span > 0:
                headings_per_page = self.total_headings / page_span
                if headings_per_page > 10:
                    issues.append("Too many headings per page (possible over-detection)")
                elif headings_per_page < 0.1:
                    issues.append("Too few headings per page (possible under-detection)")
        
        return issues
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert outline to dictionary representation."""
        return {
            'statistics': {
                'total_headings': self.total_headings,
                'h1_count': self.h1_count,
                'h2_count': self.h2_count,
                'h3_count': self.h3_count,
                'average_confidence': self.average_confidence,
                'quality_score': self.quality_score
            },
            'page_range': self.get_page_range(),
            'headings': [heading.to_dict() for heading in self.headings],
            'hierarchy': self.hierarchy,
            'validation_issues': self.validate_structure()
        }
    
    def __str__(self) -> str:
        """String representation of the outline."""
        return (f"Outline(headings={self.total_headings}, "
                f"H1={self.h1_count}, H2={self.h2_count}, H3={self.h3_count}, "
                f"avg_confidence={self.average_confidence:.2f})")
    
    def __repr__(self) -> str:
        """Detailed string representation."""
        return self.__str__()