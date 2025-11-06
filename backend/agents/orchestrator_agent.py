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
        from agents.tracker_agent import TrackerAgent
        from models import Event

        print(f"[Orchestrator] Starting OCR for document ID {doc_id}")

        import os
        from config import Config

        # Step 1: Locate file
        doc = Document.query.get(doc_id)
        if not file_path:
            file_path = os.path.join(Config.UPLOAD_FOLDER, doc.filename)

        # Step 2: OCR
        ocr = OcrAgent()
        full_text = ocr.extract_text(file_path)
        summary_text = ocr.summarize_extracted_text(full_text)

        categorizer = CategorizerAgent()
        classification = categorizer.categorize(full_text)

        category = classification.get("category", "General Event")
        department = classification.get("department", "General")
        event_name = self._extract_event_name(full_text) or doc.filename
        event_date = classification.get("date") or datetime.today().date()
        event_department = department
        event_category = category


        # Step 5: Save results to DB
        doc.raw_text = summary_text
        doc.category = event_category
        doc.department = event_department
        doc.status = "needs_review"
        db.session.add(doc)

        # ✅ Create a linked event entry for IQC
        from datetime import datetime, date

        # Ensure date is always a Python date object
        if isinstance(event_date, str):
            try:
                event_date = datetime.fromisoformat(event_date).date()
            except ValueError:
                event_date = date.today()

        event = Event(
            document_id=doc.id,
            name=event_name,
            date=event_date,  # now a true date object
            department=event_department,
            category=event_category,
            validated=False
        )
        db.session.add(event)
        db.session.commit()


        print(f"[Orchestrator] Document {doc.filename} processed successfully as {event_category} ({event_department}).")
        print(f"[Orchestrator] Event '{event_name}' added for IQC validation.")



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
