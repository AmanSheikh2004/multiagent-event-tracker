import re
from datetime import datetime

class CategorizerAgent:
    def __init__(self):
        # Department detection keywords (AIML prioritized first)
        self.department_keywords = {
            "Artificial Intelligence & Machine Learning": [
                r"\bAIML\b",
                r"\bAI&ML",
                r"ARTIFICIAL INTELLIGENCE",
                r"MACHINE LEARNING",
                r"DEEP LEARNING",
                r"NEURAL NETWORKS",
            ],
            "Computer Science & Engineering": [
                r"\bCSE\b",
                r"COMPUTER SCIENCE",
                r"PROGRAMMING",
                r"DATA STRUCTURE",
                r"SOFTWARE ENGINEERING",
            ],
            "Information Science & Engineering": [
                r"\bISE\b",
                r"INFORMATION SCIENCE",
                r"DATA ANALYTICS",
            ],
            "Electronics & Communication Engineering": [
                r"\bECE\b",
                r"ELECTRONICS",
                r"COMMUNICATION",
                r"VLSI",
            ],
        }

        self.category_keywords = {
            "Workshop": ["WORKSHOP", "HANDS-ON", "SEMINAR"],
            "Conference": ["CONFERENCE", "PAPER", "PROCEEDINGS", "JOURNAL"],
            "Competition": ["COMPETITION", "HACKATHON", "CONTEST"],
            "General Event": ["REPORT", "PROJECT", "ACTIVITY", "EVENT"],
        }

    # --- NEW: Event name extraction ---
    def extract_event_name(self, text):
        lines = [l.strip() for l in text.split("\n") if l.strip()]

        # ✅ Step 1: Try to find title inside parentheses like (Ultrares: ...)
        for line in lines:
            match = re.search(r"\(([^)]+)\)", line)
            if match and len(match.group(1).split()) > 2:
                return match.group(1).strip()

        # ✅ Step 2: Try explicit keywords like Title / Project / Paper
        for line in lines:
            if re.search(r"(title|project|paper|seminar|report|event)", line, re.IGNORECASE):
                clean = re.sub(r"^(title|project|paper|seminar|report|event)\s*[:\-]*\s*", "", line, flags=re.IGNORECASE)
                if 3 < len(clean.split()) < 15:
                    return clean.strip()

        # ✅ Step 3: Try any line with a colon (e.g. Ultrares: Boosting Image Quality ...)
        for line in lines:
            if ":" in line and len(line.split()) < 15:
                return line.strip()

        # ✅ Step 4: Fallback: first all-caps line or short title-like line
        for line in lines:
            if len(line) > 8 and len(line.split()) < 15 and sum(1 for c in line if c.isupper()) > 5:
                return line.strip()

        # ✅ Step 5: Final fallback: first short sentence before a period
        sentences = re.split(r'\.|\n', text)
        for s in sentences:
            if 8 < len(s) < 120:
                return s.strip()

        return "Unknown"


    def categorize(self, text: str):
        text_upper = text.upper()

        # --- Department Detection ---
        detected_dept = "Unknown"
        for dept, patterns in self.department_keywords.items():
            for p in patterns:
                if re.search(p, text_upper):
                    detected_dept = dept
                    break
            if detected_dept != "Unknown":
                break

        # AIML takes priority if mentioned
        if "ARTIFICIAL INTELLIGENCE" in text_upper or "MACHINE LEARNING" in text_upper:
            detected_dept = "Artificial Intelligence & Machine Learning"

        # --- Category Detection ---
        detected_cat = "General Event"
        for cat, patterns in self.category_keywords.items():
            if any(re.search(p, text_upper) for p in patterns):
                detected_cat = cat
                break

        # --- Date Extraction (fallback to today if not found) ---
        date_match = re.search(r"(\d{1,2}[\/\-\.\s](?:\d{1,2}|[A-Za-z]+)[\/\-\.\s]\d{2,4})", text)
        if date_match:
            extracted_date = date_match.group(1)
        else:
            extracted_date = datetime.now().strftime("%Y-%m-%d")

        # --- Event Name Extraction ---
        event_name = self.extract_event_name(text)

        return {
            "event_name": event_name,
            "department": detected_dept,
            "category": detected_cat,
            "date": extracted_date,
        }
