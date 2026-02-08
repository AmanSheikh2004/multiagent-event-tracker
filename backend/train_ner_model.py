"""
train_ner_model.py

Train NER model using the converted Label Studio data.
The NER model handles all entity extraction including:
- EVENT_NAME, DATE, VENUE, ORGANIZER, DEPARTMENT
- CATEGORY (as an entity)
- DOC_TYPE (as an entity)
- ABSTRACT (for reports)

Usage:
    python train_ner_model.py --data training_data/ner_training_data.json \
                              --output-dir backend/ml_models/ner_model \
                              --epochs 5
"""

import json
import argparse
from pathlib import Path
from typing import List, Dict
import torch
from torch.utils.data import Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForTokenClassification,
    TrainingArguments,
    Trainer,
    DataCollatorForTokenClassification
)
from sklearn.model_selection import train_test_split
import numpy as np

# -------------------------
# Constants
# -------------------------
NER_LABELS = [
    'O',
    'B-EVENT_NAME', 'I-EVENT_NAME',
    'B-DATE', 'I-DATE',
    'B-VENUE', 'I-VENUE',
    'B-ORGANIZER', 'I-ORGANIZER',
    'B-DEPARTMENT', 'I-DEPARTMENT',
    'B-ABSTRACT', 'I-ABSTRACT',
    'B-CATEGORY', 'I-CATEGORY',
    'B-DOC_TYPE', 'I-DOC_TYPE'
]

DEFAULT_MODEL = 'bert-base-uncased'


# -------------------------
# NER Dataset
# -------------------------
class NERDataset(Dataset):
    def __init__(self, data: List[Dict], tokenizer, label_to_id: Dict[str, int]):
        self.data = data
        self.tokenizer = tokenizer
        self.label_to_id = label_to_id
        
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        item = self.data[idx]
        tokens = item['tokens']
        ner_tags = item['ner_tags']
        
        # Tokenize with word-level alignment
        encoding = self.tokenizer(
            tokens,
            is_split_into_words=True,
            padding='max_length',
            truncation=True,
            max_length=512,
            return_tensors='pt'
        )
        
        # Align labels with subword tokens
        labels = []
        word_ids = encoding.word_ids(batch_index=0)
        previous_word_idx = None
        
        for word_idx in word_ids:
            if word_idx is None:
                labels.append(-100)  # Special tokens
            elif word_idx != previous_word_idx:
                labels.append(ner_tags[word_idx])
            else:
                # For subword tokens, use -100 (ignore)
                labels.append(-100)
            previous_word_idx = word_idx
        
        return {
            'input_ids': encoding['input_ids'].squeeze(),
            'attention_mask': encoding['attention_mask'].squeeze(),
            'labels': torch.tensor(labels, dtype=torch.long)
        }


