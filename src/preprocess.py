import pandas as pd
from pathlib import Path
'''
RAW_PATH = Path("data/raw/prompts.csv")
OUT_PATH = Path("data/processed/prompts_clean.csv")

def main():
    df = pd.read_csv(RAW_PATH)

    print("Raw shape:", df.shape)
    print("Columns:", df.columns)

    #  CHANGE THIS if your column name is different
    text_col = "prompt" if "prompt" in df.columns else df.columns[0]

    df = df[[text_col]].dropna()
    df[text_col] = df[text_col].astype(str).str.strip()
    df = df[df[text_col] != ""]

    print("After cleaning:", df.shape)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_PATH, index=False)

    print("Saved to", OUT_PATH)

if __name__ == "__main__":
    main()
    
'''
import pandas as pd
import re

def clean_text(text):
    if not isinstance(text, str):
        return ""
    text = re.sub(r"\s+", " ", text)
    text = text.strip()
    return text

def main():
    df = pd.read_csv("data/raw/prompts.csv")

    df["prompt_text"] = df["prompt_text"].apply(clean_text)

    # Drop empty prompts ONLY
    df = df[df["prompt_text"] != ""]

    # IMPORTANT: label stays
    df.to_csv("data/processed/prompts_clean.csv", index=False)

    print("Saved cleaned data with labels")
    print(df["label"].value_counts())

if __name__ == "__main__":
    main()
'''
Saved cleaned data with labels
label
1    2352
0    2264
Name: count, dtype: int64
'''