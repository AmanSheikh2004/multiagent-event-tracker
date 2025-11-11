import re
from datetime import datetime

class CategorizerAgent:
    def __init__(self):
        print("[Categorizer Agent] Initialized ✅ (Hybrid Smart Version)")

        # --- Department detection ---
        self.department_keywords = {
            "Artificial Intelligence & Machine Learning": [
                r"\bAIML\b", r"\bAI\s*&\s*ML", r"ARTIFICIAL INTELLIGENCE", r"MACHINE LEARNING", r"DEEP LEARNING", r"NEURAL NETWORK"
            ],
            "Computer Science & Engineering": [
                r"\bCSE\b", r"COMPUTER SCIENCE", r"PROGRAMMING", r"DATA STRUCTURE", r"SOFTWARE ENGINEERING"
            ],
            "Information Science & Engineering": [
                r"\bISE\b", r"INFORMATION SCIENCE", r"DATA ANALYTICS", r"DATA MINING"
            ],
            "Electronics & Communication Engineering": [
                r"\bECE\b", r"ELECTRONICS", r"COMMUNICATION", r"VLSI", r"EMBEDDED"
            ],
        }

        # --- Event category detection ---
        self.category_keywords = {
            "Workshop": ["WORKSHOP", "HANDS-ON", "TRAINING", "BOOTCAMP"],
            "Conference": ["CONFERENCE", "SYMPOSIUM", "SUMMIT", "PROCEEDINGS"],
            "Competition": ["COMPETITION", "CONTEST", "HACKATHON", "QUIZ"],
            "Guest Lecture": ["GUEST LECTURE", "INVITED TALK", "EXPERT SESSION"],
            "Orientation": ["ORIENTATION", "INDUCTION", "WELCOME PROGRAM"],
        }

        # --- Research / report detection ---
        self.research_keywords = [
            "ABSTRACT", "INTRODUCTION", "CONCLUSION", "RESULTS", "METHODOLOGY",
            "STUDY", "REVIEW", "EXPERIMENT", "DATASET", "ANALYSIS"
        ]

    # --- Extract Event Title ---
    def extract_event_name(self, text: str):
        lines = [l.strip() for l in text.split("\n") if l.strip()]

        # Look for title indicators
        for line in lines:
            if re.match(r"^(title|project|event|seminar|topic)\s*[:\-]", line, re.IGNORECASE):
                title = re.sub(r"^(title|project|event|seminar|topic)\s*[:\-]*\s*", "", line, flags=re.IGNORECASE)
                if 5 <= len(title.split()) <= 15:
                    return title.title()

        # Title candidates (short but informative)
        for line in lines:
            if ":" in line and len(line.split()) < 15:
                return line.title()

        for line in lines:
            if line.isupper() and 5 < len(line.split()) < 15:
                return line.title()

        # fallback — first decent sentence
        sentences = re.split(r"[.:\n]", text)
        for s in sentences:
            if 5 < len(s.split()) < 15:
                return s.strip().title()

        return "Unknown Event"

        # --- Detect if document is a Certificate or Report ---
    def detect_doc_type(self, text: str):
        """Detect whether document is a Certificate or Report."""
        if not text or len(text.strip()) < 10:
            return "Unknown"

        text_upper = text.upper()
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        top_region = " ".join(lines[:25])

        # 🔹 Certificate clues
        certificate_phrases = [
            "CERTIFICATE", "THIS IS TO CERTIFY", "AWARDED TO",
            "PRESENTED TO", "HAS SUCCESSFULLY COMPLETED",
            "CERTIFICATE OF COMPLETION", "CERTIFICATE OF APPRECIATION",
            "CERTIFICATE OF PARTICIPATION", "IS HEREBY CERTIFIED"
        ]

        # 🔹 Report cues
        report_phrases = [
            "REPORT", "PROJECT REPORT", "FINAL REPORT", "SUMMARY",
            "INTRODUCTION", "CONCLUSION", "ANALYSIS", "RESULTS", "STUDY"
        ]

        # 1️⃣ If “CERTIFICATE” appears near the top → Certificate
        for phrase in certificate_phrases:
            if phrase in top_region:
                return "Certificate"

        # 2️⃣ If strong certificate phrases appear anywhere → Certificate
        for phrase in certificate_phrases:
            if re.search(rf"\b{phrase}\b", text_upper):
                return "Certificate"

        # 3️⃣ If “report” phrases dominate
        report_hits = sum(phrase in text_upper for phrase in report_phrases)
        cert_hits = sum(phrase in text_upper for phrase in certificate_phrases)

        if report_hits > cert_hits:
            return "Report"

        # 4️⃣ Short document heuristic (1-2 pages → likely certificate)
        if len(text) < 7000 and cert_hits > 0:
            return "Certificate"

        # Default fallback
        return "Report"


    def categorize(self, text: str):
        if not text or len(text.strip()) < 10:
            return {
                "event_name": "Unknown",
                "department": "Unknown",
                "category": "General",
                "date": datetime.now().strftime("%Y-%m-%d"),
                "confidence": 0.5
            }

        text_upper = text.upper()

        # --- Department detection ---
        detected_dept = "Unknown"
        for dept, patterns in self.department_keywords.items():
            if any(re.search(p, text_upper) for p in patterns):
                detected_dept = dept
                break
        if "ARTIFICIAL INTELLIGENCE" in text_upper or "MACHINE LEARNING" in text_upper:
            detected_dept = "Artificial Intelligence & Machine Learning"

        # --- Event vs Research vs General categorization ---
        detected_cat = "General"
        event_score, research_score = 0, 0

        # Event indicators
        for cat, patterns in self.category_keywords.items():
            if any(re.search(p, text_upper) for p in patterns):
                detected_cat = cat
                event_score += 2

        # Research indicators
        for kw in self.research_keywords:
            if re.search(rf"\b{kw}\b", text_upper):
                research_score += 2

        # Determine dominant category
        if research_score > event_score + 2:
            detected_cat = "Research/Report"
        elif event_score == 0 and research_score == 0:
            detected_cat = "General Event"

        # --- Date detection ---
        date_match = re.search(r"(\d{1,2}[/\-\.\s](?:\d{1,2}|[A-Za-z]+)[/\-\.\s]\d{2,4})", text)
        extracted_date = date_match.group(1) if date_match else datetime.now().strftime("%Y-%m-%d")

        # --- Event name / title ---
        event_name = self.extract_event_name(text)

        # --- Normalize department short codes ---
        dept_map = {
            "Artificial Intelligence & Machine Learning": "AIML",
            "Computer Science & Engineering": "CSE(Core)",
            "Information Science & Engineering": "ISE",
            "Electronics & Communication Engineering": "ECE",
        }
        short_dept = dept_map.get(detected_dept, detected_dept)

        # --- Confidence calculation ---
        confidence = 0.6
        if detected_dept != "Unknown":
            confidence += 0.15
        if detected_cat not in ["General", "General Event"]:
            confidence += 0.15

            # --- Detect if document is Certificate or Report ---
        doc_type = self.detect_doc_type(text)

        return {
            "event_name": event_name,
            "department": short_dept,
            "category": detected_cat,
            "date": extracted_date,
            "confidence": round(min(confidence, 1.0), 2),
            "doc_type": self.detect_doc_type(text),
        }

