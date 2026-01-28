"""Pydantic models for document handling and knowledge management"""

from pydantic import BaseModel


class DocumentMetadata(BaseModel):
    title: str
    path: str
    category: str
    domain: str
    filename: str


class DocumentContent(BaseModel):
    metadata: DocumentMetadata
    content: str
    word_count: int
