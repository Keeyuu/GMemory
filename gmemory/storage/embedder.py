"""Embedding providers for GMemory."""

import logging
from typing import List, Optional

import numpy as np

from gmemory.config import config

logger = logging.getLogger(__name__)


class Embedder:
    """Interface for embedding providers."""

    @property
    def dimension(self) -> int:
        """Return the embedding dimension."""
        raise NotImplementedError

    def embed(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        raise NotImplementedError

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        return [self.embed(text) for text in texts]

    def to_blob(self, embedding: List[float]) -> bytes:
        """Convert embedding to binary blob for sqlite-vec storage."""
        return np.array(embedding, dtype=np.float32).tobytes()


class NoOpEmbedder(Embedder):
    """Fallback embedder that returns zero vectors."""

    def __init__(self) -> None:
        self._dimension = config.embedding_dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed(self, text: str) -> List[float]:
        return [0.0] * self._dimension


class FastEmbedder(Embedder):
    """FastEmbed-based local embedding provider.

    Uses ONNX runtime for efficient CPU inference without PyTorch.
    """

    # Model registry: alias -> (model_id, dimension)
    MODELS = {
        "bge-small": ("BAAI/bge-small-en-v1.5", 384),
        "bge-base": ("BAAI/bge-base-en-v1.5", 768),
        "all-minilm": ("sentence-transformers/all-MiniLM-L6-v2", 384),
        "nomic": ("nomic-ai/nomic-embed-text-v1.5", 768),
    }

    def __init__(
        self,
        model_name: str = "bge-small",
        cache_dir: Optional[str] = None,
    ) -> None:
        """Initialize FastEmbed model.

        Args:
            model_name: Model alias from MODELS registry or full HuggingFace model ID
            cache_dir: Directory to cache downloaded models
        """
        # Resolve model alias or use as-is
        if model_name in self.MODELS:
            model_id, self._dimension = self.MODELS[model_name]
        else:
            # Assume it's a full model ID, use config dimension
            model_id = model_name
            self._dimension = config.embedding_dimension

        try:
            from fastembed import TextEmbedding

            self._model = TextEmbedding(model_name=model_id, cache_dir=cache_dir)
            logger.info(f"Loaded FastEmbed model: {model_id} (dim={self._dimension})")
        except Exception as e:
            logger.error(f"Failed to load FastEmbed model '{model_id}': {e}")
            raise

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        embeddings = list(self._model.embed([text]))
        return list(embeddings[0])

    def embed_batch(self, texts: List[str], batch_size: int = 256) -> List[List[float]]:
        """Generate embeddings for multiple texts efficiently.

        Args:
            texts: List of texts to embed
            batch_size: Batch size for processing

        Returns:
            List of embeddings
        """
        embeddings = self._model.embed(texts, batch_size=batch_size)
        return [list(v) for v in embeddings]


def get_embedder() -> Embedder:
    """Factory function to get the configured embedder."""
    provider = config.embedding_provider

    if provider == "fastembed":
        try:
            embedder = FastEmbedder(
                model_name=config.embedding_model,
                cache_dir=config.embedding_cache_dir,
            )
            # Validate dimension consistency
            if embedder.dimension != config.embedding_dimension:
                logger.warning(
                    f"Embedding dimension mismatch: config={config.embedding_dimension}, "
                    f"model={embedder.dimension}. Update config.toml [embedding.dimension] "
                    f"to {embedder.dimension} to match the selected model."
                )
            return embedder
        except Exception as e:
            logger.warning(
                f"FastEmbed initialization failed: {e}, falling back to NoOpEmbedder"
            )
            return NoOpEmbedder()
    elif provider == "noop":
        return NoOpEmbedder()
    else:
        raise ValueError(f"Unsupported embedding provider: {provider}")


def is_valid_embedding(embedding: Optional[List[float]], expected_dim: int) -> bool:
    """Check if embedding is valid (not None, not all zeros, correct dimension).

    Args:
        embedding: Embedding vector to validate.
        expected_dim: Expected dimension.

    Returns:
        True if embedding is valid and usable for search.
    """
    if embedding is None:
        return False
    if len(embedding) != expected_dim:
        return False
    # Check if all zeros (NoOpEmbedder output)
    if all(v == 0.0 for v in embedding):
        return False
    return True
