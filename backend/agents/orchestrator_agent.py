import traceback
from .ocr_agent import OcrAgent
from .ner_agent import NerAgent
from .categorizer_agent import CategorizerAgent
from .validator_agent import ValidatorAgent
from .tracker_agent import TrackerAgent
from models import db, Document, Event, ExtractedEntity

class OrchestratorAgent:
    def __init__(self, app=None):
        self.app = app
        self.ocr = OcrAgent()
        self.ner = NerAgent()
        self.categorizer = CategorizerAgent()
        self.validator = ValidatorAgent()
        self.tracker = TrackerAgent()

    def process_document(self, doc_id, file_path):
        try:
            doc = Document.query.get(doc_id)
            raw = self.ocr.process({'file_path':file_path})
            doc.raw_text = raw.get('raw_text')
            db.session.commit()
            ner_out = self.ner.process({'raw_text': doc.raw_text})
            for label, text, conf in ner_out.get('entities', []):
                ee = ExtractedEntity(document_id=doc.id, label=label, text=text, confidence=conf)
                db.session.add(ee)
            db.session.commit()
            cat = self.categorizer.process({'raw_text': doc.raw_text})
            ev = Event(document_id=doc.id, name=ner_out.get('event_name') or 'Unknown', department=ner_out.get('department') or 'Unknown', category=cat.get('category'))
            if ner_out.get('date'):
                ev.date = ner_out.get('date')
            db.session.add(ev); db.session.commit()
            val = self.validator.process({'event':ev})
            if val.get('status')=='needs_review':
                doc.status = 'needs_review'
            else:
                ev.validated = True
                doc.status = 'saved'
                self.tracker.update(ev)
            db.session.commit()
        except Exception as e:
            doc = Document.query.get(doc_id)
            doc.status = 'failed'
            doc.last_error = traceback.format_exc()
            db.session.commit()
