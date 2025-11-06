from agents.ocr_agent import OcrAgent
from models import db, Document, Event, ExtractedEntity
import re
from datetime import datetime

class OrchestratorAgent:
    def __init__(self):
        self.ocr_agent = OcrAgent()

    def process_document(self, doc_id, file_path=None):
        from agents.ocr_agent import OcrAgent
        from agents.categorizer_agent import CategorizerAgent
        from models import Event, Document, db
        from datetime import datetime, date
        import os
        from config import Config

        print(f"[Orchestrator] Starting OCR for document ID {doc_id}")

        # Step 1: Locate file
        doc = Document.query.get(doc_id)
        if not file_path:
            file_path = os.path.join(Config.UPLOAD_FOLDER, doc.filename)

        # Step 2: OCR Extraction
        ocr = OcrAgent()
        full_text = ocr.extract_text(file_path)  # includes title + abstract
        summary_text = ocr.summarize_extracted_text(full_text)

        # Step 3: Categorize
        categorizer = CategorizerAgent()
        classification = categorizer.categorize(full_text)

        # Extract details
        category = classification.get("category", "General Event")
        department = classification.get("department", "General")

        # --- Extract event title and abstract from OCR ---
        lines = [l.strip() for l in full_text.split("\n") if l.strip()]
        title = lines[0] if lines else doc.filename
        abstract = ""
        for i, line in enumerate(lines):
            if re.search(r"(?i)abstract|introduction", line):
                abstract = " ".join(lines[i:i+10])  # read a few lines after
                break
        abstract = abstract or "Abstract/Intro not detected."

        # Date fallback
        event_date = classification.get("date")
        if isinstance(event_date, str):
            try:
                event_date = datetime.fromisoformat(event_date).date()
            except ValueError:
                event_date = date.today()
        elif not event_date:
            event_date = date.today()

        # Step 4: Save document info
        doc.raw_text = summary_text
        doc.category = category
        doc.department = department
        doc.status = "needs_review"
        db.session.add(doc)

        # Step 5: Save Event
        event = Event(
            document_id=doc.id,
            name=title.strip(),
            date=event_date,
            department=department,
            category=category,
            validated=False
        )
        db.session.add(event)
        db.session.commit()

        print(f"[Orchestrator] ✅ Processed: {title.strip()} ({category}, {department})")


    # --- Utility methods ---

    def _extract_event_name(self, text):
        # Use first non-empty line as title (most reliable)
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        if lines:
            first_line = lines[0]
            # Avoid degree or department names
            if not re.search(r"(department|technology|engineering|bachelor|college)", first_line, re.I):
                return first_line
            # Otherwise skip to next meaningful line
            for line in lines[1:5]:
                if len(line) > 10 and not re.search(r"(department|technology|engineering|bachelor|college)", line, re.I):
                    return line
        return "Untitled Event"


    def _extract_date(self, text):
        # Basic date finder (handles dd/mm/yyyy, dd-mm-yyyy, etc.)
        date_match = re.search(r"(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})", text)
        if date_match:
            date_str = date_match.group(1)
            for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y"):
                try:
                    return datetime.strptime(date_str, fmt).date()
                except:
                    continue
        return None

    def _extract_department(self, text):
        # Look for department keywords
        match = re.search(r"Department\s*of\s*([A-Za-z& ]+)", text, re.I)
        if match:
            return match.group(1).strip()
        if "CSE" in text.upper():
            return "Computer Science"
        if "ECE" in text.upper():
            return "Electronics"
        if "MECH" in text.upper():
            return "Mechanical"
        return None

    def _categorize_event(self, text):
        if re.search(r"workshop|training", text, re.I):
            return "Workshop"
        if re.search(r"seminar|talk|guest lecture", text, re.I):
            return "Seminar"
        if re.search(r"competition|hackathon", text, re.I):
            return "Competition"
        return "General Event"

    def _save_entity(self, label, value, confidence, doc_id):
        entity = ExtractedEntity(
            document_id=doc_id,
            label=label,
            text=value,
            confidence=confidence
        )
        db.session.add(entity)
