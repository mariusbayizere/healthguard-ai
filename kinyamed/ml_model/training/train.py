import os
import sys
import pandas as pd
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    get_linear_schedule_with_warmup
)
from torch.optim import AdamW
from sklearn.metrics import accuracy_score, f1_score
import warnings
warnings.filterwarnings("ignore")

# Add parent to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from training.config import (
    MODEL_NAME, MAX_LENGTH, BATCH_SIZE, NUM_EPOCHS,
    LEARNING_RATE, WARMUP_STEPS, WEIGHT_DECAY,
    SAVE_PATH, TRAIN_PATH, VAL_PATH, NUM_LABELS, LABEL_MAP
)

# ─── DATASET CLASS ────────────────────────────────
class SymptomDataset(Dataset):
    def __init__(self, df, tokenizer, max_length):
        self.texts  = df["text"].tolist()
        self.labels = df["label_id"].tolist()
        self.tokenizer  = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        encoding = self.tokenizer(
            self.texts[idx],
            max_length=self.max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt"
        )
        return {
            "input_ids":      encoding["input_ids"].squeeze(),
            "attention_mask": encoding["attention_mask"].squeeze(),
            "labels":         torch.tensor(self.labels[idx], dtype=torch.long)
        }

# ─── EVALUATION FUNCTION ──────────────────────────
def evaluate(model, loader, device):
    model.eval()
    all_preds, all_labels = [], []
    total_loss = 0

    with torch.no_grad():
        for batch in loader:
            input_ids      = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels         = batch["labels"].to(device)

            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                labels=labels
            )
            total_loss += outputs.loss.item()
            preds = torch.argmax(outputs.logits, dim=1)
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())

    avg_loss = total_loss / len(loader)
    accuracy = accuracy_score(all_labels, all_preds)
    f1       = f1_score(all_labels, all_preds, average="weighted")
    return avg_loss, accuracy, f1

# ─── MAIN TRAINING FUNCTION ───────────────────────
def train():
    print("=" * 55)
    print("   KinyaMed — AfroXLMR Fine-Tuning")
    print("=" * 55)

    # Device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device         : {device}")
    print(f"Model          : {MODEL_NAME}")
    print(f"Epochs         : {NUM_EPOCHS}")
    print(f"Batch size     : {BATCH_SIZE}")
    print(f"Learning rate  : {LEARNING_RATE}")
    print("=" * 55)

    # Load data
    print("\nLoading dataset...")
    train_df = pd.read_csv(TRAIN_PATH)
    val_df   = pd.read_csv(VAL_PATH)
    print(f"Train examples : {len(train_df)}")
    print(f"Val examples   : {len(val_df)}")

    # Load tokenizer and model
    print(f"\nLoading {MODEL_NAME}...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model     = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME,
        num_labels=NUM_LABELS
    )
    model.to(device)
    print("Model loaded successfully!")

    # Create datasets
    train_dataset = SymptomDataset(train_df, tokenizer, MAX_LENGTH)
    val_dataset   = SymptomDataset(val_df,   tokenizer, MAX_LENGTH)

    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
    val_loader   = DataLoader(val_dataset,   batch_size=BATCH_SIZE, shuffle=False)

    # Optimizer and scheduler
    optimizer = AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
    total_steps = len(train_loader) * NUM_EPOCHS
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=WARMUP_STEPS,
        num_training_steps=total_steps
    )

    # Training loop
    print("\nStarting training...\n")
    best_val_f1   = 0
    best_val_acc  = 0

    for epoch in range(NUM_EPOCHS):
        model.train()
        total_train_loss = 0
        all_preds, all_labels = [], []

        for step, batch in enumerate(train_loader):
            input_ids      = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels         = batch["labels"].to(device)

            optimizer.zero_grad()
            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                labels=labels
            )

            loss = outputs.loss
            total_train_loss += loss.item()

            preds = torch.argmax(outputs.logits, dim=1)
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())

            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()

            if (step + 1) % 5 == 0:
                print(f"  Epoch {epoch+1} | Step {step+1}/{len(train_loader)} | Loss: {loss.item():.4f}")

        # Epoch metrics
        train_acc  = accuracy_score(all_labels, all_preds)
        train_f1   = f1_score(all_labels, all_preds, average="weighted")
        avg_train_loss = total_train_loss / len(train_loader)

        val_loss, val_acc, val_f1 = evaluate(model, val_loader, device)

        print(f"\nEpoch {epoch+1}/{NUM_EPOCHS}")
        print(f"  Train Loss : {avg_train_loss:.4f} | Train Acc : {train_acc:.4f} | Train F1 : {train_f1:.4f}")
        print(f"  Val Loss   : {val_loss:.4f}   | Val Acc   : {val_acc:.4f} | Val F1   : {val_f1:.4f}")

        # Save best model
        if val_f1 > best_val_f1:
            best_val_f1  = val_f1
            best_val_acc = val_acc
            os.makedirs(SAVE_PATH, exist_ok=True)
            model.save_pretrained(SAVE_PATH)
            tokenizer.save_pretrained(f"{SAVE_PATH}/tokenizer")
            print(f"  ✅ Best model saved! Val F1: {best_val_f1:.4f}")

        print()

    print("=" * 55)
    print("Training Complete!")
    print(f"Best Val Accuracy : {best_val_acc:.4f} ({best_val_acc*100:.1f}%)")
    print(f"Best Val F1 Score : {best_val_f1:.4f}")
    print(f"Model saved to    : {SAVE_PATH}")
    print("=" * 55)

if __name__ == "__main__":
    train()
