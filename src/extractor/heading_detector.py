"""
Heading Detector - Identify H1, H2, H3 headings using advanced heuristics.
Supports different strategies for different languages.
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
        # English Heuristics
        self._eng_keywords = self._load_english_keywords()
        self._eng_numbering = self._compile_english_numbering()
        # Japanese Heuristics
        self._jpn_keywords = self._load_japanese_keywords()
        self._jpn_numbering = self._compile_japanese_numbering()

    def detect_headings(self, document: Document) -> List[Heading]:
        """
        Router function to call the appropriate heading detector based on language.
        """
        logger.info(f"Starting heading detection for {document.filename} (lang: {document.language})")
        
        if document.language == 'japanese':
            return self._detect_headings_japanese(document)
        else:
            return self._detect_headings_english(document)

    # --- English Heading Detection Logic (Your existing logic) ---

    def _detect_headings_english(self, document: Document) -> List[Heading]:
        candidates = self._identify_candidates_english(document)
        scored_candidates = self._score_candidates_english(candidates, document)
        headings = self._classify_heading_levels(scored_candidates)
        final_headings = self._post_process_headings(headings)
        
        logger.info(f"Detected {len(final_headings)} English headings.")
        return final_headings

    def _identify_candidates_english(self, document: Document) -> List[TextBlock]:
        candidates = []
        for block in document.text_blocks:
            text = block.text.strip()
            if not text or len(text) > self.settings.MAX_HEADING_LENGTH: continue
            if block.font_info.size < (document.avg_font_size or 12.0): continue
            if text.endswith(('.', '!', '?', ';', ':')) and len(text) > 20: continue
            candidates.append(block)
        return candidates
    
    def _score_candidates_english(self, candidates: List[TextBlock], document: Document) -> List[Tuple[TextBlock, float]]:
        """Score candidates for English documents."""
        scored = []
        for block in candidates:
            weights = {"size": 0.5, "style": 0.3, "position": 0.1, "numbering": 0.1}
            score = (
                self._calculate_font_size_score(block, document) * weights["size"] +
                self._calculate_font_style_score(block, document) * weights["style"] +
                self._calculate_position_score(block, document) * weights["position"] +
                self._calculate_numbering_score(block, self._eng_numbering) * weights["numbering"]
            )
            if self._calculate_keyword_score(block, self._eng_keywords) > 0:
                score = min(1.0, score + 0.1)

            if score >= self.settings.MIN_HEADING_CONFIDENCE:
                scored.append((block, score))
        return sorted(scored, key=lambda x: x[1], reverse=True)

    # --- Japanese Heading Detection Logic (NEW) ---

    def _detect_headings_japanese(self, document: Document) -> List[Heading]:
        """
        A dedicated set of heuristics for detecting headings in Japanese documents.
        This is a starting point and can be expanded.
        """
        # NOTE: Japanese heuristics are different. Font size is still important,
        # but keywords and numbering patterns are key.
        candidates = document.text_blocks # Start with all blocks
        scored_candidates = self._score_candidates_japanese(candidates, document)
        headings = self._classify_heading_levels(scored_candidates)
        final_headings = self._post_process_headings(headings)
        
        logger.info(f"Detected {len(final_headings)} Japanese headings.")
        return final_headings

    def _score_candidates_japanese(self, candidates: List[TextBlock], document: Document) -> List[Tuple[TextBlock, float]]:
        """Score candidates for Japanese documents."""
        scored = []
        for block in candidates:
            # For Japanese, numbering and keywords are much stronger signals
            weights = {"size": 0.4, "style": 0.2, "numbering": 0.3, "keyword": 0.1}
            score = (
                self._calculate_font_size_score(block, document) * weights["size"] +
                self._calculate_font_style_score(block, document) * weights["style"] +
                self._calculate_numbering_score(block, self._jpn_numbering) * weights["numbering"] +
                self._calculate_keyword_score(block, self._jpn_keywords) * weights["keyword"]
            )
            if score >= self.settings.MIN_HEADING_CONFIDENCE:
                scored.append((block, score))
        return sorted(scored, key=lambda x: x[1], reverse=True)


    # --- Common Helper Functions ---

    def _calculate_font_size_score(self, block, doc):
        ratio = block.font_info.size / (doc.avg_font_size or 12.0)
        if ratio > 1.5: return 1.0
        if ratio > 1.3: return 0.8
        if ratio > 1.1: return 0.6
        return 0.2

    def _calculate_font_style_score(self, block, doc):
        score = 0
        font_name = block.font_info.family.lower()
        if any(w in font_name for w in ['bold', 'black', 'heavy', 'gothicb']): score += 0.8
        return min(score, 1.0)
        
    def _calculate_position_score(self, block, doc):
        # This is less reliable for Japanese, so it's only used for English
        page_width = doc.page_dimensions[block.page - 1][0]
        center_diff = abs((block.x + block.width / 2) - (page_width / 2))
        if center_diff < (page_width * 0.15): return 0.8
        if block.x < (page_width * 0.1): return 0.5
        return 0

    def _calculate_numbering_score(self, block, numbering_rules):
        return next((score for pattern, score in numbering_rules if pattern.match(block.text.strip())), 0)

    def _calculate_keyword_score(self, block, keyword_set):
        return 1 if any(keyword in block.text for keyword in keyword_set) else 0

    def _classify_heading_levels(self, scored_candidates):
        if not scored_candidates: return []
        size_groups = defaultdict(list)
        for block, score in scored_candidates:
            size_groups[round(block.font_info.size, 1)].append((block, score))
        
        sorted_sizes = sorted(size_groups.keys(), reverse=True)
        headings = []
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
        if not headings: return []
        headings.sort(key=lambda h: (h.page, h.position[1]))
        unique_headings, seen_texts = [], set()
        for h in headings:
            norm_text = h.text.lower().strip()
            if norm_text not in seen_texts:
                unique_headings.append(h)
                seen_texts.add(norm_text)
        return unique_headings

    # --- Language-Specific Dictionaries ---

    def _load_english_keywords(self):
        return {'introduction', 'conclusion', 'abstract', 'summary', 'background', 
                'methodology', 'results', 'discussion', 'references', 'appendix', 
                'chapter', 'section'}

    def _compile_english_numbering(self):
        return [
            (re.compile(r'^\d+\.\d*'), 0.8),
            (re.compile(r'^[A-Z]\.'), 0.7),
            (re.compile(r'^[IVXLC]+\.\s+', re.IGNORECASE), 0.7),
            (re.compile(r'^(Chapter|Section)\s+\d+', re.IGNORECASE), 0.9),
        ]

    def _load_japanese_keywords(self):
        return {'概要', 'はじめに', '要旨', '背景', '目的', '方法', '結果', '考察', '結論', '参考文献', '付録'}

    def _compile_japanese_numbering(self):
        return [
            (re.compile(r'^第[一二三四五六七八九十百]+(章|節)'), 1.0), # "Chapter 1", etc.
            (re.compile(r'^\d+．'), 0.8), # Full-width dot
            (re.compile(r'^\d+\.\d*'), 0.7),
        ]