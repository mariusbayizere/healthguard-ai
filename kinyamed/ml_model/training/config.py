import os

# Base directory — always correct regardless of where you run from
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Training configuration
MODEL_NAME         = "Davlan/afro-xlmr-mini"
MAX_LENGTH         = 128
BATCH_SIZE         = 8
NUM_EPOCHS         = 5
LEARNING_RATE      = 2e-5
WARMUP_STEPS       = 50
WEIGHT_DECAY       = 0.01

# Absolute paths — never breaks
SAVE_PATH          = os.path.join(BASE_DIR, "saved_model")
TRAIN_PATH         = os.path.join(BASE_DIR, "dataset", "processed", "train.csv")
VAL_PATH           = os.path.join(BASE_DIR, "dataset", "processed", "val.csv")
TEST_PATH          = os.path.join(BASE_DIR, "dataset", "processed", "test.csv")

LABEL_MAP = {
    "CRITICAL": 0,
    "URGENT":   1,
    "ROUTINE":  2
}

ID_TO_LABEL = {
    0: "CRITICAL",
    1: "URGENT",
    2: "ROUTINE"
}

NUM_LABELS = 3
