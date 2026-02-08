# ner_agent.py
"""
Enhanced Transformer-based NER Agent with integrated document categorization
- First predicts doc_type (Certificate/Report)
- Then extracts entities based on doc_type
- Certificates: skip abstract extraction
- Reports: extract all fields including abstract

Patch: ensure doc_type ALWAYS has a sensible default ('Report').
Reference original file used for patching: :contentReference[oaicite:1]{index=1}
"""

from typing import List, Dict, Any
import os
import re
from dataclasses import dataclass

import torch
from transformers import (
    AutoTokenizer,
    AutoModelForTokenClassification,
    AutoModelForSequenceClassification,
    pipeline,
    TrainingArguments,
    Trainer,
    DataCollatorForTokenClassification
)

# -------------------------
# Constants / Labels
# -------------------------
NER_MODEL_NAME = os.environ.get('NER_BASE_MODEL', 'bert-base-uncased')
NER_MODEL_DIR = os.environ.get('NER_MODEL_DIR', 'backend/ml_models/ner_model')
CAT_MODEL_NAME = os.environ.get('CAT_BASE_MODEL', 'distilroberta-base')
CAT_MODEL_DIR = os.environ.get('CAT_MODEL_DIR', 'backend/ml_models/category_model')

# NER Labels - expanded (kept same as before)
NER_LABELS = [
    'O',
    'B-EVENT_NAME', 'I-EVENT_NAME',
    'B-DATE', 'I-DATE',
    'B-VENUE', 'I-VENUE',
    'B-ORGANIZER', 'I-ORGANIZER',
    'B-DEPARTMENT', 'I-DEPARTMENT',
    'B-ABSTRACT', 'I-ABSTRACT',
    'B-CATEGORY', 'I-CATEGORY'
]

# Document types - only two for your usecase
DOC_TYPES = ['Certificate', 'Report']

# Default doc type (guaranteed fallback)
DEFAULT_DOC_TYPE = 'Report'

