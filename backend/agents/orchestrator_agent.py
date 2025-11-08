from agents.ocr_agent import OcrAgent
from agents.ner_agent import NerAgent
from agents.categorizer_agent import CategorizerAgent
from models import db, Document, Event, ExtractedEntity
import re
from datetime import datetime, date
import os
from config import Config


class OrchestratorAgent:
    def __init__(self):
        try:
            self.ocr_agent = OcrAgent()
        except Exception as e:
            print("[Orchestrator] ⚠️ OCR init failed:", e)
            self.ocr_agent = None
        print("[Orchestrator] Ready ✅")

    def process_document(self, doc_id, file_path=None):
        """Process document end-to-end:
        OCR → NER → CATEGORIZER → DB persist
        """
        print(f"[Orchestrator] 🚀 Starting processing for Document ID {doc_id}")

        doc = Document.query.get(doc_id)
        if not doc:
            print(f"[Orchestrator] ❌ Document id={doc_id} not found.")
            return

        doc.status = "processing"
        db.session.commit()

        upload_folder = getattr(Config, "UPLOAD_FOLDER", "static/uploads")
        file_path = file_path or os.path.join(upload_folder, doc.filename)
        if not os.path.exists(file_path):
            doc.status = "failed"
            doc.last_error = f"File not found: {file_path}"
            db.session.commit()
            return

        try:
            # ---------- 1️⃣ OCR ----------
            ocr = self.ocr_agent or OcrAgent()
            ocr_output = ocr.extract_text(file_path)

            # Support both dict (new) and string (legacy)
            if isinstance(ocr_output, dict):
                raw_text = ocr_output.get("text", "")
                detected_title = ocr_output.get("title", "")
            else:
                raw_text = ocr_output
                detected_title = None

            summary_text = ocr.summarize_extracted_text(raw_text)

            # ---------- 2️⃣ NER ----------
            ner = NerAgent()
            ner_output = ner.process({"raw_text": raw_text})

            event_name = ner_output.get("event_name")
            event_date = ner_output.get("date")
            department = ner_output.get("department")
            venue = ner_output.get("venue")
            organizer = ner_output.get("organizer")

            # ---------- 3️⃣ Categorizer ----------
            cat = CategorizerAgent()
            classification = cat.categorize(raw_text)

            category = classification.get("category", "General Event")
            classified_dept = classification.get("department", department or "General")

            # Normalize date
            if isinstance(event_date, str):
                try:
                    event_date_obj = datetime.fromisoformat(event_date).date()
                except Exception:
                    event_date_obj = date.today()
            elif isinstance(event_date, date):
                event_date_obj = event_date
            else:
                event_date_obj = date.today()

            # ---------- 4️⃣ Abstract + title extraction ----------
            lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
            title = event_name or detected_title or (lines[0] if lines else doc.filename)

            # Find abstract-like section
            abstract = ""
            for i, line in enumerate(lines):
                if re.search(r"\b(abstract|introduction)\b", line, re.I):
                    # Capture next few lines to get context
                    next_lines = lines[i + 1:i + 6]
                    abstract = line + "\n" + "\n".join(next_lines)
                    break
            if not abstract:
                abstract = "Abstract not found."

            # ---------- 5️⃣ Save Document ----------
            doc.raw_text = summary_text
            doc.department = classified_dept
            doc.category = category
            doc.status = "needs_review"
            doc.last_error = None
            db.session.add(doc)

            # ---------- 6️⃣ Create Event ----------
            event = Event(
                document_id=doc.id,
                name=title.strip(),
                date=event_date_obj,
                department=classified_dept,
                category=category,
                validated=False
            )
            db.session.add(event)
            db.session.commit()

            # ---------- 7️⃣ Save NER entities ----------
            entity_map = {
                "event_name": event_name,
                "date": event_date,
                "department": department,
                "venue": venue,
                "organizer": organizer,
                "abstract": abstract,
            }

            for key, val in entity_map.items():
                if val:
                    e = ExtractedEntity(
                        document_id=doc.id,
                        entity_type=key,
                        entity_value=val,
                        confidence=0.9
                    )
                    db.session.add(e)
            db.session.commit()

            print(f"[Orchestrator] ✅ Processed '{title.strip()}' ({category}, {classified_dept})")
            print(f"[Orchestrator] 🧩 Abstract: {abstract[:120]}...")

        except Exception as e:
            doc.status = "failed"
            doc.last_error = str(e)
            db.session.commit()
            print(f"[Orchestrator] ❌ Failed to process doc {doc_id}: {e}")
