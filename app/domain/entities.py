
#basic chunking

#thisis for data classes, which are a way to define classes that are primarily used to store data. The @dataclass decorator automatically generates special methods for the class, such as __

import datetime
from uuid import UUID, uuid4
from dataclasses import dataclass
from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class Document():  
    id: UUID
    title: str
    content: str
    created_at: datetime

    @staticmethod
    def create(title: str, content: str) -> "Document":        
        return Document(id = uuid4(),    title = title.strip(),  content = content,    created_at = utc_now())
        
        

@dataclass(frozen=True, slots=True)
class Chunk():
    id: UUID
    document_id: UUID
    index: int
    text: str
    start_char: int #inclusive
    end_char: int #exclusive
    created_at: datetime
    
    @staticmethod
    def create(document_id: UUID,   index: int,    text: str,   start_char: int,    end_char: int) -> "Chunk":        
        return Chunk(id = uuid4(), document_id = document_id, index = index, text = text, start_char = start_char, end_char = end_char, created_at = utc_now())