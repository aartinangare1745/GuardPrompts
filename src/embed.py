'''import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
import os

def main():
    # Paths
    X_PATH = "data/processed/X.npy"
    EMB_PATH = "data/processed/X_emb.npy"

    # Load text data
    texts = np.load(X_PATH, allow_pickle=True)
    clean_texts = []
    for t in texts:
        if t is None:
            continue
        t = str(t).strip()
        if len(t) == 0:
            continue
        clean_texts.append(t)
    # Load embedding model
    model = SentenceTransformer("all-MiniLM-L6-v2")

    embeddings = model.encode(
        clean_texts,
        batch_size=32,
        show_progress_bar=True
    )

    os.makedirs("data/processed", exist_ok=True)
    np.save(EMB_PATH, embeddings)

    print("Embeddings saved:", embeddings.shape)

if __name__ == "__main__":
    main()

import pandas as pd
from sentence_transformers import SentenceTransformer
import numpy as np
from tqdm import tqdm
import os

def main():
    # Load cleaned prompts
    df = pd.read_csv('data/raw/prompts.csv')

    # Initialize embedding model
    model = SentenceTransformer('all-MiniLM-L6-v2')

    # Generate embeddings
    embeddings = []
    for text in tqdm(df['prompt_text']):
        emb = model.encode(text)
        embeddings.append(emb)
    
    embeddings = np.array(embeddings)
    

    # Save embeddings and labels
    os.makedirs('data/processed', exist_ok=True)
    np.save('data/processed/X.npy', embeddings)
    np.save("data/processed/y.npy", df['label'].values)
    np.save("data/processed/embeddings.npy", embeddings)

    
    print(f"Embeddings saved to data/processed/X.npy and labels to y.npy")

if __name__ == "__main__":
    main()
'''
import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
import os

def main():
    DATA_PATH = "data/processed/prompts_clean.csv"
    EMB_PATH = "data/processed/X_emb.npy"
    Y_PATH = "data/processed/y.npy"

    df = pd.read_csv(DATA_PATH)

    texts = df["prompt_text"].astype(str).tolist()
    labels = df["label"].values

    model = SentenceTransformer("all-MiniLM-L6-v2")

    embeddings = model.encode(
        texts,
        batch_size=32,
        show_progress_bar=True
    )

    os.makedirs("data/processed", exist_ok=True)

    np.save(EMB_PATH, embeddings)
    np.save(Y_PATH, labels)

    print("Embeddings shape:", embeddings.shape)
    print("Labels shape:", labels.shape)

if __name__ == "__main__":
    main()

'''
Batches: 100%|████████████████████████████████████████████████████████████████████████████████████████| 145/145 [01:11<00:00,  2.04it/s]
Embeddings shape: (4616, 384)
Labels shape: (4616,)
'''