# -------------------------
# Helper Functions
# -------------------------
def load_json_data(filepath: str) -> List[Dict]:
    """Load training data from JSON file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def create_datasets(data: List[Dict], tokenizer, label_to_id: Dict[str, int], test_size: float = 0.2):
    """Split data and create train/validation datasets"""
    if len(data) < 10:
        print("⚠️  WARNING: Very small dataset. Using 90/10 split.")
        test_size = 0.1
    
    train_data, val_data = train_test_split(data, test_size=test_size, random_state=42)
    
    train_dataset = NERDataset(train_data, tokenizer, label_to_id)
    val_dataset = NERDataset(val_data, tokenizer, label_to_id)
    
    return train_dataset, val_dataset


def compute_metrics(pred):
    """Compute metrics for NER evaluation"""
    predictions, labels = pred
    predictions = np.argmax(predictions, axis=2)
    
    # Remove ignored index (special tokens)
    true_predictions = []
    true_labels = []
    
    for prediction, label in zip(predictions, labels):
        for pred_id, label_id in zip(prediction, label):
            if label_id != -100:
                true_predictions.append(pred_id)
                true_labels.append(label_id)
    
    # Calculate accuracy
    accuracy = sum(p == l for p, l in zip(true_predictions, true_labels)) / len(true_labels)
    
    return {'accuracy': accuracy}


# -------------------------
# Training Function
# -------------------------
def train_ner_model(
    train_data: List[Dict],
    output_dir: str,
    base_model: str = DEFAULT_MODEL,
    epochs: int = 3,
    batch_size: int = 8,
    learning_rate: float = 2e-5
):
    """Train NER model"""
    print("\n" + "=" * 70)
    print("Training NER Model")
    print("=" * 70)
    
    # Create label mapping
    label_to_id = {label: idx for idx, label in enumerate(NER_LABELS)}
    id_to_label = {idx: label for label, idx in label_to_id.items()}
    
    # Load tokenizer and model
    print(f"\n📥 Loading base model: {base_model}")
    tokenizer = AutoTokenizer.from_pretrained(base_model)
    model = AutoModelForTokenClassification.from_pretrained(
        base_model,
        num_labels=len(NER_LABELS),
        id2label=id_to_label,
        label2id=label_to_id
    )
    
    # Create datasets
    print(f"\n📊 Splitting data: {len(train_data)} examples")
    train_dataset, val_dataset = create_datasets(train_data, tokenizer, label_to_id)
    print(f"   - Training: {len(train_dataset)} examples")
    print(f"   - Validation: {len(val_dataset)} examples")
    
    # Training arguments
    # Note: Use eval_strategy for transformers >= 4.19, evaluation_strategy for older versions
    import transformers
    transformers_version = tuple(int(x) for x in transformers.__version__.split('.')[:2])
    
    training_args_dict = {
        'output_dir': output_dir,
        'learning_rate': learning_rate,
        'per_device_train_batch_size': batch_size,
        'per_device_eval_batch_size': batch_size,
        'num_train_epochs': epochs,
        'weight_decay': 0.01,
        'save_strategy': 'epoch',
        'save_total_limit': 2,
        'load_best_model_at_end': True,
        'metric_for_best_model': 'accuracy',
        'logging_steps': 10,
        'push_to_hub': False,
    }
    
    # Add version-specific parameters
    if transformers_version >= (4, 19):
        training_args_dict['eval_strategy'] = 'epoch'
        training_args_dict['report_to'] = 'none'
    else:
        training_args_dict['evaluation_strategy'] = 'epoch'
        training_args_dict['report_to'] = []
    
    training_args = TrainingArguments(**training_args_dict)
    
    # Data collator
    data_collator = DataCollatorForTokenClassification(tokenizer)
    
    # Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        tokenizer=tokenizer,
        data_collator=data_collator,
        compute_metrics=compute_metrics
    )
    
    # Train
    print(f"\n🚀 Starting training for {epochs} epochs...")
    trainer.train()
    
    # Evaluate
    print("\n📊 Evaluating on validation set...")
    eval_results = trainer.evaluate()
    print(f"   Validation Accuracy: {eval_results['eval_accuracy']:.4f}")
    
    # Save
    print(f"\n💾 Saving model to: {output_dir}")
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)
    
    # Save label mapping
    label_map_path = Path(output_dir) / 'label_map.json'
    with open(label_map_path, 'w') as f:
        json.dump({'label_to_id': label_to_id, 'id_to_label': id_to_label}, f, indent=2)
    
    print("✅ NER model training complete!")
    return eval_results


# -------------------------
# Main
# -------------------------
def main():
    parser = argparse.ArgumentParser(description='Train NER model')
    parser.add_argument('--data', type=str, default='training_data/ner_training_data.json',
                       help='Path to NER training data JSON')
    parser.add_argument('--output-dir', type=str, default='backend/ml_models/ner_model',
                       help='Directory for saving trained model')
    parser.add_argument('--base-model', type=str, default=DEFAULT_MODEL,
                       help='Base model for NER')
    parser.add_argument('--epochs', type=int, default=3,
                       help='Number of training epochs')
    parser.add_argument('--batch-size', type=int, default=8,
                       help='Batch size for training')
    parser.add_argument('--learning-rate', type=float, default=2e-5,
                       help='Learning rate')
    
    args = parser.parse_args()
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 70)
    print("NER Model Training Pipeline")
    print("=" * 70)
    print(f"\nConfiguration:")
    print(f"   Data: {args.data}")
    print(f"   Output Directory: {output_dir}")
    print(f"   Base Model: {args.base_model}")
    print(f"   Epochs: {args.epochs}")
    print(f"   Batch Size: {args.batch_size}")
    print(f"   Learning Rate: {args.learning_rate}")
    
    # Load and train
    try:
        train_data = load_json_data(args.data)
        print(f"\n✅ Loaded {len(train_data)} training examples")
        
        train_ner_model(
            train_data=train_data,
            output_dir=str(output_dir),
            base_model=args.base_model,
            epochs=args.epochs,
            batch_size=args.batch_size,
            learning_rate=args.learning_rate
        )
        
        print("\n" + "=" * 70)
        print("Training Complete!")
        print("=" * 70)
        print(f"\nModel saved to: {output_dir}")
        print("\nNext steps:")
        print("1. Test the model: python test_ner_agent.py")
        print("2. Update your .env file:")
        print(f"   NER_MODEL_DIR={output_dir}")
        print("3. Restart your application to use the new model")
        
    except Exception as e:
        print(f"\n❌ Training failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()