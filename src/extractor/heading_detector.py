"""
Heading Detector - Identify H1, H2, H3 headings using advanced heuristics.
"""
import re
import logging
from typing import List, Dict, Tuple
from collections import defaultdict
import numpy as np

from models.document import Document, TextBlock
from config.settings import Settings
from models.outline import Heading

logger = logging.getLogger(__name__)

class HeadingDetector:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._heading_keywords = self._load_heading_keywords()
        self._numbering_patterns = self._compile_numbering_patterns()

    def detect_headings(self, document: Document) -> List[Heading]:
        logger.info(f"Starting heading detection for {document.filename}")
        
        candidates = self._identify_heading_candidates(document)
        logger.debug(f"Found {len(candidates)} potential heading candidates")
        
        scored_candidates = self._score_candidates(candidates, document)
        
        headings = self._classify_heading_levels(scored_candidates)
        
        final_headings = self._post_process_headings(headings)
        
        logger.info(f"Detected {len(final_headings)} headings: "
                   f"H1={len([h for h in final_headings if h.level == 1])}, "
                   f"H2={len([h for h in final_headings if h.level == 2])}, "
                   f"H3={len([h for h in final_headings if h.level == 3])}")
        return final_headings

    def _identify_heading_candidates(self, document: Document) -> List[TextBlock]:
        """Filter out blocks that are clearly not headings."""
        candidates = []
        for block in document.text_blocks:
            text = block.text.strip()
            if not text or len(text) > self.settings.MAX_HEADING_LENGTH: continue
            if block.font_info.size < (document.avg_font_size or 12.0): continue
            if text.endswith(('.', '!', '?', ';', ':')) and len(text) > 20: continue
            candidates.append(block)
        return candidates

    def _score_candidates(self, candidates: List[TextBlock], document: Document) -> List[Tuple[TextBlock, float]]:
        """Score candidates based on a weighted combination of heuristics."""
        scored = []
        for block in candidates:
            weights = {"size": 0.5, "style": 0.3, "position": 0.1, "numbering": 0.1}
            score = (
                self._calculate_font_size_score(block, document) * weights["size"] +
                self._calculate_font_style_score(block, document) * weights["style"] +
                self._calculate_position_score(block, document) * weights["position"] +
                self._calculate_numbering_score(block) * weights["numbering"]
            )
            # Add a bonus for keywords
            if self._calculate_keyword_score(block) > 0:
                score = min(1.0, score + 0.1)

            if score >= self.settings.MIN_HEADING_CONFIDENCE:
                scored.append((block, score))
        return sorted(scored, key=lambda x: x[1], reverse=True)

    def _calculate_font_size_score(self, block, doc):
        ratio = block.font_info.size / (doc.avg_font_size or 12.0)
        if ratio > 1.6: return 1.0
        if ratio > 1.4: return 0.8
        if ratio > 1.2: return 0.6
        if ratio > 1.0: return 0.4
        return 0.1

    def _calculate_font_style_score(self, block, doc):
        score = 0
        font_name = block.font_info.family.lower()
        if any(w in font_name for w in ['bold', 'black', 'heavy']): score += 0.7
        if block.font_info.family != doc.primary_font: score += 0.3
        return min(score, 1.0)

    def _calculate_position_score(self, block, doc):
        page_width = doc.page_dimensions[block.page - 1][0]
        center_diff = abs((block.x + block.width / 2) - (page_width / 2))
        # Strong score for being centered
        if center_diff < (page_width * 0.1):
            return 1.0
        # Decent score for being left-aligned
        if block.x < (page_width * 0.1):
            return 0.5
        return 0

    def _calculate_numbering_score(self, block):
        return next((score for pattern, score in self._numbering_patterns if pattern.match(block.text.strip())), 0)

    def _calculate_keyword_score(self, block):
        return 1 if any(keyword in block.text.lower() for keyword in self._heading_keywords) else 0

    def _classify_heading_levels(self, scored_candidates):
        """Group by font size and assign H1, H2, H3."""
        if not scored_candidates: return []
        
        size_groups = defaultdict(list)
        for block, score in scored_candidates:
            # Round size to 1 decimal place to group similar fonts
            size_groups[round(block.font_info.size, 1)].append((block, score))
        
        # Sort font sizes from largest to smallest
        sorted_sizes = sorted(size_groups.keys(), reverse=True)
        
        headings = []
        # Assign H1, H2, H3 to the top 3 largest font groups
        for i, size in enumerate(sorted_sizes[:3]):
            level = i + 1
            for block, confidence in size_groups[size]:
                headings.append(Heading(
                    text=block.text, level=level, page=block.page,
                    confidence=confidence, font_info=block.font_info,
                    position=(block.x, block.y)
                ))
        return headings

    def _post_process_headings(self, headings):
        """Sort and remove duplicates."""
        if not headings: return []
        
        # Sort by page and vertical position
        headings.sort(key=lambda h: (h.page, h.position[1]))
        
        # Remove duplicates
        unique_headings, seen_texts = [], set()
        for h in headings:
            norm_text = h.text.lower().strip()
            if norm_text not in seen_texts:
                unique_headings.append(h)
                seen_texts.add(norm_text)
                
        return unique_headings

    def _load_heading_keywords(self):
        return {'introduction', 'conclusion', 'abstract', 'summary', 'background', 
                'methodology', 'results', 'discussion', 'references', 'appendix', 
                'chapter', 'section'}

    def _compile_numbering_patterns(self):
        return [
            (re.compile(r'^\d+\.\d*'), 0.8),
            (re.compile(r'^[A-Z]\.'), 0.7),
            (re.compile(r'^[IVXLC]+\.', re.IGNORECASE), 0.7),
            (re.compile(r'^(Chapter|Section)\s+\d+', re.IGNORECASE), 0.9),
        ]