# Event categories (kept from the file)
EVENT_CATEGORIES = [
    'Workshop / Hands-on / Training',
    'Seminar',
    'Guest Lecture / Expert Talk',
    'Conference / Symposium',
    'Competition / Hackathon / Quiz',
    'Orientation / Induction / Welcome',
    'Research / Report / Paper Presentation',
    'General / Department Activity'
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
        cat_model_dir: str = CAT_MODEL_DIR,
        cat_base_model: str = CAT_MODEL_NAME,
        device: int = None
    ):
        """
        Initialize NER Agent with integrated categorization
        """
        # Device selection
        if device is None:
            self.device = 0 if torch.cuda.is_available() else -1
        else:
            self.device = device

        print(f"[NerAgent] Initializing on device: {'GPU' if self.device >= 0 else 'CPU'}")

        # ==================== Load Categorizer (optional) ====================
        cat_path = cat_model_dir if os.path.exists(cat_model_dir) else cat_base_model
        print(f"[NerAgent] Loading categorizer from: {cat_path}")

        try:
            self.cat_tokenizer = AutoTokenizer.from_pretrained(cat_path)
            self.cat_model = AutoModelForSequenceClassification.from_pretrained(cat_path)
            self.categorizer = pipeline(
                'text-classification',
                model=self.cat_model,
                tokenizer=self.cat_tokenizer,
                return_all_scores=True,
                device=self.device
            )
            print("[NerAgent] ✅ Categorizer loaded successfully")
        except Exception as e:
            print(f"[NerAgent] ⚠️ Categorizer load failed: {e}")
            self.categorizer = None

        # ==================== Load NER Model (required) ====================
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
        print("[NerAgent] ✅ NER model loaded successfully")

    # -------------------------
    # Document type / category prediction
    # -------------------------
    def predict_doc_type(self, text: str, title: str = '') -> Dict[str, Any]:
        """
        Predict document type and event category.
        Always returns a dict containing 'doc_type' (never None).
        """
        # Default fallback
        fallback = {
            'doc_type': DEFAULT_DOC_TYPE,
            'category': 'General / Department Activity',
            'confidence': 0.0
        }

        if not text and not title:
            return fallback

        if not self.categorizer:
            # Simple heuristic fallback (keeps default doc_type if not matched)
            sample = (title + ' ' + text).lower()
            if any(word in sample for word in ['certificate', 'certification', 'awarded', 'participant']):
                return {'doc_type': 'Certificate', 'category': 'General / Department Activity', 'confidence': 0.5}
            return fallback

        # Prepare payload
        payload = (title + '\n' + text).strip()[:512]
        try:
            outputs = self.categorizer(payload)
            if not outputs or not isinstance(outputs, list) or not outputs[0]:
                return fallback

            scores = outputs[0]
            sorted_scores = sorted(scores, key=lambda x: x['score'], reverse=True)
            top = sorted_scores[0]
            label = top.get('label', '')
            confidence = float(top.get('score', 0.0))

            # Map label index to category if possible
            label_idx = None
            try:
                label_idx = int(label.split('_')[-1])
            except Exception:
                label_idx = None

            if label_idx is not None and 0 <= label_idx < len(EVENT_CATEGORIES):
                category = EVENT_CATEGORIES[label_idx]
            else:
                category = 'General / Department Activity'

            # Heuristic doc_type detection (we still default to DEFAULT_DOC_TYPE)
            doc_type = DEFAULT_DOC_TYPE
            text_sample = payload.lower()
            if 'certificate' in text_sample or 'participant' in text_sample or 'awarded' in text_sample:
                doc_type = 'Certificate'
            # If model is extremely confident and category implies award/certificate, you could set Certificate,
            # but to be safe, we prefer explicit keywords. Keep default otherwise.
            return {
                'doc_type': doc_type,
                'category': category,
                'confidence': confidence
            }
        except Exception as e:
            print(f"[NerAgent] Categorization error: {e}")
            return fallback

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
            # Defensive slicing: ensure indices are in-bounds
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
    # Consolidation / mapping to fields
    # -------------------------
    def _consolidate_fields(
        self,
        text: str,
        preds: List[NerPrediction],
        doc_type: str
    ) -> Dict[str, Any]:
        """
        Map predicted entities to final fields. doc_type guaranteed to be a string.
        """
        out = {
            'event_name': '',
            'date': '',
            'venue': '',
            'organizer': '',
            'department': '',
            'abstract': '',
            'entities': []
        }

        out['entities'] = [p.__dict__ for p in preds]

        # Group by entity type
        by_type: Dict[str, List[NerPrediction]] = {}
        for p in preds:
            t = p.entity_type
            by_type.setdefault(t, []).append(p)

        def choose_best(candidates: List[NerPrediction]) -> NerPrediction:
            return sorted(
                candidates,
                key=lambda x: (x.score, (x.end - x.start)),
                reverse=True
            )[0]

        mapping = {
            'EVENT_NAME': ['B-EVENT_NAME', 'I-EVENT_NAME', 'EVENT_NAME'],
            'DATE': ['B-DATE', 'I-DATE', 'DATE'],
            'VENUE': ['B-VENUE', 'I-VENUE', 'VENUE'],
            'ORGANIZER': ['B-ORGANIZER', 'I-ORGANIZER', 'ORGANIZER'],
            'DEPARTMENT': ['B-DEPARTMENT', 'I-DEPARTMENT', 'DEPARTMENT'],
            'ABSTRACT': ['B-ABSTRACT', 'I-ABSTRACT', 'ABSTRACT'],
            'CATEGORY': ['B-CATEGORY', 'I-CATEGORY', 'CATEGORY'],
            'DOC_TYPE': ['B-DOC_TYPE', 'I-DOC_TYPE', 'DOC_TYPE']  # in case NER predicts doc_type spans
        }

        for field, label_variants in mapping.items():
            candidates: List[NerPrediction] = []
            for lv in label_variants:
                candidates.extend(by_type.get(lv, []))

            if candidates:
                chosen = choose_best(candidates)
                out_field = chosen.text.strip()
                if field == 'DATE':
                    iso = self._normalize_date(out_field)
                    out['date'] = iso or out_field
                elif field == 'ABSTRACT':
                    if doc_type != 'Certificate':
                        out['abstract'] = out_field
                else:
                    out[field.lower()] = out_field

        # Fallback abstract extraction for reports
        if doc_type == 'Report' and not out['abstract']:
            out['abstract'] = self._extract_abstract_fallback(text)

        return out

    # -------------------------
    # Main pipeline
    # -------------------------
    def predict(self, text: str, title: str = '') -> Dict[str, Any]:
        """
        Main prediction pipeline. Guarantees 'doc_type' key in returned dict.
        """
        print(f"[NerAgent] Starting prediction pipeline...")

        # Step 1: predict doc type / category (guaranteed to contain doc_type)
        cat_result = self.predict_doc_type(text, title)
        doc_type = (cat_result.get('doc_type') or DEFAULT_DOC_TYPE)
        category = cat_result.get('category') or 'General / Department Activity'
        confidence = float(cat_result.get('confidence', 0.0))

        print(f"[NerAgent] 📄 Document Type: {doc_type}")
        print(f"[NerAgent] 🎯 Category: {category}")
        print(f"[NerAgent] ✨ Confidence: {confidence:.2f}")

        # Step 2: extract entities
        preds = self.predict_entities(text)
        print(f"[NerAgent] 🏷️  Extracted {len(preds)} entities")

        # Step 3: consolidate
        fields = self._consolidate_fields(text, preds, doc_type)

        # Step 4: attach categorization info and ensure doc_type present
        fields['doc_type'] = doc_type
        fields['category'] = category
        fields['confidence'] = confidence

        return fields

    # -------------------------
    # Helpers
    # -------------------------
    def _extract_abstract_fallback(self, text: str) -> str:
        m = re.search(
            r'(?i)abstract\s*[:\-]?\s*\n?(.*?)(?:\n\s*\n|\Z)',
            text,
            re.DOTALL
        )
        if m:
            candidate = m.group(1).strip()
            if len(candidate.split()) > 20:
                return candidate[:2000]
        return ''

    def _normalize_date(self, text: str) -> str:
        try:
            from dateutil import parser as dateparser
            dt = dateparser.parse(text, fuzzy=True)
            return dt.date().isoformat()
        except Exception:
            return ''

    # -------------------------
    # Training wrappers (unchanged)
    # -------------------------
    def train_ner(
        self,
        train_dataset,
        val_dataset,
        output_dir: str = NER_MODEL_DIR,
        epochs: int = 3,
        batch_size: int = 8,
        learning_rate: float = 2e-5
    ):
        print(f"[NerAgent] Training NER model...")

        tokenizer = AutoTokenizer.from_pretrained(NER_MODEL_NAME)
        model = AutoModelForTokenClassification.from_pretrained(
            NER_MODEL_NAME,
            num_labels=len(NER_LABELS)
        )

        args = TrainingArguments(
            output_dir=output_dir,
            evaluation_strategy='epoch',
            learning_rate=learning_rate,
            per_device_train_batch_size=batch_size,
            per_device_eval_batch_size=batch_size,
            num_train_epochs=epochs,
            weight_decay=0.01,
            save_strategy='epoch',
            logging_steps=50,
            push_to_hub=False,
            load_best_model_at_end=True
        )

        data_collator = DataCollatorForTokenClassification(tokenizer)

        trainer = Trainer(
            model=model,
            args=args,
            train_dataset=train_dataset,
            eval_dataset=val_dataset,
            tokenizer=tokenizer,
            data_collator=data_collator
        )

        trainer.train()
        trainer.save_model(output_dir)
        print(f"[NerAgent] ✅ NER model saved to {output_dir}")

    def train_categorizer(
        self,
        train_dataset,
        val_dataset,
        output_dir: str = CAT_MODEL_DIR,
        epochs: int = 3,
        batch_size: int = 16,
        learning_rate: float = 2e-5
    ):
        print(f"[NerAgent] Training categorizer...")

        tokenizer = AutoTokenizer.from_pretrained(CAT_MODEL_NAME)
        model = AutoModelForSequenceClassification.from_pretrained(
            CAT_MODEL_NAME,
            num_labels=len(EVENT_CATEGORIES)
        )

        args = TrainingArguments(
            output_dir=output_dir,
            evaluation_strategy='epoch',
            learning_rate=learning_rate,
            per_device_train_batch_size=batch_size,
            per_device_eval_batch_size=batch_size,
            num_train_epochs=epochs,
            weight_decay=0.01,
            save_strategy='epoch',
            load_best_model_at_end=True
        )

        trainer = Trainer(
            model=model,
            args=args,
            train_dataset=train_dataset,
            eval_dataset=val_dataset,
            tokenizer=tokenizer
        )

        trainer.train()
        trainer.save_model(output_dir)
        print(f"[NerAgent] ✅ Categorizer saved to {output_dir}")
