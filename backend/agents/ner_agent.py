# ner_agent.py
"""
Enhanced NER Agent with Regex Fallback Extractors

This agent uses a two-tier approach:
1. Primary: Transformer-based NER model for entity extraction
2. Fallback: Regex patterns when NER model misses fields

Handles all entity types including:
- EVENT_NAME, DATE, VENUE, ORGANIZER, DEPARTMENT (core fields)
- CATEGORY, DOC_TYPE (document classification)

Note: ABSTRACT is handled separately, not by NER.
"""

from typing import List, Dict, Any
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import torch
from transformers import (
    AutoTokenizer,
    AutoModelForTokenClassification,
    pipeline
)

# Import OCR preprocessor
sys.path.append(str(Path(__file__).parent.parent))
from ocr_preprocessor import OCRPreprocessor

# -------------------------
# Constants / Labels
# -------------------------
NER_MODEL_NAME = os.environ.get('NER_BASE_MODEL', 'bert-base-uncased')
NER_MODEL_DIR = os.environ.get('NER_MODEL_DIR', 'backend/ml_models/ner_model')

# Default doc type (guaranteed fallback)
DEFAULT_DOC_TYPE = 'Report'

# NER Labels (ABSTRACT removed - handled separately)
NER_LABELS = [
    'O',
    'B-EVENT_NAME', 'I-EVENT_NAME',
    'B-DATE', 'I-DATE',
    'B-VENUE', 'I-VENUE',
    'B-ORGANIZER', 'I-ORGANIZER',
    'B-DEPARTMENT', 'I-DEPARTMENT',
    'B-CATEGORY', 'I-CATEGORY',
    'B-DOC_TYPE', 'I-DOC_TYPE'
]


@dataclass
class NerPrediction:
    entity_type: str
    text: str
    start: int
    end: int
    score: float


