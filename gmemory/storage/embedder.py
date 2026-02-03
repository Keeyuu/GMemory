import ollama
import socket
import os
from urllib.parse import urlparse
from typing import List
from gmemory.config import config


class Embedder:
    """Interface for embedding providers."""

    def embed(self, text: str) -> List[float]:
        raise NotImplementedError


class NoOpEmbedder(Embedder):
    """Fallback embedder that returns zero vectors."""

    def __init__(self):
        self.dimension = config.embedding_dimension

    def embed(self, text: str) -> List[float]:
        return [0.0] * self.dimension


class OllamaEmbedder(Embedder):
    """Ollama-based embedding provider."""

    def __init__(self):
        self.model = config.embedding_model

    @staticmethod
    def is_available() -> bool:
        """Check if Ollama server is reachable."""
        try:
            host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
            if "://" not in host:
                host = f"http://{host}"
            parsed = urlparse(host)
            hostname = parsed.hostname or "127.0.0.1"
            port = parsed.port or 11434

            with socket.create_connection((hostname, port), timeout=0.2):
                return True
        except (OSError, ValueError):
            return False

    def embed(self, text: str) -> List[float]:
        """Generates an embedding for the given text using Ollama."""
        response = ollama.embeddings(model=self.model, prompt=text)
        return response["embedding"]


def get_embedder() -> Embedder:
    """Factory function to get the configured embedder."""
    if config.embedding_provider == "ollama":
        if OllamaEmbedder.is_available():
            return OllamaEmbedder()
        return NoOpEmbedder()
    else:
        # Fallback to Ollama or raise error
        raise ValueError(f"Unsupported embedding provider: {config.embedding_provider}")
