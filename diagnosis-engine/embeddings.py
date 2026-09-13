import os
import random

try:
    import openai
except ImportError:
    pass

def generate_embedding(text: str) -> list[float]:
    """Generate a 1536-dimensional embedding for the error signature."""
    api_key = os.getenv("EMBEDDING_API_KEY")
    if api_key and os.getenv("EMBEDDING_PROVIDER") == "openai":
        openai.api_key = api_key
        response = openai.embeddings.create(
            input=text,
            model="text-embedding-ada-002"
        )
        return response.data[0].embedding
    
    # Fallback to random embedding if no provider/key is set
    # Using a deterministic random seed based on text length for stability
    random.seed(len(text))
    return [random.random() for _ in range(1536)]
