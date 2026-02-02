# src/embed.pycd C:\Users\Dell\Documents
git clone https://github.com/<YOUR_USERNAME>/guardprompts.git
cd guardprompts

import pandas as pd
from sentence_transformers import SentenceTransformer
import numpy as np
import os

def main():
    # Load cleaned prompts
    df = pd.read_csv('data/processed/prompts_clean.csv')

    # Initialize embedding model
    model = SentenceTransformer('all-MiniLM-L6-v2')

    # Generate embeddings
    embeddings = model.encode(df['prompt_text'].tolist(), show_progress_bar=True)

    # Save embeddings and labels
    os.makedirs('data/processed', exist_ok=True)
    np.save('data/processed/X.npy', embeddings)
    np.save('data/processed/y.npy', df['label'].values)
    
    print(f"Embeddings saved to data/processed/X.npy and labels to y.npy")

if __name__ == "__main__":
    main()
