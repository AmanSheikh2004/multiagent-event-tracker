import os
import re
import fitz  # PyMuPDF
from paddleocr import PaddleOCR


class OcrAgent:
    def __init__(self):
        print("[OCR Agent] Initializing smart hybrid OCR...")
        self.ocr = PaddleOCR(lang='en')
        print("[OCR Agent] Ready ✅")

    def extract_text(self, file_path):
        """
        Hybrid OCR: intelligently extracts title + abstract/introduction.
        Uses PyMuPDF for text-based PDFs and PaddleOCR for scanned pages.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        print(f"[OCR Agent] Processing {file_path} ...")
        pdf = fitz.open(file_path)
        all_text = ""

        # Extract only first 5 pages (performance optimization)
        for page_num, page in enumerate(pdf):
            if page_num > 4:
                break

            text = page.get_text("text")
            if len(text.strip()) > 100:
                all_text += "\n" + text
            else:
                # Fallback to OCR if no text layer found
                pix = page.get_pixmap(dpi=150)
                img_bytes = pix.tobytes("png")
                result = self.ocr.ocr(img_bytes, det=True, rec=True)
                page_text = " ".join([line[1][0] for line in result[0]]) if result and result[0] else ""
                all_text += "\n" + page_text

        pdf.close()

        text = re.sub(r'\s+', ' ', all_text).strip()
        title = self._extract_title(text)
        abstract = self._extract_abstract(text)

        return f"{title}\n\n{abstract}\n\n{text[:1500]}"

    def _extract_title(self, text):
        """
        Detects the project/event title based on patterns and capitalization.
        """
        # Try for “titled” or “project” phrases
        match = re.search(r'(?:titled|title[:\s]+)[“"]?([^“”"]{5,150})[”"]?', text, re.I)
        if match:
            return match.group(1).strip().title()

        match = re.search(r'(?:project|paper|seminar)[:\s]+([A-Z][A-Z0-9 :&,\-()]{5,150})', text)
        if match:
            return match.group(1).title().strip()

        # Try to find all-caps lines that look like titles (but skip universities)
        caps = re.findall(r'\b([A-Z][A-Z0-9 :\-&]{5,100})\b', text[:1000])
        for line in caps:
            if 10 < len(line) < 100 and not re.search(r'UNIVERSITY|ENGINEERING|COLLEGE|TECHNOLOGY', line):
                return line.title().strip()

        # Fallback to the first meaningful line
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        for line in lines[:10]:
            if len(line) > 5 and not re.search(r"(department|college|bachelor|technology|university)", line, re.I):
                return line.strip().title()

        return "Untitled Event"

    def _extract_abstract(self, text):
        """
        Extracts abstract or introduction intelligently while skipping certificate/acknowledgment.
        """
        # Skip certificate/acknowledgment parts
        text = re.sub(r'.*?(ACKNOWLEDGEMENT|CERTIFICATE)', '', text, flags=re.I | re.S)

        # Extract Abstract
        match = re.search(r'(?:ABSTRACT|Abstract)[:\s]+([\s\S]{0,1000}?)(?=\s[A-Z ]{3,}|INTRODUCTION|CHAPTER|$)', text)
        if match:
            return re.sub(r'\s+', ' ', match.group(1)).strip()

        # Or extract Introduction
        match = re.search(r'(?:INTRODUCTION|Introduction)[:\s]+([\s\S]{0,1000}?)(?=\s[A-Z ]{3,}|CHAPTER|$)', text)
        if match:
            return re.sub(r'\s+', ' ', match.group(1)).strip()

        return "No abstract or introduction detected."

    def summarize_extracted_text(self, text):
        """
        Produces a condensed summary (first 2000 chars).
        """
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        return " ".join(lines)[:2000]
