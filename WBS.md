
### ## Step 1: Improve Heading Detection Accuracy

This is where you'll gain the most points. The goal is to move beyond simple font size rules and handle complex, real-world PDFs.

#### **A. Analyze Whitespace and Layout**

Headings often have more space around them than regular text.

* **Action:** In `extractor/heading_detector.py`, upgrade your `_has_whitespace_around` function. Instead of just checking for nearby blocks, calculate the vertical distance between a candidate block and the text block that appeared directly above it. A larger-than-average gap is a strong signal that a new section is starting.
* **Example Logic:**
    * Find the text block on the same page that is closest vertically *above* the current candidate.
    * If the distance is, for example, more than 1.5 times the height of the candidate text, significantly boost its heading score.

#### **B. Use Font Weight and Style More Granularly**

Different heading levels often use different font weights (e.g., "Black" or "Heavy" for H1, "Bold" for H2).

* **Action:** In `_calculate_font_style_score` within `heading_detector.py`, assign different scores for different bold indicators.
* **Example Logic:**
    * If the font name contains "Black" or "Heavy", add `0.8` to the score.
    * If it just contains "Bold", add `0.6`.
    * This helps differentiate between H1 and H2/H3 headings more accurately.

#### **C. Detect Centered Text for Titles**

Titles and top-level headings are often centered on the page.

* **Action:** Add a check in your `_calculate_position_score` function to identify centered text.
* **Example Logic:**
    * Get the page width (e.g., from `page.rect.width` in `PyMuPDF`).
    * Calculate the horizontal center of the text block: `block.x + (block.width / 2)`.
    * If the block's center is very close to the page's center, it's highly likely to be a title or H1. Give it a large score boost.

***

### ## Step 2: Ensure Performance (≤ 10 seconds)**

Your application needs to be fast. While it seems fast now with a small sample, a 50-page document is much larger.

* **Action:** The most time-consuming part of your process is likely the `_enhance_font_analysis` step in `pdf_parser.py`, which uses `pdfplumber`. You can make this step smarter.
* **Example Logic:**
    1.  First, do a quick pass on all pages using only the fast `PyMuPDF` parser.
    2.  Identify a small set of "candidate pages" that contain text with unusually large or bold fonts.
    3.  *Then*, run the slower, more detailed `pdfplumber` analysis **only on those specific candidate pages**, instead of always doing it on the first three pages. This will significantly speed up processing for most documents.

***

### ## Step 3: Tackle the Bonus (Multilingual Support)

This can set your project apart. Handling a language like Japanese requires a different approach because it doesn't use spaces and has unique characters.

* **Action**: Create a language-specific detection strategy. You can add a function at the beginning of your pipeline to detect the document's language (e.g., by checking for specific character ranges). Based on the result, you can switch to a different set of rules.
* **Japanese Strategy:**
    1.  **Update Numbering Patterns**: In `heading_detector.py`, add Japanese numbering patterns to your `_compile_numbering_patterns` method. For example: `(re.compile(r'^第[一二三四五六七八九十百]+章'), 0.9)` to detect "Chapter 1", "Chapter 2", etc.
    2.  **Add Japanese Keywords**: Create a separate keyword dictionary for Japanese terms like `概要` (Summary), `はじめに` (Introduction), and `結論` (Conclusion).
    3.  **Handle Vertical Text**: `pdfplumber` is generally better at handling vertical text, which is common in Japanese documents. You might need to rely on it more heavily for parsing if you detect a Japanese document.

