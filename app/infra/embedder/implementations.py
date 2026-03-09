from app.domain.interfaces import EmbedderInterface
from openai import OpenAI
from sentence_transformers import SentenceTransformer


class OpenAIEmbedder(EmbedderInterface):
    def __init__(self, api_key: str, model_name: str):
        self.client = OpenAI(api_key=api_key)
        self.model_name = model_name
    
    def embed_text(self, text: str) -> list[float]:
        cleaned_text = (text or "").strip()
        if not cleaned_text:
            raise ValueError("Text cannot be empty.")
        
        response = self.client.embeddings.create(input=cleaned_text, model=self.model_name)
        
        return response.data[0].embedding

#we will use this locally for now. In the future we could add openai embedder.
# 384 dimensions. Change orm model and entity to this dimensions.
class SentenceTransformerEmbedder(EmbedderInterface):
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):        
        self.model = SentenceTransformer(model_name) #we can make this configurable later if needed. This is a good general purpose model for sentence embeddings that is also lightweight and fast.
    
    def embed_text(self, text: str) -> list[float]:
        cleaned_text = (text or "").strip()
        if not cleaned_text:
            raise ValueError("Text cannot be empty.")
        
        embedding = self.model.encode(cleaned_text)
        
        return embedding.tolist()