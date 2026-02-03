import pandas as pd

df = pd.read_csv("data/raw/prompts.csv")  # your original CSV
print(df.columns)
print(df.head())