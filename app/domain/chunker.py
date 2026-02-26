from uuid import UUID, uuid4
#service that retusns a list of chunks given a text document. 
from dataclasses import dataclass
from app.domain.entities import Chunk
from typing import List

@dataclass(frozen=True, slots=True)
class ConfigChunker:
    size: int = 1000
    overlap: int = 200
    strip: bool = True



class Chunker:
    def __init__(self, config: ConfigChunker | None = None) -> None:
        self.config = config or ConfigChunker()
    
    def chunk_document(self, document_id: UUID, text: str):
        if text is None:
            raise ValueError("text cannot be None")
        
        if self.config.strip:
            text = text.strip()
        
        if self.config.size <= 0:
            raise ValueError("size must be greater than 0")
        if self.config.overlap < 0:
            raise ValueError("overlap cannot be negative")
        if self.config.overlap >= self.config.size:
            raise ValueError("overlap must be less than size")        

        if not text:
            return []

        #config validated, text not empty, let's chunk a little:
        chunks: List[Chunk] = []
        #need 2 pointers, x, y to define the chunk boundaries.
        x = 0 #starting point and increasing
        y = self.config.size #end point and increasing, but always ahead of x by size
        index = 0 #chunk index, starting at 0 and increasing by 1 for each chunk
        
        N = len(text)
        
        while x < N:
            #compute y:
            y = min(x + self.config.size, N)
            chunk_text = text[x:y]
            
            new_chunk = Chunk.create(
                #id and created_at are set automatically in the create method of the Chunk class
                document_id = document_id,
                index = index, 
                text = chunk_text,
                start_char = x,
                end_char = y                                
            )
            
            chunks.append(new_chunk)
            
            #update pointers
            
            if y >= N:
                break #we're done, no more chunks
            
            x = y - self.config.overlap 
            index += 1
            
        return chunks


if __name__ == "__main__":    #test the chunker with a simple example:
    config = ConfigChunker(size=50, overlap=20)
    chunker = Chunker(config)
    
    document_id = uuid4()
    text = "This is a test document to be chunked into smaller pieces. I sometimes fly high and people call me Johnny. I like to eat pizza and watch movies. Love is in the air."
    
    chunks = chunker.chunk_document(document_id, text)
    
    for chunk in chunks:
        print(f"Chunk {chunk.index}: '{chunk.text}' (chars {chunk.start_char}-{chunk.end_char})")