class NerAgent:
    def __init__(
        self,
        ner_model_dir: str = NER_MODEL_DIR,
        ner_base_model: str = NER_MODEL_NAME,
        device: int = None
    ):
        """Initialize NER Agent"""
        # Device selection
        if device is None:
            self.device = 0 if torch.cuda.is_available() else -1
        else:
            self.device = device

        print(f"[NerAgent] Initializing on device: {'GPU' if self.device >= 0 else 'CPU'}")

        # Load NER Model
        ner_path = ner_model_dir if os.path.exists(ner_model_dir) else ner_base_model
        print(f"[NerAgent] Loading NER model from: {ner_path}")

        self.ner_tokenizer = AutoTokenizer.from_pretrained(ner_path)
        self.ner_model = AutoModelForTokenClassification.from_pretrained(ner_path)
        self.ner_pipeline = pipeline(
            "token-classification",
            model=self.ner_model,
            tokenizer=self.ner_tokenizer,
            aggregation_strategy='simple',
            device=self.device
        )
        
        # Initialize OCR preprocessor for text cleaning
        self.ocr_preprocessor = OCRPreprocessor()
        
        print("[NerAgent] ✅ NER model loaded successfully")

    # -------------------------
    # Entity extraction
    # -------------------------
    def predict_entities(self, text: str) -> List[NerPrediction]:
        """Extract entities using NER model"""
        if not text or len(text.strip()) < 2:
            return []

        raw = self.ner_pipeline(text)
        preds: List[NerPrediction] = []

        for p in raw:
            label = p.get('entity_group') or p.get('entity')
            score = float(p.get('score', 0.0))
            start = int(p.get('start', 0))
            end = int(p.get('end', 0))
            txt = text[max(0, start):min(len(text), end)]
            preds.append(NerPrediction(
                entity_type=label,
                text=txt,
                start=start,
                end=end,
                score=score
            ))

        return preds

    # -------------------------
    # Department Normalization
    # -------------------------
    def _normalize_department(self, dept_text: str) -> str:
        """
        Normalize department text to match exact dropdown values.
        
        Valid departments (matching frontend/database):
        - AIML
        - CSE(Core)
        - CSE-DS
        - CSE-CY
        - ISE
        - ECE
        - AERO
        """
        if not dept_text:
            return ''
        
        dept_upper = dept_text.upper().strip()
        dept_clean = re.sub(r'\s+', ' ', dept_upper)
        
        # Remove common prefixes
        dept_clean = re.sub(r'^DEPARTMENT\s+OF\s+', '', dept_clean)
        dept_clean = re.sub(r'^DEPT\.?\s+OF\s+', '', dept_clean)
        
        # Exact mapping to valid dropdown values
        EXACT_DEPARTMENTS = {
            # AIML variants
            'AIML': 'AIML',
            'AI & ML': 'AIML',
            'AI&ML': 'AIML',
            'AI ML': 'AIML',
            'ARTIFICIAL INTELLIGENCE AND MACHINE LEARNING': 'AIML',
            'ARTIFICIAL INTELLIGENCE & MACHINE LEARNING': 'AIML',
            'COMPUTER SCIENCE AND ENGINEERING (ARTIFICIAL INTELLIGENCE AND MACHINE LEARNING)': 'AIML',
            'COMPUTER SCIENCE AND ENGINEERING (AI & ML)': 'AIML',
            'COMPUTER SCIENCE AND ENGINEERING (AIML)': 'AIML',
            'CSE(AI & ML)': 'AIML',
            'CSE(AIML)': 'AIML',
            'CSE (AI&ML)': 'AIML',
            'CSE ( AIML )': 'AIML',
            'CSE-AIML': 'AIML',
            
            # Aerospace variants
            'AEROSPACE': 'AERO',
            'AERO': 'AERO',
            'AERONAUTICS': 'AERO',
            'CSE(AEROSPACE)': 'AERO',
            'CSE (AEROSPACE)': 'AERO',
            'COMPUTER SCIENCE AND ENGINEERING (AEROSPACE)': 'AERO',
            'COMPUTER SCIENCE AND ENGINEERING ( AEROSPACE )': 'AERO',
            
            # Cybersecurity variants
            'CYBERSECURITY': 'CSE-CY',
            'CYBER SECURITY': 'CSE-CY',
            'CYBER': 'CSE-CY',
            'CSE-CY': 'CSE-CY',
            'CSE(CYBERSECURITY)': 'CSE-CY',
            'CSE (CYBERSECURITY)': 'CSE-CY',
            'COMPUTER SCIENCE AND ENGINEERING (CYBERSECURITY)': 'CSE-CY',
            'COMPUTER SCIENCE AND ENGINEERING ( CYBERSECURITY )': 'CSE-CY',
            'CYBER SECURITY': 'CSE-CY',
            
            # Data Science variants
            'DATA SCIENCE': 'CSE-DS',
            'DS': 'CSE-DS',
            'CSE-DS': 'CSE-DS',
            'CSE(DATA SCIENCE)': 'CSE-DS',
            'CSE (DATA SCIENCE)': 'CSE-DS',
            'COMPUTER SCIENCE AND ENGINEERING (DATA SCIENCE)': 'CSE-DS',
            'COMPUTER SCIENCE AND ENGINEERING ( DATA SCIENCE )': 'CSE-DS',
            
            # CSE Core variants
            'CSE': 'CSE(Core)',
            'CSE CORE': 'CSE(Core)',
            'CSE-CORE': 'CSE(Core)',
            'CSE (CORE)': 'CSE(Core)',
            'CSE(CORE)': 'CSE(Core)',
            'COMPUTER SCIENCE': 'CSE(Core)',
            'COMPUTER SCIENCE AND ENGINEERING': 'CSE(Core)',
            'COMPUTER SCIENCE AND ENGINEERING (CORE)': 'CSE(Core)',
            'COMPUTER SCIENCE & ENGINEERING': 'CSE(Core)',
            'CSE - CORE': 'CSE(Core)',
            'COMPUTER SCIENCE AND ENGINEERING ( CSE - CORE )': 'CSE(Core)',
            
            # ISE variants
            'ISE': 'ISE',
            'INFORMATION SCIENCE': 'ISE',
            'INFORMATION SCIENCE AND ENGINEERING': 'ISE',
            'INFORMATION SCIENCE & ENGINEERING': 'ISE',
            
            # ECE variants
            'ECE': 'ECE',
            'ELECTRONICS': 'ECE',
            'ELECTRONICS AND COMMUNICATION': 'ECE',
            'ELECTRONICS AND COMMUNICATION ENGINEERING': 'ECE',
            'ELECTRONICS & COMMUNICATION ENGINEERING': 'ECE',
        }
        
        # Direct match
        if dept_clean in EXACT_DEPARTMENTS:
            return EXACT_DEPARTMENTS[dept_clean]
        
        # Fuzzy match - check if any key is contained in the text
        for key, value in EXACT_DEPARTMENTS.items():
            if key in dept_clean or dept_clean in key:
                return value
        
        # Keyword-based fallback
        if 'AIML' in dept_clean or 'AI' in dept_clean and 'ML' in dept_clean:
            return 'AIML'
        elif 'AEROSPACE' in dept_clean or 'AERO' in dept_clean:
            return 'AERO'
        elif 'CYBERSECURITY' in dept_clean or 'CYBER' in dept_clean:
            return 'CSE-CY'
        elif 'DATA' in dept_clean and 'SCIENCE' in dept_clean:
            return 'CSE-DS'
        elif 'ISE' in dept_clean or 'INFORMATION' in dept_clean:
            return 'ISE'
        elif 'ECE' in dept_clean or 'ELECTRONICS' in dept_clean:
            return 'ECE'
        elif 'CSE' in dept_clean or 'COMPUTER SCIENCE' in dept_clean:
            return 'CSE(Core)'
        
        # If nothing matched, return empty (orchestrator will use user's department)
        return ''
    def _extract_event_name_fallback(self, text: str) -> str:
        """Fallback regex extraction for event name with aggressive patterns"""
        patterns = [
            # Pattern 1: Report/Certificate ON (most common)
            r'(?i)(?:REPORT|CERTIFICATE|REPORT\s+ON)\s+(?:ON|OF|FOR)?\s*[:\-]?\s*([A-Z][^\n]{8,150}?)(?=\s*(?:Date|Venue|Organized|Department|\n\n|$))',
            # Pattern 2: Title/Topic/Subject line
            r'(?i)(?:title|topic|subject|name of (?:the )?event)\s*[:\-]\s*([^\n]{10,150})',
            # Pattern 3: Event at beginning of line
            r'(?i)^\s*(?:event|workshop|seminar|conference|training|competition)\s*(?:name)?[:\-]?\s*([A-Z][^\n]{10,120})',
            # Pattern 4: Organized event pattern
            r'(?i)organized\s+(?:a|an)?\s*(?:event|workshop|seminar|training|meetup|session)\s+(?:on|about|for)?\s*([A-Z][^\n]{10,120})',
            # Pattern 5: On [Capitalized Title] (more strict)
            r'(?i)(?:^|\n)\s*On\s+([A-Z][A-Z\s&\-\w]{10,150})\s*(?=\n|Date|Venue)',
            # Pattern 6: Meetup/Session on
            r'(?i)(?:meetup|session|meeting|gathering)\s+on\s+([A-Z][^\n]{10,120})',
            # Pattern 7: All caps title (first line)
            r'^([A-Z][A-Z\s&\-]{8,100})(?=\n)',
            # Pattern 8: Between quotes or after colon
            r'[:"]\s*([A-Z][^\n"]{15,120}?)(?="|\n|Date)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.MULTILINE)
            if match:
                name = match.group(1).strip()
                
                # Clean up the extracted name
                name = re.sub(r'\s+', ' ', name)  # Normalize whitespace
                name = re.sub(r'^(the|a|an)\s+', '', name, flags=re.IGNORECASE)  # Remove articles
                name = name.strip('.,;:!?')  # Remove trailing punctuation
                
                # More aggressive cleaning
                name = re.sub(r'\s+(Date|Venue|Organized|Department|Report).*$', '', name, flags=re.IGNORECASE)
                name = re.sub(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}.*$', '', name)  # Remove dates at end
                name = re.sub(r'\s+\d{4}$', '', name)  # Remove year at end
                name = name.strip()
                
                # Skip if it's too generic or contains noise
                noise_patterns = [
                    r'^(event|report|certificate|document|date|venue|organized)$',  # Single generic words
                    r'^\d{4}-\d{2}-\d{2}',  # ISO dates
                    r'^page \d+',
                    r'^\d+$',  # Just numbers
                    r'^[A-Z]{1,3}$',  # Short acronyms without context
                ]
                
                is_noise = any(re.search(p, name, re.IGNORECASE) for p in noise_patterns)
                if is_noise:
                    continue
                
                # Reject very short extractions (likely fragments)
                word_count = len(name.split())
                if word_count < 2 and len(name) < 10:
                    print(f"[NerAgent][FALLBACK] Rejected short event name: '{name}'")
                    continue
                
                # Valid length check (at least 8 chars for meaningful names)
                if 8 <= len(name) <= 150:
                    print(f"[NerAgent][FALLBACK] Event name extracted: '{name}' ({word_count} words)")
                    return name
        
        return ''

    def _extract_date_fallback(self, text: str) -> str:
        """Fallback regex extraction for dates"""
        patterns = [
            r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b',
            r'\b((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})\b',
            r'\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})\b',
            r'\b(\d{4}-\d{2}-\d{2})\b',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                normalized = self._normalize_date(date_str)
                if normalized:
                    return normalized
                return date_str
        return ''

    def _extract_venue_fallback(self, text: str) -> str:
        """Fallback regex extraction for venue"""
        patterns = [
            r'(?i)(?:venue|location|place|hall|room|lab)\s*[:\-]?\s*([^\n]{5,80})',
            r'(?i)(?:held at|conducted at|organized at)\s+([^\n]{5,80})',
            r'(?i)((?:Block|Hall|Room|Lab|Auditorium|Seminar Hall)\s+[A-Z0-9\-]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                venue = match.group(1).strip()
                venue = re.sub(r'\s+', ' ', venue)
                venue = re.sub(r'[,\.;]+$', '', venue)
                if 5 <= len(venue) <= 80:
                    return venue
        return ''

    def _extract_organizer_fallback(self, text: str) -> str:
        """Fallback regex extraction for organizer"""
        patterns = [
            r'(?i)(?:organized by|organiser|organizer|conducted by|coordinated by)\s*[:\-]?\s*([^\n]{5,100})',
            r'(?i)(?:Dr\.|Prof\.|Mr\.|Ms\.|Mrs\.)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'(?i)Team\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        ]
        
        organizers = []
        for pattern in patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                org = match.group(1).strip()
                org = re.sub(r'\s+', ' ', org)
                if 3 <= len(org) <= 100 and org not in organizers:
                    organizers.append(org)
        
        return ', '.join(organizers[:3]) if organizers else ''

    def _extract_department_fallback(self, text: str) -> str:
        """Fallback regex extraction for department"""
        patterns = [
            r'(?i)department\s+of\s+computer\s+science\s+and\s+engineering\s*\(\s*artificial\s+intelligence\s+and\s+machine\s+learning\s*\)',
            r'(?i)department\s+of\s+computer\s+science\s+and\s+engineering\s*\(\s*ai\s*&?\s*ml\s*\)',
            r'(?i)department\s+of\s+computer\s+science\s+and\s+engineering\s*\(\s*aerospace\s*\)',
            r'(?i)department\s+of\s+computer\s+science\s+and\s+engineering\s*\(\s*cybersecurity\s*\)',
            r'(?i)department\s+of\s+computer\s+science\s+and\s+engineering\s*\(\s*data\s+science\s*\)',
            r'(?i)department\s+of\s+(?:computer\s+science|cse)\s*\(?core\)?',
            r'(?i)department\s+of\s+(?:information\s+science|ise)',
            r'(?i)department\s+of\s+(?:electronics|ece)',
            r'(?i)CSE\s*\(\s*AI\s*&?\s*ML\s*\)',
            r'(?i)CSE\s*\(\s*AIML\s*\)',
            r'(?i)CSE\s*\(\s*AEROSPACE\s*\)',
            r'(?i)CSE\s*\(\s*CYBERSECURITY\s*\)',
            r'(?i)CSE\s*\(\s*DATA\s+SCIENCE\s*\)',
            r'(?i)CSE[\s\-]*CORE',
            r'(?i)\b(?:AIML|AI\s*&?\s*ML)\b',
            r'(?i)\bAERO(?:SPACE)?\b',
            r'(?i)\bCYBER(?:SECURITY)?\b',
            r'(?i)\b(?:DATA\s+SCIENCE|DS)\b',
            r'(?i)\bISE\b',
            r'(?i)\bECE\b',
        ]
        
        # Exact mapping to match your database/dropdown values
        DEPARTMENT_MAPPING = {
            'AIML': 'AIML',
            'AI & ML': 'AIML',
            'AI&ML': 'AIML',
            'ARTIFICIAL INTELLIGENCE AND MACHINE LEARNING': 'AIML',
            'COMPUTER SCIENCE AND ENGINEERING (ARTIFICIAL INTELLIGENCE AND MACHINE LEARNING)': 'AIML',
            'CSE(AI & ML)': 'AIML',
            'CSE(AIML)': 'AIML',
            'CSE (AI&ML)': 'AIML',
            
            'AEROSPACE': 'AERO',
            'AERO': 'AERO',
            'CSE(AEROSPACE)': 'AERO',
            'COMPUTER SCIENCE AND ENGINEERING (AEROSPACE)': 'AERO',
            
            'CYBERSECURITY': 'CSE-CY',
            'CYBER SECURITY': 'CSE-CY',
            'CYBER': 'CSE-CY',
            'CSE(CYBERSECURITY)': 'CSE-CY',
            'COMPUTER SCIENCE AND ENGINEERING (CYBERSECURITY)': 'CSE-CY',
            
            'DATA SCIENCE': 'CSE-DS',
            'DS': 'CSE-DS',
            'CSE(DATA SCIENCE)': 'CSE-DS',
            'COMPUTER SCIENCE AND ENGINEERING (DATA SCIENCE)': 'CSE-DS',
            
            'CSE': 'CSE(Core)',
            'CSE CORE': 'CSE(Core)',
            'CSE-CORE': 'CSE(Core)',
            'CSE (CORE)': 'CSE(Core)',
            'COMPUTER SCIENCE AND ENGINEERING': 'CSE(Core)',
            'CSE - CORE': 'CSE(Core)',
            
            'ISE': 'ISE',
            'INFORMATION SCIENCE': 'ISE',
            'INFORMATION SCIENCE AND ENGINEERING': 'ISE',
            
            'ECE': 'ECE',
            'ELECTRONICS': 'ECE',
            'ELECTRONICS AND COMMUNICATION': 'ECE',
            'ELECTRONICS AND COMMUNICATION ENGINEERING': 'ECE',
        }
        
        text_upper = text.upper()
        
        # Try each pattern
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                # Get the matched text and normalize it
                dept_raw = match.group(0).strip()
                dept_upper = dept_raw.upper()
                dept_clean = re.sub(r'\s+', ' ', dept_upper)
                dept_clean = re.sub(r'DEPARTMENT\s+OF\s+', '', dept_clean)
                dept_clean = dept_clean.strip()
                
                # Try to map to standard department
                for key, value in DEPARTMENT_MAPPING.items():
                    if key in dept_clean or dept_clean in key:
                        return value
        
        # If no pattern matched, try keyword matching in the whole text
        if 'AIML' in text_upper or 'AI & ML' in text_upper or 'AI&ML' in text_upper or 'ARTIFICIAL INTELLIGENCE' in text_upper:
            return 'AIML'
        elif 'AEROSPACE' in text_upper or 'AERO' in text_upper:
            return 'AERO'
        elif 'CYBERSECURITY' in text_upper or 'CYBER SECURITY' in text_upper:
            return 'CSE-CY'
        elif 'DATA SCIENCE' in text_upper:
            return 'CSE-DS'
        elif 'ISE' in text_upper or 'INFORMATION SCIENCE' in text_upper:
            return 'ISE'
        elif 'ECE' in text_upper or 'ELECTRONICS' in text_upper:
            return 'ECE'
        elif 'CSE' in text_upper or 'COMPUTER SCIENCE' in text_upper:
            return 'CSE(Core)'
        
        # Default fallback
        return ''

    def _extract_category_fallback(self, text: str) -> str:
        """Fallback keyword-based category detection with better pattern matching"""
        text_lower = text.lower()
        
        # More comprehensive keyword patterns
        category_keywords = {
            'Workshop / Hands-on / Training': [
                'workshop', 'hands-on', 'hands on', 'training', 'masterclass',
                'bootcamp', 'skill development', 'practical session'
            ],
            'Seminar': [
                'seminar', 'webinar', 'panel discussion'
            ],
            'Guest Lecture / Expert Talk': [
                'lecture', 'expert talk', 'guest lecture', 'talk', 'speaker',
                'guest speaker', 'invited talk', 'keynote'
            ],
            'Conference / Symposium': [
                'conference', 'symposium', 'summit', 'colloquium', 'congress'
            ],
            'Competition / Hackathon / Quiz': [
                'competition', 'hackathon', 'quiz', 'challenge', 'hackfest',
                'contest', 'coding competition', 'tech fest', 'ideathon'
            ],
            'Orientation / Induction / Welcome': [
                'orientation', 'induction', 'welcome', 'fresher',
                'inauguration', 'opening ceremony'
            ],
            'Research / Report / Paper Presentation': [
                'research', 'paper presentation', 'presentation', 'thesis',
                'project presentation', 'poster presentation'
            ],
            'General / Department Activity': [
                'activity', 'appreciation', 'participation', 'certificate',
                'event', 'program', 'function', 'celebration', 'meetup',
                'gathering', 'session'
            ],
        }
        
        scores = {}
        for category, keywords in category_keywords.items():
            score = 0
            for kw in keywords:
                if kw in text_lower:
                    # Give higher weight to longer, more specific keywords
                    weight = len(kw.split())  # Multi-word phrases get more weight
                    score += weight
            
            if score > 0:
                scores[category] = score
        
        if scores:
            best_category = max(scores, key=scores.get)
            print(f"[NerAgent][FALLBACK] Category detected: '{best_category}' (score={scores[best_category]})")
            return best_category
        
        return 'General / Department Activity'

    def _extract_doc_type_fallback(self, text: str) -> str:
        """Fallback keyword-based doc type detection"""
        text_lower = text.lower()
        
        cert_keywords = ['certificate', 'certification', 'appreciation', 'participation', 'awarded', 'presented to', 'recognition']
        report_keywords = ['report', 'foss', 'submitted by', 'supervision', 'overview', 'event list', 'bachelor of technology']
        
        cert_score = sum(1 for kw in cert_keywords if kw in text_lower)
        report_score = sum(1 for kw in report_keywords if kw in text_lower)
        
        if cert_score > report_score:
            return 'Certificate'
        return 'Report'

    # -------------------------
    # Field consolidation
    # -------------------------
    def _consolidate_fields(
        self,
        text: str,
        preds: List[NerPrediction]
    ) -> Dict[str, Any]:
        """Map predicted entities to final fields with regex fallback"""
        out = {
            'event_name': '',
            'date': '',
            'venue': '',
            'organizer': '',
            'department': '',
            'category': '',
            'doc_type': '',
            'entities': []
        }

        out['entities'] = [p.__dict__ for p in preds]

        # Group by entity type
        by_type: Dict[str, List[NerPrediction]] = {}
        for p in preds:
            t = p.entity_type
            by_type.setdefault(t, []).append(p)
        
        # DEBUG: Print what entity types we actually got
        print(f"[NerAgent][DEBUG] Entity types found: {list(by_type.keys())}")
        for entity_type, entities in by_type.items():
            print(f"[NerAgent][DEBUG]   {entity_type}: {len(entities)} occurrences")
            if entities:
                # Show top 3 examples
                for i, ent in enumerate(entities[:3]):
                    print(f"[NerAgent][DEBUG]     Example {i+1}: '{ent.text}' (score={ent.score:.3f})")

        def choose_best(candidates: List[NerPrediction]) -> NerPrediction:
            """
            Select best entity with quality filtering
            - Filters out low confidence predictions
            - Filters out too-short or garbage text
            - Prefers longer, more complete extractions
            """
            # Quality filtering
            MIN_CONFIDENCE = {
                'EVENT_NAME': 0.55,  # Stricter for event names
                'DATE': 0.70,        # Dates need high confidence
                'VENUE': 0.50,
                'ORGANIZER': 0.60,
                'DEPARTMENT': 0.85,  # Departments need high confidence
                'CATEGORY': 0.60,
                'DOC_TYPE': 0.90,    # Doc type needs very high confidence
            }
            
            MIN_LENGTH = {
                'EVENT_NAME': 3,     # At least 3 characters
                'DATE': 4,           # At least "2024" or "Jan 1"
                'VENUE': 2,
                'ORGANIZER': 2,
                'DEPARTMENT': 3,
                'CATEGORY': 4,
                'DOC_TYPE': 6,       # "Report" or "Certificate"
            }
            
            # Determine field type from first candidate
            field_type = None
            for c in candidates:
                for key, variants in {
                    'EVENT_NAME': ['B-EVENT_NAME', 'I-EVENT_NAME', 'EVENT_NAME'],
                    'DATE': ['B-DATE', 'I-DATE', 'DATE'],
                    'VENUE': ['B-VENUE', 'I-VENUE', 'VENUE'],
                    'ORGANIZER': ['B-ORGANIZER', 'I-ORGANIZER', 'ORGANIZER'],
                    'DEPARTMENT': ['B-DEPARTMENT', 'I-DEPARTMENT', 'DEPARTMENT'],
                    'CATEGORY': ['B-CATEGORY', 'I-CATEGORY', 'CATEGORY'],
                    'DOC_TYPE': ['B-DOC_TYPE', 'I-DOC_TYPE', 'DOC_TYPE']
                }.items():
                    if c.entity_type in variants:
                        field_type = key
                        break
                if field_type:
                    break
            
            min_conf = MIN_CONFIDENCE.get(field_type, 0.5)
            min_len = MIN_LENGTH.get(field_type, 2)
            
            # Filter candidates by quality
            quality_candidates = []
            for c in candidates:
                text = c.text.strip()
                
                # Skip garbage patterns
                if text in ['-', 'NA', 'N/A', '—', '–', 'None', 'nil']:
                    continue
                    
                # Skip single characters (except for meaningful ones)
                if len(text) == 1 and text not in ['A', 'I']:
                    continue
                
                # Skip pure numbers for non-date fields
                if field_type != 'DATE' and text.isdigit() and len(text) < 3:
                    continue
                
                # Check minimum confidence
                if c.score < min_conf:
                    continue
                
                # Check minimum length
                if len(text) < min_len:
                    continue
                
                quality_candidates.append(c)
            
            # If no quality candidates, return None to force fallback extraction
            if not quality_candidates:
                print(f"[NerAgent][FILTER] All {field_type} candidates filtered out (low quality)")
                return None
            
            # Return best quality candidate (score and length)
            return sorted(
                quality_candidates,
                key=lambda x: (x.score, (x.end - x.start)),
                reverse=True
            )[0]

        mapping = {
            'EVENT_NAME': ['B-EVENT_NAME', 'I-EVENT_NAME', 'EVENT_NAME'],
            'DATE': ['B-DATE', 'I-DATE', 'DATE'],
            'VENUE': ['B-VENUE', 'I-VENUE', 'VENUE'],
            'ORGANIZER': ['B-ORGANIZER', 'I-ORGANIZER', 'ORGANIZER'],
            'DEPARTMENT': ['B-DEPARTMENT', 'I-DEPARTMENT', 'DEPARTMENT'],
            'CATEGORY': ['B-CATEGORY', 'I-CATEGORY', 'CATEGORY'],
            'DOC_TYPE': ['B-DOC_TYPE', 'I-DOC_TYPE', 'DOC_TYPE']
        }

        # First pass: Extract from NER predictions with quality filtering
        for field, label_variants in mapping.items():
            candidates: List[NerPrediction] = []
            for lv in label_variants:
                candidates.extend(by_type.get(lv, []))

            if candidates:
                chosen = choose_best(candidates)
                
                # check_best might return None if all candidates were filtered out
                if chosen is None:
                    print(f"[NerAgent][MODEL] {field}: No quality candidates (all filtered)")
                    continue
                
                out_field = chosen.text.strip()

                print(f"[NerAgent][MODEL] {field}: '{out_field}' (score={chosen.score:.3f})")

                if field == 'DATE':
                    iso = self._normalize_date(out_field)
                    out['date'] = iso or out_field
                elif field == 'DEPARTMENT':
                    normalized = self._normalize_department(out_field)
                    out['department'] = normalized if normalized else out_field
                elif field == 'CATEGORY':
                    # Validate category - must be a known full category name
                    valid_categories = [
                        'Workshop / Hands-on / Training',
                        'Seminar',
                        'Guest Lecture / Expert Talk',
                        'Conference / Symposium',
                        'Competition / Hackathon / Quiz',
                        'Orientation / Induction / Welcome',
                        'Research / Report / Paper Presentation',
                        'General / Department Activity'
                    ]
                    
                    # Check if extracted text matches any valid category
                    is_valid = any(cat.lower() == out_field.lower() for cat in valid_categories)
                    
                    if is_valid:
                        out['category'] = out_field
                    else:
                        # Partial match detected (e.g., "meet" instead of full category)
                        print(f"[NerAgent][MODEL] CATEGORY: '{out_field}' is partial/invalid (rejected)")
                        # Leave empty for fallback to handle
                elif field == 'DOC_TYPE':
                    out['doc_type'] = out_field
                elif field == 'VENUE':
                    # Validate venue - reject partial extractions
                    # Check for trailing punctuation indicating incomplete extraction
                    if out_field.rstrip().endswith((',', '-', ':', ';')):
                        print(f"[NerAgent][MODEL] VENUE: '{out_field}' has trailing punctuation (rejected)")
                    # Reject very short venues
                    elif len(out_field.strip()) < 3:
                        print(f"[NerAgent][MODEL] VENUE: '{out_field}' too short (rejected)")
                    # Reject single short words
                    elif len(out_field.split()) == 1 and len(out_field) < 5:
                        print(f"[NerAgent][MODEL] VENUE: '{out_field}' too short/partial (rejected)")
                    else:
                        out['venue'] = out_field
                else:
                    out[field.lower()] = out_field


        # Second pass: Apply regex fallbacks for missing fields
        print(f"[NerAgent] 🔍 Applying fallback extraction...")

        def log_fallback(field_name, value):
            print(f"[NerAgent][FALLBACK] {field_name}: '{value}'")

        def log_missing(field_name):
            print(f"[NerAgent][MISSING] {field_name}")

        # Event Name
        if not out['event_name']:
            fallback = self._extract_event_name_fallback(text)
            if fallback:
                out['event_name'] = fallback
                log_fallback("EVENT_NAME", fallback)
            else:
                log_missing("EVENT_NAME")

        # Date
        if not out['date']:
            fallback = self._extract_date_fallback(text)
            if fallback:
                out['date'] = fallback
                log_fallback("DATE", fallback)
            else:
                log_missing("DATE")

        # Venue
        if not out['venue']:
            fallback = self._extract_venue_fallback(text)
            if fallback:
                out['venue'] = fallback
                log_fallback("VENUE", fallback)
            else:
                log_missing("VENUE")

        # Organizer
        if not out['organizer']:
            fallback = self._extract_organizer_fallback(text)
            if fallback:
                out['organizer'] = fallback
                log_fallback("ORGANIZER", fallback)
            else:
                log_missing("ORGANIZER")

        # Department
        if not out['department']:
            fallback = self._extract_department_fallback(text)
            if fallback:
                out['department'] = fallback
                log_fallback("DEPARTMENT", fallback)
            else:
                log_missing("DEPARTMENT")

        # Normalize Department if exists
        if out['department']:
            normalized_dept = self._normalize_department(out['department'])
            if normalized_dept and normalized_dept != out['department']:
                print(f"[NerAgent][NORMALIZED] DEPARTMENT → '{normalized_dept}'")
                out['department'] = normalized_dept

        # Category
        if not out['category']:
            fallback = self._extract_category_fallback(text)
            if fallback:
                out['category'] = fallback
                log_fallback("CATEGORY", fallback)
            else:
                log_missing("CATEGORY")

        # Doc Type
        if not out['doc_type']:
            fallback = self._extract_doc_type_fallback(text)
            if fallback:
                out['doc_type'] = fallback
                log_fallback("DOC_TYPE", fallback)
            else:
                log_missing("DOC_TYPE")


        # Determine doc_type if still missing
        if not out['doc_type']:
            out['doc_type'] = DEFAULT_DOC_TYPE

        return out

    # -------------------------
    # Main pipeline
    # -------------------------
    def predict(self, text: str, title: str = '') -> Dict[str, Any]:
        """Main prediction pipeline"""
        print(f"[NerAgent] Starting prediction pipeline...")

        # Extract entities
        preds = self.predict_entities(text)
        print(f"[NerAgent] 🏷️  Extracted {len(preds)} entities from NER model")

        # Consolidate fields (with fallbacks)
        fields = self._consolidate_fields(text, preds)

        print(f"[NerAgent] 📄 Document Type: {fields['doc_type']}")
        print(f"[NerAgent] 🎯 Category: {fields['category']}")

        return fields

    # -------------------------
    # Helpers
    # -------------------------
    def _normalize_date(self, text: str) -> str:
        """Normalize date string to ISO format with incomplete year fixing"""
        if not text:
            return ''
        
        try:
            # Fix incomplete years (202 -> 2024, 199 -> 1999, etc.)
            import re
            from datetime import datetime
            
            # Pattern: incomplete 3-digit year
            incomplete_year_pattern = r'\b(19|20)(\d)\b'
            match = re.search(incomplete_year_pattern, text)
            if match:
                # Get current year to guess missing digit
                current_year = datetime.now().year
                decade = match.group(1)  # "19" or "20"
                
                if decade == "20":
                    # For 2000s, guess based on current year
                    # If we're in 2026, "202" likely means 2024 or 2025
                    digit = match.group(2)  # The single digit
                    # Try 2020-2029
                    guessed_year = f"202{digit}"
                    text = re.sub(incomplete_year_pattern, guessed_year, text, count=1)
                    print(f"[NerAgent] Fixed incomplete year: 202{digit} -> {guessed_year}")
                elif decade == "19":
                    # For 1900s, likely means 1990s
                    digit = match.group(2)
                    guessed_year = f"199{digit}"
                    text = re.sub(incomplete_year_pattern, guessed_year, text, count=1)
                    print(f"[NerAgent] Fixed incomplete year: 199{digit} -> {guessed_year}")
            
            # Now parse with dateutil
            from dateutil import parser as dateparser
            dt = dateparser.parse(text, fuzzy=True)
            return dt.date().isoformat()
        except Exception as e:
            print(f"[NerAgent] Date parsing failed for '{text}': {e}")
            return ''