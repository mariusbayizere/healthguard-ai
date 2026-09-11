import os

# Base directory — always correct regardless of where you run from
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Training configuration
MODEL_NAME = "Davlan/afro-xlmr-mini"
MAX_LENGTH = 128
BATCH_SIZE = 8
NUM_EPOCHS = 5
LEARNING_RATE = 2e-5
WARMUP_STEPS = 50
WEIGHT_DECAY = 0.01

# Absolute paths — never breaks
SAVE_PATH = os.path.join(BASE_DIR, "saved_model")
TRAIN_PATH = os.path.join(BASE_DIR, "dataset", "processed", "train.csv")
VAL_PATH = os.path.join(BASE_DIR, "dataset", "processed", "val.csv")
TEST_PATH = os.path.join(BASE_DIR, "dataset", "processed", "test.csv")

# AUDIT 1.3. Re-exported from dataset/labels.py rather than redefined. The
# training package may import the dataset package; the reverse is forbidden,
# because the dataset pipeline must stay importable with nothing installed.
from dataset.labels import ID_TO_LABEL, LABEL_MAP, NUM_LABELS  # noqa: E402

__all__ = ["ID_TO_LABEL", "LABEL_MAP", "MAX_LENGTH", "MODEL_NAME", "NUM_LABELS"]
