1. Collect & clean data
HF datasets, pandas, rapidfuzz
2. Embed & train classifier
MiniLM, scikit-learn
3. Defense pipeline
regex rules, MiniLM, LLM API
4. Serve as API
FastAPI, Pydantic, Uvicorn
5. Test with real attacks
Garak, TextAttack
6. Containerize & deploy
Docker, Render/Railway






                    TRAIN
                      │
        ┌─────────────┼─────────────┐
        │             │             │
     NeCenT        Deepest       Mindgard
      subset          662       selected examples
        │             │             │
        └─────────────┼─────────────┘
                      ↓
              Binary classifier
                      ↓
              0 = benign
              1 = attack


                    TEST
                      │
        ┌─────────────┼─────────────┐
        │             │             │
    Standard       Direct       Obfuscated
     attacks       attacks        attacks
                                  ↑
                               Mindgard


   
