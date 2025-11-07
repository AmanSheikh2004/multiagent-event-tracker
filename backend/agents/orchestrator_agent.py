from agents.ocr_agent import OcrAgent
from models import db, Document, Event, ExtractedEntity
import re
from datetime import datetime, date
import os
from config import Config

class OrchestratorAgent:
    def __init__(self):
        # keep single OCR instance for faster repeated calls
        try:
            self.ocr_agent = OcrAgent()
        except Exception as e:
            # If OCR initialization fails, log but keep going (will raise later if used)
            print("[Orchestrator] OCR init failed:", e)
            self.ocr_agent = None

    def process_document(self, doc_id, file_path=None):
        """
        Process a saved document:
         1) Locate file path
         2) Extract text (OCR)
         3) Categorize (via CategorizerAgent)
         4) Save summary into Document.raw_text
         5) Create an Event entry
        """
        from agents.categorizer_agent import CategorizerAgent

        print(f"[Orchestrator] Starting processing for document ID {doc_id}")

        doc = Document.query.get(doc_id)
        if not doc:
            print(f"[Orchestrator] Document id={doc_id} not found")
            return

        # mark processing
        doc.status = "processing"
        db.session.add(doc)
        db.session.commit()

        # resolve file path
        if not file_path:
            upload_folder = getattr(Config, "UPLOAD_FOLDER", "static/uploads")
            file_path = os.path.join(upload_folder, doc.filename)

        if not os.path.exists(file_path):
            doc.status = "failed"
            doc.last_error = f"file not found: {file_path}"
            db.session.add(doc)
            db.session.commit()
            print(f"[Orchestrator] File not found: {file_path}")
            return

        try:
            # Use the created OCR agent (if available) otherwise create one
            ocr = self.ocr_agent or OcrAgent()
            full_text = ocr.extract_text(file_path)
            summary_text = ocr.summarize_extracted_text(full_text)

            # Categorize
            categorizer = CategorizerAgent()
            classification = categorizer.categorize(full_text)

            category = classification.get("category", "General Event")
            department = classification.get("department", "General")
            event_date = classification.get("date")

            # normalize date -> date object
            if isinstance(event_date, str):
                try:
                    # Try ISO
                    event_date_obj = datetime.fromisoformat(event_date).date()
                except Exception:
                    # try fuzzy parse (simple fallback)
                    try:
                        # attempt dd/mm/yyyy or dd-mm-yyyy
                        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y"):
                            try:
                                event_date_obj = datetime.strptime(event_date, fmt).date()
                                break
                            except:
                                event_date_obj = None
                        if event_date_obj is None:
                            event_date_obj = date.today()
                    except:
                        event_date_obj = date.today()
            elif isinstance(event_date, date):
                event_date_obj = event_date
            else:
                event_date_obj = date.today()

            # Extract title (first meaningful line)
            lines = [l.strip() for l in full_text.split("\n") if l.strip()]
            title = lines[0] if lines else doc.filename
            abstract = ""
            for i, line in enumerate(lines):
                if re.search(r"(?i)abstract|introduction", line):
                    abstract = " ".join(lines[i:i+10])
                    break
            abstract = abstract or "Abstract/Intro not detected."

            # Save document updates
            doc.raw_text = summary_text
            doc.category = category
            doc.department = department
            doc.status = "needs_review"
            doc.last_error = None
            db.session.add(doc)

            # Create an Event record
            event = Event(
                document_id=doc.id,
                name=title.strip(),
                date=event_date_obj,
                department=department,
                category=category,
                validated=False
            )
            db.session.add(event)

            # Optionally, save some entities (basic)
            # (keeping ExtractedEntity saving minimal here — categorizer/ner can add more)
            db.session.commit()

            print(f"[Orchestrator] ✅ Processed: {title.strip()} ({category}, {department})")

        except Exception as e:
            # Capture error on doc and save last_error
            doc.status = "failed"
            doc.last_error = str(e)
            db.session.add(doc)
            db.session.commit()
            print(f"[Orchestrator] Processing failed for doc {doc_id}: {e}")

    # Utility helpers (kept for possible future use)
    def _extract_event_name(self, text):
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        if lines:
            first_line = lines[0]
            if not re.search(r"(department|technology|engineering|bachelor|college)", first_line, re.I):
                return first_line
            for line in lines[1:5]:
                if len(line) > 10 and not re.search(r"(department|technology|engineering|bachelor|college)", line, re.I):
                    return line
        return "Untitled Event"

    def _extract_date(self, text):
        date_match = re.search(r"(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})", text)
        if date_match:
            date_str = date_match.group(1)
            for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y"):
                try:
                    return datetime.strptime(date_str, fmt).date()
                except:
                    continue
        return None
