from app.domain.interfaces import EmbedderInterface
from openai import OpenAI
#from sentence_transformers import SentenceTransformer

class OpenAIEmbedder(EmbedderInterface):
    def __init__(
        self,
        api_key: str,
        model_name: str = "text-embedding-3-small",
        dimensions: int = 384,
    ):
        if not api_key or not api_key.strip():
            raise ValueError("OpenAI API key is required.")

        if dimensions <= 0:
            raise ValueError("Dimensions must be greater than 0.")

        self.client = OpenAI(api_key=api_key) 
        self.model_name = model_name
        self.dimensions = dimensions

    def embed_text(self, text: str) -> list[float]:
        cleaned_text = (text or "").strip()
        if not cleaned_text:
            raise ValueError("Text cannot be empty.")

        response = self.client.embeddings.create(
            model=self.model_name,
            input=cleaned_text,
            dimensions=self.dimensions,
        )
        #print(f"Embedding response: {response}")
        return response.data[0].embedding


'''
class SentenceTransformerEmbedder(EmbedderInterface):
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):        
        self.model = SentenceTransformer(model_name)
    
    def embed_text(self, text: str) -> list[float]:
        cleaned_text = (text or "").strip()
        if not cleaned_text:
            raise ValueError("Text cannot be empty.")
        
        embedding = self.model.encode(cleaned_text)
        
        return embedding.tolist()
'''