import pandas as pd
from sklearn.model_selection import train_test_split
import os

def process_dataset(raw_path: str, output_dir: str):
    df = pd.read_csv(raw_path)

    # Map labels to numbers
    label_map = {"CRITICAL": 0, "URGENT": 1, "ROUTINE": 2}
    df["label_id"] = df["label"].map(label_map)

    print(f"Total examples: {len(df)}")
    print(df["label"].value_counts())

    # Split 80% train, 10% val, 10% test
    train_df, temp_df = train_test_split(df, test_size=0.2, random_state=42, stratify=df["label"])
    val_df,   test_df = train_test_split(temp_df, test_size=0.5, random_state=42, stratify=temp_df["label"])

    os.makedirs(output_dir, exist_ok=True)
    train_df.to_csv(f"{output_dir}/train.csv", index=False)
    val_df.to_csv(f"{output_dir}/val.csv",     index=False)
    test_df.to_csv(f"{output_dir}/test.csv",   index=False)

    print(f"\nSplit complete:")
    print(f"Train : {len(train_df)} examples")
    print(f"Val   : {len(val_df)} examples")
    print(f"Test  : {len(test_df)} examples")
    print(f"Saved to {output_dir}")

if __name__ == "__main__":
    process_dataset("dataset/raw/symptoms_raw.csv", "dataset/processed")
