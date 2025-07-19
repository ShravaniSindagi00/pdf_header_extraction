#!/usr/bin/env python3
"""
Debug Viewer - Visual debugging tool for PDF outline extraction.

This tool provides a graphical interface to inspect detected text blocks,
font information, and heading classifications for debugging purposes.
"""

import sys
import argparse
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from extractor.pdf_parser import PDFParser
from extractor.heading_detector import HeadingDetector
from extractor.outline_builder import OutlineBuilder
from config.settings import Settings
from models.document import Document, TextBlock


class DebugViewer:
    """Visual debugging interface for PDF outline extraction."""
    
    def __init__(self, pdf_path: Path):
        self.pdf_path = pdf_path
        self.settings = Settings()
        self.document: Optional[Document] = None
        self.headings: List = []
        
        # Initialize GUI
        self.root = tk.Tk()
        self.root.title(f"PDF Debug Viewer - {pdf_path.name}")
        self.root.geometry("1200x800")
        
        self.setup_gui()
        self.process_pdf()
    
    def setup_gui(self):
        """Setup the GUI components."""
        # Create main frames
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab 1: Document Overview
        self.overview_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.overview_frame, text="Document Overview")
        self.setup_overview_tab()
        
        # Tab 2: Text Blocks
        self.blocks_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.blocks_frame, text="Text Blocks")
        self.setup_blocks_tab()
        
        # Tab 3: Detected Headings
        self.headings_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.headings_frame, text="Detected Headings")
        self.setup_headings_tab()
        
        # Tab 4: Font Analysis
        self.fonts_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.fonts_frame, text="Font Analysis")
        self.setup_fonts_tab()
        
        # Tab 5: Heuristic Scores
        self.scores_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.scores_frame, text="Heuristic Scores")
        self.setup_scores_tab()
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(self.main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.status_var.set("Ready")
    
    def setup_overview_tab(self):
        """Setup document overview tab."""
        # Document info frame
        info_frame = ttk.LabelFrame(self.overview_frame, text="Document Information")
        info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.info_text = scrolledtext.ScrolledText(info_frame, height=8, width=80)
        self.info_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Statistics frame
        stats_frame = ttk.LabelFrame(self.overview_frame, text="Processing Statistics")
        stats_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.stats_text = scrolledtext.ScrolledText(stats_frame, height=10, width=80)
        self.stats_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def setup_blocks_tab(self):
        """Setup text blocks analysis tab."""
        # Controls frame
        controls_frame = ttk.Frame(self.blocks_frame)
        controls_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(controls_frame, text="Page:").pack(side=tk.LEFT)
        self.page_var = tk.StringVar()
        self.page_combo = ttk.Combobox(controls_frame, textvariable=self.page_var, width=10)
        self.page_combo.pack(side=tk.LEFT, padx=5)
        self.page_combo.bind('<<ComboboxSelected>>', self.on_page_selected)
        
        ttk.Button(controls_frame, text="Refresh", command=self.refresh_blocks).pack(side=tk.LEFT, padx=5)
        
        # Text blocks list
        list_frame = ttk.LabelFrame(self.blocks_frame, text="Text Blocks")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Treeview for blocks
        columns = ('Text', 'Font', 'Size', 'Position', 'Potential Heading')
        self.blocks_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)
        
        for col in columns:
            self.blocks_tree.heading(col, text=col)
            self.blocks_tree.column(col, width=150)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.blocks_tree.yview)
        h_scrollbar = ttk.Scrollbar(list_frame, orient=tk.HORIZONTAL, command=self.blocks_tree.xview)
        self.blocks_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        self.blocks_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.blocks_tree.bind('<<TreeviewSelect>>', self.on_block_selected)
    
    def setup_headings_tab(self):
        """Setup detected headings tab."""
        # Headings list
        headings_frame = ttk.LabelFrame(self.headings_frame, text="Detected Headings")
        headings_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        columns = ('Level', 'Text', 'Page', 'Confidence', 'Font Info')
        self.headings_tree = ttk.Treeview(headings_frame, columns=columns, show='headings', height=20)
        
        for col in columns:
            self.headings_tree.heading(col, text=col)
            self.headings_tree.column(col, width=120)
        
        # Scrollbars
        v_scrollbar2 = ttk.Scrollbar(headings_frame, orient=tk.VERTICAL, command=self.headings_tree.yview)
        self.headings_tree.configure(yscrollcommand=v_scrollbar2.set)
        
        self.headings_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scrollbar2.pack(side=tk.RIGHT, fill=tk.Y)
    
    def setup_fonts_tab(self):
        """Setup font analysis tab."""
        # Font distribution chart
        chart_frame = ttk.LabelFrame(self.fonts_frame, text="Font Size Distribution")
        chart_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Matplotlib figure
        self.fig, (self.ax1, self.ax2) = plt.subplots(1, 2, figsize=(12, 6))
        self.canvas = FigureCanvasTkAgg(self.fig, chart_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Font details
        details_frame = ttk.LabelFrame(self.fonts_frame, text="Font Details")
        details_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.font_details_text = scrolledtext.ScrolledText(details_frame, height=8)
        self.font_details_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def setup_scores_tab(self):
        """Setup heuristic scores tab."""
        # Controls
        controls_frame = ttk.Frame(self.scores_frame)
        controls_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(controls_frame, text="Text Block:").pack(side=tk.LEFT)
        self.block_var = tk.StringVar()
        self.block_combo = ttk.Combobox(controls_frame, textvariable=self.block_var, width=50)
        self.block_combo.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.block_combo.bind('<<ComboboxSelected>>', self.on_block_for_scoring_selected)
        
        # Scores display
        scores_frame = ttk.LabelFrame(self.scores_frame, text="Heuristic Scores")
        scores_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.scores_text = scrolledtext.ScrolledText(scores_frame, height=20)
        self.scores_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def process_pdf(self):
        """Process the PDF and extract information."""
        try:
            self.status_var.set("Processing PDF...")
            self.root.update()
            
            # Parse PDF
            parser = PDFParser(self.settings)
            self.document = parser.parse(self.pdf_path)
            
            # Detect headings
            detector = HeadingDetector(self.settings)
            self.headings = detector.detect_headings(self.document)
            
            # Build outline
            builder = OutlineBuilder(self.settings)
            outline = builder.build_outline(self.headings)
            self.document.outline = outline
            
            # Update GUI
            self.update_overview()
            self.update_blocks()
            self.update_headings()
            self.update_fonts()
            self.update_scores()
            
            self.status_var.set(f"Processed {self.document.page_count} pages, found {len(self.headings)} headings")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to process PDF: {str(e)}")
            self.status_var.set("Error processing PDF")
    
    def update_overview(self):
        """Update document overview tab."""
        if not self.document:
            return
        
        # Document information
        info = f"""Document: {self.document.filename}
Pages: {self.document.page_count}
Text Blocks: {len(self.document.text_blocks)}
Processing Time: {getattr(self.document, 'processing_time', 0):.2f} seconds

Font Statistics:
- Average Font Size: {self.document.avg_font_size:.1f}
- Primary Font: {self.document.primary_font}
- Font Size Std Dev: {self.document.font_size_std:.1f}

Outline Statistics:
- Total Headings: {len(self.headings)}
- H1 Count: {len([h for h in self.headings if h.level == 1])}
- H2 Count: {len([h for h in self.headings if h.level == 2])}
- H3 Count: {len([h for h in self.headings if h.level == 3])}
"""
        
        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(1.0, info)
        
        # Processing statistics
        if hasattr(self.document, 'outline') and self.document.outline:
            stats = f"""Outline Quality Metrics:
- Average Confidence: {self.document.outline.average_confidence:.3f}
- Quality Score: {self.document.outline.quality_score:.3f}

Detection Settings:
- Min Confidence: {self.settings.MIN_HEADING_CONFIDENCE}
- Max Length: {self.settings.MAX_HEADING_LENGTH}
- Font Size Multipliers: {self.settings.HEADING_SIZE_MULTIPLIERS}

Performance Metrics:
- Text Blocks per Second: {len(self.document.text_blocks) / max(getattr(self.document, 'processing_time', 1), 0.1):.1f}
- Pages per Second: {self.document.page_count / max(getattr(self.document, 'processing_time', 1), 0.1):.1f}
"""
        else:
            stats = "No outline statistics available"
        
        self.stats_text.delete(1.0, tk.END)
        self.stats_text.insert(1.0, stats)
    
    def update_blocks(self):
        """Update text blocks tab."""
        if not self.document:
            return
        
        # Populate page combo
        pages = sorted(set(block.page for block in self.document.text_blocks))
        self.page_combo['values'] = ['All'] + [str(p) for p in pages]
        if not self.page_var.get():
            self.page_var.set('All')
        
        self.refresh_blocks()
    
    def refresh_blocks(self):
        """Refresh the blocks display."""
        if not self.document:
            return
        
        # Clear existing items
        for item in self.blocks_tree.get_children():
            self.blocks_tree.delete(item)
        
        # Filter blocks by page
        selected_page = self.page_var.get()
        if selected_page == 'All':
            blocks = self.document.text_blocks
        else:
            try:
                page_num = int(selected_page)
                blocks = [b for b in self.document.text_blocks if b.page == page_num]
            except ValueError:
                blocks = self.document.text_blocks
        
        # Add blocks to tree
        for i, block in enumerate(blocks[:100]):  # Limit to first 100 for performance
            text_preview = block.text[:50] + "..." if len(block.text) > 50 else block.text
            font_info = f"{block.font_info.family}"
            size_info = f"{block.font_info.size:.1f}"
            position = f"({block.x:.0f}, {block.y:.0f})"
            
            # Check if this block is a detected heading
            is_heading = any(h.text.strip() == block.text.strip() for h in self.headings)
            heading_status = "Yes" if is_heading else "No"
            
            self.blocks_tree.insert('', tk.END, values=(
                text_preview, font_info, size_info, position, heading_status
            ))
    
    def update_headings(self):
        """Update detected headings tab."""
        # Clear existing items
        for item in self.headings_tree.get_children():
            self.headings_tree.delete(item)
        
        # Add headings to tree
        for heading in self.headings:
            text_preview = heading.text[:60] + "..." if len(heading.text) > 60 else heading.text
            font_info = f"{heading.font_info.family} {heading.font_info.size:.1f}pt"
            
            self.headings_tree.insert('', tk.END, values=(
                f"H{heading.level}",
                text_preview,
                heading.page,
                f"{heading.confidence:.3f}",
                font_info
            ))
    
    def update_fonts(self):
        """Update font analysis tab."""
        if not self.document:
            return
        
        # Font size distribution
        font_sizes = [block.font_info.size for block in self.document.text_blocks]
        
        self.ax1.clear()
        self.ax1.hist(font_sizes, bins=20, alpha=0.7, edgecolor='black')
        self.ax1.axvline(self.document.avg_font_size, color='red', linestyle='--', 
                        label=f'Average: {self.document.avg_font_size:.1f}')
        self.ax1.set_xlabel('Font Size')
        self.ax1.set_ylabel('Frequency')
        self.ax1.set_title('Font Size Distribution')
        self.ax1.legend()
        
        # Font family distribution
        from collections import Counter
        font_families = [block.font_info.family for block in self.document.text_blocks]
        family_counts = Counter(font_families).most_common(10)
        
        if family_counts:
            families, counts = zip(*family_counts)
            self.ax2.clear()
            self.ax2.bar(range(len(families)), counts)
            self.ax2.set_xlabel('Font Family')
            self.ax2.set_ylabel('Usage Count')
            self.ax2.set_title('Font Family Usage')
            self.ax2.set_xticks(range(len(families)))
            self.ax2.set_xticklabels([f[:10] + '...' if len(f) > 10 else f for f in families], 
                                   rotation=45, ha='right')
        
        self.canvas.draw()
        
        # Font details
        details = "Font Analysis Details:\n\n"
        details += f"Total unique font sizes: {len(set(font_sizes))}\n"
        details += f"Font size range: {min(font_sizes):.1f} - {max(font_sizes):.1f}\n"
        details += f"Most common font size: {Counter(font_sizes).most_common(1)[0][0]:.1f}\n\n"
        
        details += "Font families by usage:\n"
        for family, count in family_counts:
            percentage = (count / len(font_families)) * 100
            details += f"  {family}: {count} blocks ({percentage:.1f}%)\n"
        
        self.font_details_text.delete(1.0, tk.END)
        self.font_details_text.insert(1.0, details)
    
    def update_scores(self):
        """Update heuristic scores tab."""
        if not self.document:
            return
        
        # Populate block combo with potential headings
        candidates = []
        for block in self.document.text_blocks:
            if (block.font_info.size > self.document.avg_font_size * 1.1 and 
                len(block.text.strip()) > 3 and 
                len(block.text.strip()) < 200):
                preview = block.text[:50] + "..." if len(block.text) > 50 else block.text
                candidates.append((preview, block))
        
        self.block_combo['values'] = [c[0] for c in candidates]
        self.block_candidates = {c[0]: c[1] for c in candidates}
        
        if candidates and not self.block_var.get():
            self.block_var.set(candidates[0][0])
            self.show_block_scores(candidates[0][1])
    
    def show_block_scores(self, block: TextBlock):
        """Show detailed heuristic scores for a text block."""
        if not self.document:
            return
        
        # Create a temporary heading detector to get scores
        detector = HeadingDetector(self.settings)
        
        # Calculate individual scores (simplified version)
        font_size_ratio = block.font_info.size / self.document.avg_font_size
        font_size_score = min(max((font_size_ratio - 1.0) * 2, 0), 1.0)
        
        font_style_score = 0.0
        if block.font_info.is_bold:
            font_style_score += 0.6
        if block.font_info.family != self.document.primary_font:
            font_style_score += 0.3
        font_style_score = min(font_style_score, 1.0)
        
        position_score = 0.0
        if block.x < 100:  # Left aligned
            position_score += 0.4
        if block.y < 150:  # Top of page
            position_score += 0.3
        position_score = min(position_score, 1.0)
        
        # Length score
        length = len(block.text.strip())
        if length <= 30:
            length_score = 1.0
        elif length <= 60:
            length_score = 0.7
        elif length <= 100:
            length_score = 0.4
        else:
            length_score = 0.1
        
        # Numbering score (simplified)
        import re
        numbering_score = 0.0
        if re.match(r'^\d+\.', block.text.strip()):
            numbering_score = 0.8
        elif re.match(r'^\d+\.\d+', block.text.strip()):
            numbering_score = 0.7
        
        # Keyword score (simplified)
        keyword_score = 0.0
        text_lower = block.text.lower()
        keywords = ['introduction', 'conclusion', 'abstract', 'summary', 'chapter', 'section']
        for keyword in keywords:
            if keyword in text_lower:
                keyword_score += 0.3
        keyword_score = min(keyword_score, 1.0)
        
        # Calculate final score
        final_score = (
            font_size_score * 0.3 +
            font_style_score * 0.2 +
            position_score * 0.15 +
            numbering_score * 0.15 +
            keyword_score * 0.1 +
            length_score * 0.1
        )
        
        # Display results
        scores_text = f"""Text Block Analysis
{'=' * 50}

Text: "{block.text}"

Font Information:
- Family: {block.font_info.family}
- Size: {block.font_info.size:.1f}pt
- Bold: {block.font_info.is_bold}
- Color: {block.font_info.color}

Position Information:
- Page: {block.page}
- Position: ({block.x:.1f}, {block.y:.1f})
- Size: {block.width:.1f} x {block.height:.1f}

Heuristic Scores:
{'=' * 30}

Font Size Score: {font_size_score:.3f} (weight: 30%)
- Size ratio: {font_size_ratio:.2f} (size/avg)
- Document avg: {self.document.avg_font_size:.1f}pt

Font Style Score: {font_style_score:.3f} (weight: 20%)
- Bold: {block.font_info.is_bold}
- Different family: {block.font_info.family != self.document.primary_font}

Position Score: {position_score:.3f} (weight: 15%)
- Left aligned: {block.x < 100}
- Top of page: {block.y < 150}

Numbering Score: {numbering_score:.3f} (weight: 15%)
- Has numbering pattern: {numbering_score > 0}

Keyword Score: {keyword_score:.3f} (weight: 10%)
- Contains heading keywords: {keyword_score > 0}

Length Score: {length_score:.3f} (weight: 10%)
- Text length: {length} characters

Final Score: {final_score:.3f}
Threshold: {self.settings.MIN_HEADING_CONFIDENCE}
Classification: {'HEADING' if final_score >= self.settings.MIN_HEADING_CONFIDENCE else 'NOT HEADING'}

Detected as Heading: {any(h.text.strip() == block.text.strip() for h in self.headings)}
"""
        
        self.scores_text.delete(1.0, tk.END)
        self.scores_text.insert(1.0, scores_text)
    
    def on_page_selected(self, event):
        """Handle page selection change."""
        self.refresh_blocks()
    
    def on_block_selected(self, event):
        """Handle text block selection."""
        selection = self.blocks_tree.selection()
        if selection:
            # Get selected block info
            item = self.blocks_tree.item(selection[0])
            # Could show detailed info in a popup or status bar
            pass
    
    def on_block_for_scoring_selected(self, event):
        """Handle block selection for scoring analysis."""
        selected_text = self.block_var.get()
        if selected_text in self.block_candidates:
            block = self.block_candidates[selected_text]
            self.show_block_scores(block)
    
    def run(self):
        """Run the debug viewer."""
        self.root.mainloop()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="PDF Outline Extractor Debug Viewer")
    parser.add_argument("pdf_file", help="Path to PDF file to analyze")
    parser.add_argument("--config", help="Configuration file path")
    
    args = parser.parse_args()
    
    pdf_path = Path(args.pdf_file)
    if not pdf_path.exists():
        print(f"Error: PDF file not found: {pdf_path}")
        sys.exit(1)
    
    try:
        viewer = DebugViewer(pdf_path)
        viewer.run()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()