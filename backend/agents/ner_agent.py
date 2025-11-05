import re
import spacy
from dateutil import parser as dateparser
nlp = spacy.load('en_core_web_sm')

EVENT_PATTERNS = [r'(workshop on .+)', r'(seminar on .+)', r'(guest lecture on .+)', r'(symposium on .+)', r'(conference on .+)', r'(annual day .+)']

class NerAgent:
    def __init__(self):
        self.nlp = nlp

    def process(self, data):
        text = data.get('raw_text','')
        entities = []
        event_name = None; date = None; department = None
        for pat in EVENT_PATTERNS:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                event_name = m.group(1).strip()
                entities.append(('EVENT_NAME', event_name, 0.95))
                break
        doc = self.nlp(text)
        for ent in doc.ents:
            if ent.label_ == 'ORG' and not department:
                department = ent.text
                entities.append(('DEPARTMENT', department, 0.7))
            if ent.label_ == 'DATE' and not date:
                try:
                    parsed = dateparser.parse(ent.text, fuzzy=True).date()
                    date = parsed
                    entities.append(('DATE', ent.text, 0.9))
                except:
                    pass
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        if not event_name and lines:
            event_name = lines[0]
            entities.append(('EVENT_NAME', event_name, 0.6))
        return {'entities': entities, 'event_name': event_name, 'date': date, 'department': department}
