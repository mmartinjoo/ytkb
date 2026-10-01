from abc import ABC, abstractmethod
from enum import Enum
from functools import lru_cache
import logging

from fastembed import TextEmbedding
from mistralai import Mistral

from ytkb.core.config import settings

logger = logging.getLogger(__name__)

class EmbedderProvider(Enum):
    MISTRAL = "MISTRAL"
    LOCAL = "LOCAL"

class Embedder(ABC):
    @abstractmethod
    def embed(self, texts: list[str]) -> list[float]: ...
    
class LocalEmbedder(Embedder):
    @lru_cache(maxsize=1)
    def get_model(self) -> TextEmbedding:
        return TextEmbedding(
            model_name="intfloat/multilingual-e5-large",
            cache_dir="/tmp/fastembed_cache",
        )
        
    def embed(self, texts: list[str]) -> list[float]:
        logger.info(f"embedding {texts}")
        return list(self.get_model().embed(texts))
    
class MistralEmbedder(Embedder):
    client: Mistral
    
    def __init__(self, api_key):
        self.client = Mistral(api_key=api_key)
        
    def embed(self, texts: list[str]) -> list[float]:
        response = self.client.embeddings.create(
            model="mistral-embed",
            inputs=texts,
        )
        return [item.embedding for item in response.data]
    
def create_embedder() -> Embedder:
    provider = EmbedderProvider(settings.embedder_provider)
    match provider:
        case EmbedderProvider.LOCAL:
            return LocalEmbedder()
        case EmbedderProvider.MISTRAL:
            return MistralEmbedder(settings.mistral_api_key)