import os
import sys
import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from sklearn.metrics import (
    accuracy_score, f1_score,
    precision_score, recall_score,
    classification_report, confusion_matrix
)
import warnings
warnings.filterwarnings("ignore")

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from training.config import SAVE_PATH, TEST_PATH, MAX_LENGTH, ID_TO_LABEL

def evaluate_model():
    print("=" * 55)
    print("   KinyaMed — Model Evaluation on Test Set")
    print("=" * 55)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # Load saved model
    print(f"\nLoading model from {SAVE_PATH}...")
    tokenizer = AutoTokenizer.from_pretrained(f"{SAVE_PATH}/tokenizer")
    model     = AutoModelForSequenceClassification.from_pretrained(SAVE_PATH)
    model.to(device)
    model.eval()
    print("Model loaded!")

    # Load test data
    test_df = pd.read_csv(TEST_PATH)
    print(f"Test examples: {len(test_df)}\n")

    all_preds, all_labels = [], []

    for _, row in test_df.iterrows():
        encoding = tokenizer(
            row["text"],
            max_length=MAX_LENGTH,
            padding="max_length",
            truncation=True,
            return_tensors="pt"
        )
        input_ids      = encoding["input_ids"].to(device)
        attention_mask = encoding["attention_mask"].to(device)

        with torch.no_grad():
            outputs = model(input_ids=input_ids, attention_mask=attention_mask)
            pred    = torch.argmax(outputs.logits, dim=1).item()

        all_preds.append(pred)
        all_labels.append(row["label_id"])

    # Metrics
    accuracy  = accuracy_score(all_labels, all_preds)
    f1        = f1_score(all_labels, all_preds, average="weighted")
    precision = precision_score(all_labels, all_preds, average="weighted")
    recall    = recall_score(all_labels, all_preds, average="weighted")

    print("=" * 55)
    print("BENCHMARK RESULTS")
    print("=" * 55)
    print(f"Accuracy  : {accuracy:.4f} ({accuracy*100:.1f}%)")
    print(f"F1 Score  : {f1:.4f}")
    print(f"Precision : {precision:.4f}")
    print(f"Recall    : {recall:.4f}")
    print()

    # Per class report
    label_names = [ID_TO_LABEL[i] for i in range(3)]
    print("Per-Class Report:")
    print(classification_report(
        all_labels, all_preds,
        target_names=label_names
    ))

    # Confusion matrix
    cm = confusion_matrix(all_labels, all_preds)
    print("Confusion Matrix:")
    print(f"{'':12} CRITICAL  URGENT  ROUTINE")
    for i, row in enumerate(cm):
        print(f"{label_names[i]:12} {row[0]:8} {row[1]:7} {row[2]:7}")

    # Per language breakdown
    print("\nPer-Language Accuracy:")
    for lang in ["kinyarwanda", "english", "mixed"]:
        lang_df = test_df[test_df["language"] == lang]
        if len(lang_df) == 0:
            continue
        lang_preds, lang_labels = [], []
        for _, row in lang_df.iterrows():
            encoding = tokenizer(
                row["text"],
                max_length=MAX_LENGTH,
                padding="max_length",
                truncation=True,
                return_tensors="pt"
            )
            with torch.no_grad():
                outputs = model(
                    input_ids=encoding["input_ids"].to(device),
                    attention_mask=encoding["attention_mask"].to(device)
                )
                pred = torch.argmax(outputs.logits, dim=1).item()
            lang_preds.append(pred)
            lang_labels.append(row["label_id"])
        lang_acc = accuracy_score(lang_labels, lang_preds)
        print(f"  {lang:15} : {lang_acc:.4f} ({lang_acc*100:.1f}%) — {len(lang_df)} examples")

    print("\n✅ Evaluation complete. These numbers go in your research paper.")

if __name__ == "__main__":
    evaluate_model()
