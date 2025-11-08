import re
import spacy
from dateutil import parser as dateparser

nlp = spacy.load("en_core_web_sm")

class NerAgent:
    def __init__(self):
        print("[NER Agent] Initialized with spaCy + rule-based hybrid model ✅")

    def clean_text(self, text: str):
        text = re.sub(r"\s+", " ", text)  # collapse multiple spaces/newlines
        return text.strip()

    def process(self, data):
        text = self.clean_text(data.get("raw_text", ""))
        doc = nlp(text)

        entities = []
        event_name = date = department = venue = organizer = None

        # ---------- 1️⃣ Event Name Detection ----------
        event_patterns = [
            r"(?:workshop|seminar|guest lecture|symposium|conference|orientation|training|webinar)\s+(?:on|about)\s+([A-Za-z0-9 ,:-]+)",
            r"(?:event|program|activity)\s+(?:titled|called)\s+([A-Za-z0-9 ,:-]+)"
        ]
        for pat in event_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                event_name = m.group(1).strip().title()
                entities.append(("EVENT_NAME", event_name, 0.95))
                break
        if not event_name:
            # fallback: pick the first capitalized line or title-like phrase
            title_candidates = [sent.text.strip() for sent in doc.sents if len(sent.text.split()) < 15]
            if title_candidates:
                event_name = title_candidates[0]
                entities.append(("EVENT_NAME", event_name, 0.7))

        # ---------- 2️⃣ Date Detection ----------
        for ent in doc.ents:
            if ent.label_ == "DATE" and not date:
                try:
                    parsed = dateparser.parse(ent.text, fuzzy=True).date()
                    date = str(parsed)
                    entities.append(("DATE", date, 0.9))
                except:
                    pass

        # ---------- 3️⃣ Department Detection ----------
        dept_patterns = [
            r"Department of ([A-Za-z &]+)",
            r"Dept\. of ([A-Za-z &]+)",
            r"Organized by the ([A-Za-z &]+ Department)"
        ]
        for pat in dept_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                department = m.group(1).strip().title()
                entities.append(("DEPARTMENT", department, 0.95))
                break

        # ---------- 4️⃣ Venue Detection ----------
        venue_patterns = [
            r"(?:Venue|Place|Location)\s*[:\-]\s*([A-Za-z0-9 ,.-]+)",
            r"held at ([A-Za-z0-9 ,.-]+)"
        ]
        for pat in venue_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                venue = m.group(1).strip()
                entities.append(("VENUE", venue, 0.9))
                break

        # ---------- 5️⃣ Organizer Detection ----------
        org_patterns = [
            r"Organized by\s*[:\-]?\s*([A-Za-z &.,]+)",
            r"Conducted by\s*[:\-]?\s*([A-Za-z &.,]+)"
        ]
        for pat in org_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                organizer = m.group(1).strip()
                entities.append(("ORGANIZER", organizer, 0.9))
                break

        # ---------- 🧾 Fallback cleanups ----------
        if not department:
            for ent in doc.ents:
                if ent.label_ == "ORG":
                    department = ent.text
                    entities.append(("DEPARTMENT", department, 0.7))
                    break

        return {
            "entities": entities,
            "event_name": event_name,
            "date": date,
            "department": department,
            "venue": venue,
            "organizer": organizer
        }
