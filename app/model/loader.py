from functools import lru_cache
from transformers import pipeline, AutoTokenizer
MODEL_NAME = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
MAX_ATTEMPTS = 2
MIN_LOG_LENGTH = 10  
@lru_cache(maxsize=1)
def get_model():
    ...

@lru_cache(maxsize=1)
def get_model():
    try:
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        model = pipeline(
            "text-generation",
            model=MODEL_NAME,
            torch_dtype=torch.float16,
            device_map="auto"
        )
        return model
    except Exception as e:
        print(f"⚠️ Failed to load model: {e}")
        return None