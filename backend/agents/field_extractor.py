"""
backend/agents/field_extractor.py

Robust multi-strategy field extraction agent.
Extracts: event_name, date, department, venue, organizer, abstract, category, doc_type
"""

import re
from datetime import datetime, date
from dateutil import parser as dateparser


class RobustFieldExtractor:
    def __init__(self):
        print("[Field Extractor] 🔍 Initialized with multi-strategy extraction")
        
        # Department patterns with variations
        self.dept_patterns = {
            "AIML": [
                r"\bAIML\b",
                r"\bAI\s*&\s*ML\b",
                r"Artificial\s+Intelligence\s+(?:and|&)?\s*Machine\s+Learning",
                r"CSE[\s\-]*AIML",
                r"Computer\s+Science.*?AIML",
                r"Dept\.?\s+of\s+AIML"
            ],
            "CSE(Core)": [
                r"\bCSE\b(?!\s*[-\(])",  # CSE not followed by dash or parenthesis
                r"Computer\s+Science\s+(?:and|&)?\s*Engineering(?!\s*[-\(])",  # CSE not followed by specialization
                r"CSE\s*Core",
                r"CSE\s*-\s*Core",
                r"Department\s+of\s+Computer\s+Science\s+(?:and\s+)?Engineering$"  # Must end here
            ],
            "CSE-DS": [
                r"CSE[\s\-]*DS",
                r"CSE[\s\-]*Data\s+Science",
                r"Computer\s+Science.*?Data\s+Science",
                r"Data\s+Science\s+(?:and|&)?\s*Engineering"
            ],
            "CSE-CY": [
                r"CSE[\s\-]*CY",
                r"CSE[\s\-]*Cyber",
                r"Computer\s+Science.*?Cyber",
                r"Cyber\s+Security\s+(?:and|&)?\s*Engineering"
            ],
            "ISE": [
                r"\bISE\b",
                r"Information\s+Science\s+(?:and|&)?\s*Engineering",
                r"IS\s*&\s*E",
                r"Department\s+of\s+Information\s+Science"
            ],
            "ECE": [
                r"\bECE\b",
                r"Electronics\s+(?:and|&)?\s*Communication",
                r"E\s*&\s*C\s*E",
                r"CSE[\s\-]*EC",
                r"Computer\s+Science.*?Electronics",
                r"Department\s+of\s+Electronics"
            ],
            "AERO": [
                r"\bAERO\b",
                r"Aeronautical\s+Engineering",
                r"Aerospace\s+Engineering",
                r"Department\s+of\s+Aeronautical"
            ]
        }
        
        # Event type patterns
        self.event_patterns = {
            "Workshop": [
                r"\bworkshop\b",
                r"hands[\s-]*on\s+(?:session|training)",
                r"training\s+(?:session|program|workshop)",
                r"practical\s+session"
            ],
            "Seminar": [
                r"\bseminar\b",
                r"lecture\s+series",
                r"talk\s+on"
            ],
            "Guest Lecture": [
                r"guest\s+lecture",
                r"invited\s+(?:talk|lecture)",
                r"expert\s+(?:session|talk)",
                r"guest\s+speaker"
            ],
            "Conference": [
                r"\bconference\b",
                r"symposium",
                r"summit",
                r"proceedings"
            ],
            "Competition": [
                r"\bcompetition\b",
                r"\bcontest\b",
                r"hackathon",
                r"coding\s+challenge",
                r"\bquiz\b"
            ],
            "Orientation": [
                r"orientation",
                r"induction",
                r"welcome\s+program"
            ]
        }
        
        # Certificate detection (high priority)
        self.cert_patterns = [
            r"certificate\s+of\s+(?:achievement|completion|participation|appreciation)",
            r"this\s+is\s+to\s+certify",
            r"(?:awarded|presented)\s+to",
            r"has\s+successfully\s+completed",
            r"is\s+hereby\s+certified",
            r"certifies\s+that"
        ]

    def extract_all_fields(self, text: str, filename: str = "") -> dict:
        """
        Main extraction method - returns all fields.
        Returns dict with: doc_type, event_name, date, department, venue, 
                          organizer, abstract, category, confidence
        """
        if not text or len(text.strip()) < 20:
            return self._get_default_fields()
        
        text_upper = text.upper()
        lines = [l.strip() for l in text.split("\n") if l.strip() and len(l.strip()) > 2]
        
        print(f"[Extractor] Processing {len(lines)} lines, {len(text)} chars")
        
        # Extract fields in sequence
        doc_type = self._detect_document_type(text, text_upper, lines)
        department = self._extract_department(text, text_upper, lines)
        event_name = self._extract_event_name(text, lines, doc_type)
        event_date = self._extract_date(text, lines)
        venue = self._extract_venue(text, lines)
        organizer = self._extract_organizer(text, lines)
        abstract = self._extract_abstract(text, lines, doc_type)
        category = self._extract_category(text, text_upper, doc_type)
        
        confidence = self._calculate_confidence(
            event_name, event_date, department, venue, organizer, abstract
        )
        
        result = {
            "doc_type": doc_type,
            "event_name": event_name,
            "date": event_date,
            "department": department,
            "venue": venue,
            "organizer": organizer,
            "abstract": abstract,
            "category": category,
            "confidence": confidence
        }
        
        # Log extraction summary
        print(f"[Extractor] ✅ Extraction Complete:")
        print(f"  📄 Type: {doc_type}")
        print(f"  🎯 Event: {event_name[:50]}..." if len(event_name) > 50 else f"  🎯 Event: {event_name}")
        print(f"  📅 Date: {event_date}")
        print(f"  🏢 Dept: {department}")
        print(f"  📍 Venue: {venue}")
        print(f"  👤 Organizer: {organizer}")
        print(f"  📂 Category: {category}")
        print(f"  ✨ Confidence: {confidence}")
        
        return result
    
    def _detect_document_type(self, text: str, text_upper: str, lines: list) -> str:
        """Detect Certificate vs Report with scoring system"""
        cert_score = 0
        report_score = 0
        
        # Check top section (first 30 lines)
        top_text = " ".join(lines[:30]).upper()
        
        # Certificate pattern matching
        for pattern in self.cert_patterns:
            matches = len(re.findall(pattern, text_upper))
            cert_score += matches * 3
            
            # Extra weight if in top section
            if re.search(pattern, top_text):
                cert_score += 2
        
        # Certificate keywords
        cert_keywords = ["CERTIFICATE", "CERTIFY", "AWARDED", "PRESENTED", "COMPLETION"]
        for kw in cert_keywords:
            count = text_upper.count(kw)
            cert_score += count * 2
        
        # Report indicators
        report_keywords = [
            "ABSTRACT", "INTRODUCTION", "CONCLUSION", "METHODOLOGY",
            "RESULTS", "REFERENCES", "CHAPTER", "TABLE OF CONTENTS",
            "ACKNOWLEDGEMENT", "LITERATURE REVIEW"
        ]
        for kw in report_keywords:
            count = text_upper.count(kw)
            report_score += count * 2
        
        # Document structure analysis
        if "TABLE OF CONTENTS" in text_upper or "CONTENTS" in text_upper[:500]:
            report_score += 5
        
        # Length heuristic (certificates are typically shorter)
        if len(text) < 3000:
            cert_score += 3
        elif len(text) > 10000:
            report_score += 3
        
        print(f"[Extractor] Doc Type Scores - Certificate: {cert_score}, Report: {report_score}")
        
        return "Certificate" if cert_score > report_score else "Report"
    
    def _extract_event_name(self, text: str, lines: list, doc_type: str) -> str:
        """Extract event name using multiple strategies"""
        
        # Strategy 1: Explicit labels
        label_patterns = [
            r"(?:event|title|program|activity|topic|subject|name)\s*[:\-]\s*(.+?)(?:\n|$)",
            r"(?:name\s+of\s+(?:the\s+)?(?:event|program|workshop|seminar|conference))\s*[:\-]\s*(.+?)(?:\n|$)",
        ]
        
        for pattern in label_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                title = match.group(1).strip()
                title = re.sub(r'\s+', ' ', title)
                title = title.split('\n')[0]
                if 3 <= len(title.split()) <= 20 and len(title) > 10:
                    print(f"[Extractor] Event name (labeled): {title}")
                    return title.title()
        
        # Strategy 2: Certificate-specific patterns
        if doc_type == "Certificate":
            cert_patterns = [
                r"certificate\s+of\s+\w+\s+(?:for|in|on)\s+(.+?)(?:\.|held|organized|conducted|on\s+\d)",
                r"(?:workshop|seminar|conference|training|program)\s+on\s+(.+?)(?:\.|held|organized|$)",
                r"successfully\s+completed\s+(?:the\s+)?(.+?)(?:\.|held|organized|on\s+\d)",
                r"participated\s+in\s+(?:the\s+)?(.+?)(?:\.|held|organized|on\s+\d)"
            ]
            
            for pattern in cert_patterns:
                match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
                if match:
                    title = match.group(1).strip()
                    title = re.sub(r'\s+', ' ', title)
                    title = re.sub(r'\s+on\s+\d{1,2}[\-/]\d{1,2}[\-/]\d{2,4}.*$', '', title)
                    if 3 <= len(title.split()) <= 25 and len(title) > 10:
                        print(f"[Extractor] Event name (certificate pattern): {title}")
                        return title.title()
        
        # Strategy 3: Look for large/prominent text (all caps, likely title)
        for i, line in enumerate(lines[:20]):
            words = line.split()
            if not (3 <= len(words) <= 20):
                continue
            
            # All caps lines (common for titles)
            if line.isupper() and len(line) > 15:
                # Skip common headers
                if any(skip in line for skip in ["UNIVERSITY", "DEPARTMENT", "CERTIFICATE"]):
                    continue
                print(f"[Extractor] Event name (caps line): {line}")
                return line.title()
            
            # Lines with event keywords
            if any(kw in line.upper() for kw in ["WORKSHOP", "SEMINAR", "CONFERENCE", "TRAINING", "LECTURE"]):
                print(f"[Extractor] Event name (keyword line): {line}")
                return line.title()
        
        # Strategy 4: First substantial line
        for line in lines[:15]:
            words = line.split()
            if 5 <= len(words) <= 20 and len(line) > 20:
                # Skip dates, departments, common headers
                if re.search(r'\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}', line):
                    continue
                if any(skip in line.upper() for skip in ["DEPARTMENT", "UNIVERSITY", "COLLEGE"]):
                    continue
                print(f"[Extractor] Event name (first substantial): {line}")
                return line.title()
        
        print("[Extractor] Event name: Untitled (fallback)")
        return "Untitled Event"
    
    def _extract_date(self, text: str, lines: list) -> str:
        """Extract date using multiple formats"""
        
        # Comprehensive date patterns
        date_patterns = [
            # Labeled dates
            r"(?:date|on|held\s+on|conducted\s+on|dated)\s*[:\-]?\s*(\d{1,2}[\s\-/\.]\w+[\s\-/\.]\d{2,4})",
            r"(?:date|on|held\s+on|conducted\s+on|dated)\s*[:\-]?\s*(\d{1,2}[\s\-/\.]\d{1,2}[\s\-/\.]\d{2,4})",
            # Ordinal dates (15th October 2024)
            r"(\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*[\s,]+\d{4})",
            # Month Day, Year (October 15, 2024)
            r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{1,2}[\s,]+\d{4})",
            # DD/MM/YYYY or DD-MM-YYYY
            r"(\d{1,2}[\s\-/\.]\d{1,2}[\s\-/\.]\d{4})",
            # YYYY-MM-DD (ISO format)
            r"(\d{4}[\-/]\d{1,2}[\-/]\d{1,2})"
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    parsed = dateparser.parse(match, fuzzy=True)
                    if parsed and 2000 <= parsed.year <= 2030:
                        result = parsed.date().isoformat()
                        print(f"[Extractor] Date found (pattern): {result} from '{match}'")
                        return result
                except:
                    continue
        
        # Search line by line in first 30 lines
        for line in lines[:30]:
            try:
                parsed = dateparser.parse(line, fuzzy=True)
                if parsed and 2000 <= parsed.year <= 2030:
                    result = parsed.date().isoformat()
                    print(f"[Extractor] Date found (fuzzy): {result} from '{line}'")
                    return result
            except:
                continue
        
        result = date.today().isoformat()
        print(f"[Extractor] Date: {result} (default to today)")
        return result
    
    def _extract_department(self, text: str, text_upper: str, lines: list) -> str:
        """Extract department with improved matching"""
        
        # Strategy 1: Explicit "Department of X" patterns
        dept_explicit_patterns = [
            r"department\s+of\s+([\w\s&(),]+?)(?:\s+(?:hosted|organized|conducted|presents)|[,\.\n])",
            r"dept\.?\s+of\s+([\w\s&(),]+?)(?:\s+(?:hosted|organized)|[,\.\n])",
            r"organized\s+by\s+(?:the\s+)?department\s+of\s+([\w\s&(),]+?)(?:[,\.\n])"
        ]
        
        for pattern in dept_explicit_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                dept_text = match.group(1).strip()
                normalized = self._normalize_department(dept_text)
                print(f"[Extractor] Department (explicit): {normalized} from '{dept_text}'")
                return normalized
        
        # Strategy 2: Pattern matching for codes/keywords
        for dept_code, patterns in self.dept_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    print(f"[Extractor] Department (pattern): {dept_code}")
                    return dept_code
        
        print("[Extractor] Department: General (fallback)")
        return "General"
    
    def _normalize_department(self, dept_text: str) -> str:
        """Normalize department text to standard codes"""
        dept_upper = dept_text.upper()
        
        # Priority order matters! Check specializations BEFORE core CSE
        
        # AI/ML variations (highest priority for CSE-AIML)
        if any(kw in dept_upper for kw in ["AIML", "AI & ML", "AI&ML", "CSE-AIML", "CSE AIML"]):
            return "AIML"
        
        if "ARTIFICIAL INTELLIGENCE" in dept_upper or "MACHINE LEARNING" in dept_upper:
            return "AIML"
        
        # Data Science variations
        if any(kw in dept_upper for kw in ["CSE-DS", "CSE DS", "DATA SCIENCE"]):
            return "CSE-DS"
        
        # Cyber Security variations
        if any(kw in dept_upper for kw in ["CSE-CY", "CSE CY", "CYBER"]):
            return "CSE-CY"
        
        # Electronics/Communication (before CSE check)
        if any(kw in dept_upper for kw in ["ELECTRONICS", "COMMUNICATION", "ECE", "E&CE", "CSE-EC"]):
            return "ECE"
        
        # ISE variations (before CSE check)
        if "INFORMATION SCIENCE" in dept_upper or "IS&E" in dept_upper or "ISE" in dept_upper:
            return "ISE"
        
        # AERO variations
        if any(kw in dept_upper for kw in ["AERO", "AEROSPACE", "AERONAUTICAL"]):
            return "AERO"
        
        # CSE Core - ONLY if it's pure Computer Science Engineering with NO specialization
        # This should be last to avoid false matches
        if "COMPUTER SCIENCE" in dept_upper:
            # Check if any specialization keywords exist
            specializations = ["AIML", "DATA SCIENCE", "CYBER", "ELECTRONICS", "INFORMATION"]
            has_specialization = any(spec in dept_upper for spec in specializations)
            
            if not has_specialization:
                return "CSE(Core)"
        
        # Return truncated original if no match
        return dept_text[:30]
    
    def _extract_venue(self, text: str, lines: list) -> str:
        """Extract venue/location"""
        
        venue_patterns = [
            r"(?:venue|location|place)\s*[:\-]\s*([^\n\.]+)",
            r"(?:hall|room|auditorium|lab|center|block)\s*[:\-]\s*([^\n\.]+)",
            r"(?:held|conducted|organized)\s+at\s+([^\n\.]+)",
            r"at\s+([\w\s]+(?:hall|auditorium|room|building|block|lab|center))"
        ]
        
        for pattern in venue_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                venue = match.group(1).strip()
                venue = re.sub(r'\s+', ' ', venue)
                venue = venue.split(',')[0]  # Take first part before comma
                if 2 <= len(venue.split()) <= 15 and len(venue) > 5:
                    print(f"[Extractor] Venue: {venue}")
                    return venue
        
        print("[Extractor] Venue: Not specified (fallback)")
        return "Venue not specified"
    
    def _extract_organizer(self, text: str, lines: list) -> str:
        """Extract organizer/coordinator"""
        
        organizer_patterns = [
            r"(?:organized|conducted|coordinated|hosted)\s+by\s*[:\-]?\s*([^\n\.]+)",
            r"(?:organizer|coordinator|convenor)\s*[:\-]\s*([^\n\.]+)",
            r"(?:under\s+(?:the\s+)?(?:guidance|supervision)\s+of)\s+([^\n\.]+)"
        ]
        
        for pattern in organizer_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                organizer = match.group(1).strip()
                organizer = re.sub(r'\s+', ' ', organizer)
                organizer = organizer.split(',')[0]
                if 2 <= len(organizer.split()) <= 15 and len(organizer) > 5:
                    print(f"[Extractor] Organizer: {organizer}")
                    return organizer
        
        print("[Extractor] Organizer: Not specified (fallback)")
        return "Organizer not specified"
    
    def _extract_abstract(self, text: str, lines: list, doc_type: str) -> str:
        """Extract abstract or description"""
        
        if doc_type == "Certificate":
            # For certificates, create brief description from top lines
            cert_text = " ".join(lines[:10])
            cert_text = re.sub(r'\s+', ' ', cert_text)
            result = f"Certificate document. {cert_text[:200]}..."
            print(f"[Extractor] Abstract (cert): {len(result)} chars")
            return result
        
        # Look for explicit abstract section
        abstract_patterns = [
            r"abstract\s*[:\-]?\s*\n((?:.+\n?){1,10})",
            r"summary\s*[:\-]?\s*\n((?:.+\n?){1,10})",
            r"introduction\s*[:\-]?\s*\n((?:.+\n?){1,10})"
        ]
        
        for pattern in abstract_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                abstract = match.group(1).strip()
                abstract = re.sub(r'\s+', ' ', abstract)
                if 50 <= len(abstract) <= 1000:
                    print(f"[Extractor] Abstract (labeled): {len(abstract)} chars")
                    return abstract[:500]
        
        # Fallback: Use first substantial paragraph
        paragraphs = text.split('\n\n')
        for para in paragraphs[:5]:
            para = para.strip()
            para = re.sub(r'\s+', ' ', para)
            if 50 <= len(para) <= 1000:
                print(f"[Extractor] Abstract (paragraph): {len(para)} chars")
                return para[:500]
        
        result = "Abstract not found"
        print(f"[Extractor] Abstract: {result}")
        return result
    
    def _extract_category(self, text: str, text_upper: str, doc_type: str) -> str:
        """Extract event category"""
        
        if doc_type == "Certificate":
            return "Certificate Event"
        
        # Check event type patterns
        for category, patterns in self.event_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_upper):
                    print(f"[Extractor] Category: {category}")
                    return category
        
        # Check for research indicators
        research_keywords = [
            "ABSTRACT", "METHODOLOGY", "RESULTS", "CONCLUSION",
            "REFERENCES", "LITERATURE REVIEW", "DATA ANALYSIS"
        ]
        research_score = sum(1 for kw in research_keywords if kw in text_upper)
        
        if research_score >= 3:
            print("[Extractor] Category: Research/Report")
            return "Research/Report"
        
        print("[Extractor] Category: General Event (fallback)")
        return "General Event"
    
    def _calculate_confidence(self, event_name, date_val, dept, venue, organizer, abstract) -> float:
        """Calculate extraction confidence score (0.0 to 1.0)"""
        score = 0.0
        
        if event_name and event_name != "Untitled Event":
            score += 0.25
        if date_val and date_val != date.today().isoformat():
            score += 0.20
        if dept and dept != "General":
            score += 0.20
        if venue and venue != "Venue not specified":
            score += 0.15
        if organizer and organizer != "Organizer not specified":
            score += 0.10
        if abstract and abstract != "Abstract not found":
            score += 0.10
        
        return round(min(score, 1.0), 2)
    
    def _get_default_fields(self) -> dict:
        """Return default values when extraction fails"""
        return {
            "doc_type": "Report",
            "event_name": "Untitled Event",
            "date": date.today().isoformat(),
            "department": "General",
            "venue": "Venue not specified",
            "organizer": "Organizer not specified",
            "abstract": "No content extracted",
            "category": "General Event",
            "confidence": 0.3
        }