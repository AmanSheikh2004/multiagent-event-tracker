import os
import re
import fitz  # PyMuPDF
from datetime import datetime

class OcrAgent:
    def __init__(self):
        print("[OCR Agent] Ready ✅")

    def extract_text(self, file_path):
        """
        Extracts the title and abstract/introduction from PDF.
        Works well for academic or event reports.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        print(f"[OCR Agent] Processing {file_path} ...")
        pdf = fitz.open(file_path)

        # ---------------------------
        # 1️⃣ Extract title intelligently
        # ---------------------------
        first_page = pdf.load_page(0)
        title_text = ""
        blocks = first_page.get_text("dict")["blocks"]

        for b in blocks:
            if "lines" in b:
                for l in b["lines"]:
                    for s in l["spans"]:
                        text = s["text"].strip()
                        if (
                            len(text) > 5
                            and not re.search(r"(bachelor|technology|department|college|engineering)", text, re.I)
                            and s["size"] >= 13  # large font means title
                        ):
                            title_text = text
                            break
                    if title_text:
                        break
            if title_text:
                break

        # Fallback title
        if not title_text:
            all_text = first_page.get_text("text").split("\n")
            title_text = next((line for line in all_text if len(line.strip()) > 10), "Untitled Document")

        # ---------------------------
        # 2️⃣ Extract meaningful content (first 3 pages)
        # ---------------------------
        body_text = ""
        for page_num, page in enumerate(pdf):
            if page_num > 2:
                break
            body_text += "\n" + page.get_text("text")

        pdf.close()

        # Remove junk like headers/footers
        body_text = re.sub(r"\n+", "\n", body_text)
        body_text = re.sub(r"Page\s*\d+", "", body_text)

        # ---------------------------
        # 3️⃣ Detect abstract or introduction
        # ---------------------------
        match = re.search(r"(?:ABSTRACT|Abstract|abstract)[:\s\n]+([\s\S]{0,1500})", body_text)
        if match:
            abstract_part = match.group(1).strip()
        else:
            # Try Introduction
            match = re.search(r"(?:INTRODUCTION|Introduction)[:\s\n]+([\s\S]{0,1500})", body_text)
            abstract_part = match.group(1).strip() if match else ""

        # Clean abstract
        abstract_part = re.sub(r"\s+", " ", abstract_part).strip()
        if not abstract_part:
            abstract_part = "No abstract or introduction found."

        # ---------------------------
        # 4️⃣ Combine & summarize
        # ---------------------------
        summary = (
            f"Title: {title_text}\n\n"
            f"Abstract/Intro: {abstract_part[:800]}{'...' if len(abstract_part) > 800 else ''}"
        )

        print(f"[OCR Agent] Title extracted: {title_text}")
        print(f"[OCR Agent] Abstract length: {len(abstract_part)} characters")
        print("[OCR Agent] Text extraction complete.")
        return summary

    def summarize_extracted_text(self, text):
        """
        Optional post-processor — returns trimmed text (for dashboard display)
        """
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        short_text = " ".join(lines)
        return short_text[:2000]
