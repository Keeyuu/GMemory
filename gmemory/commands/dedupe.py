"""Dedupe and merge commands for GMemory.

Provides functionality to find and handle duplicate or similar memories.
Supports multiple deduplication strategies:
- vector: Semantic similarity using embeddings (default)
- simhash: Locality-sensitive hashing for near-duplicate text
- minhash: Jaccard similarity estimation using shingles
"""

import hashlib
import time
from typing import List, Optional, Dict, Any, Tuple, Set
from dataclasses import dataclass
from collections import defaultdict

from gmemory.storage.database import MemoryDatabase
from gmemory.storage.embedder import get_embedder, NoOpEmbedder, is_valid_embedding
from gmemory.config import config
from gmemory.models import Memory


# ============================================================================
# SimHash Implementation
# ============================================================================


class SimHash:
    """SimHash for near-duplicate text detection.

    SimHash is a locality-sensitive hashing technique that produces
    similar hashes for similar documents. It's efficient for finding
    near-duplicates in large text collections.
    """

    def __init__(self, hash_bits: int = 64):
        """Initialize SimHash.

        Args:
            hash_bits: Number of bits in the hash (default 64).
        """
        self.hash_bits = hash_bits

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into words."""
        # Simple word tokenization
        import re

        words = re.findall(r"\w+", text.lower())
        return words

    def _hash_token(self, token: str) -> int:
        """Hash a single token to an integer."""
        # Use MD5 and take first 8 bytes for 64-bit hash
        h = hashlib.md5(token.encode("utf-8")).digest()
        return int.from_bytes(h[:8], byteorder="big")

    def compute(self, text: str) -> int:
        """Compute SimHash for text.

        Args:
            text: Input text.

        Returns:
            SimHash value as integer.
        """
        tokens = self._tokenize(text)
        if not tokens:
            return 0

        # Initialize bit counts
        v = [0] * self.hash_bits

        for token in tokens:
            token_hash = self._hash_token(token)
            for i in range(self.hash_bits):
                bit = (token_hash >> i) & 1
                if bit:
                    v[i] += 1
                else:
                    v[i] -= 1

        # Convert to hash
        fingerprint = 0
        for i in range(self.hash_bits):
            if v[i] > 0:
                fingerprint |= 1 << i

        return fingerprint

    def hamming_distance(self, hash1: int, hash2: int) -> int:
        """Calculate Hamming distance between two hashes.

        Args:
            hash1: First hash.
            hash2: Second hash.

        Returns:
            Number of differing bits.
        """
        xor = hash1 ^ hash2
        distance = 0
        while xor:
            distance += xor & 1
            xor >>= 1
        return distance

    def similarity(self, hash1: int, hash2: int) -> float:
        """Calculate similarity between two hashes.

        Args:
            hash1: First hash.
            hash2: Second hash.

        Returns:
            Similarity score (0.0-1.0).
        """
        distance = self.hamming_distance(hash1, hash2)
        return 1.0 - (distance / self.hash_bits)


# ============================================================================
# MinHash Implementation
# ============================================================================


class MinHash:
    """MinHash for Jaccard similarity estimation.

    MinHash uses multiple hash functions to estimate the Jaccard
    similarity between sets (represented as shingles of text).
    """

    def __init__(self, num_hashes: int = 128, shingle_size: int = 3):
        """Initialize MinHash.

        Args:
            num_hashes: Number of hash functions (default 128).
            shingle_size: Size of character shingles (default 3).
        """
        self.num_hashes = num_hashes
        self.shingle_size = shingle_size
        # Generate random coefficients for hash functions
        import random

        random.seed(42)  # Deterministic for reproducibility
        self._a = [random.randint(1, 2**31 - 1) for _ in range(num_hashes)]
        self._b = [random.randint(0, 2**31 - 1) for _ in range(num_hashes)]
        self._prime = 2**31 - 1  # Mersenne prime

    def _get_shingles(self, text: str) -> Set[str]:
        """Extract character shingles from text.

        Args:
            text: Input text.

        Returns:
            Set of shingles.
        """
        text = text.lower()
        if len(text) < self.shingle_size:
            return {text} if text else set()

        shingles = set()
        for i in range(len(text) - self.shingle_size + 1):
            shingles.add(text[i : i + self.shingle_size])
        return shingles

    def _hash_shingle(self, shingle: str, idx: int) -> int:
        """Hash a shingle using the idx-th hash function.

        Args:
            shingle: Shingle string.
            idx: Hash function index.

        Returns:
            Hash value.
        """
        # Convert shingle to integer
        h = int(hashlib.md5(shingle.encode("utf-8")).hexdigest()[:8], 16)
        # Apply hash function: (a*h + b) mod prime
        return (self._a[idx] * h + self._b[idx]) % self._prime

    def compute(self, text: str) -> List[int]:
        """Compute MinHash signature for text.

        Args:
            text: Input text.

        Returns:
            MinHash signature as list of integers.
        """
        shingles = self._get_shingles(text)
        if not shingles:
            return [self._prime] * self.num_hashes

        # Initialize signature with max values
        signature = [self._prime] * self.num_hashes

        for shingle in shingles:
            for i in range(self.num_hashes):
                h = self._hash_shingle(shingle, i)
                if h < signature[i]:
                    signature[i] = h

        return signature

    def similarity(self, sig1: List[int], sig2: List[int]) -> float:
        """Estimate Jaccard similarity from MinHash signatures.

        Args:
            sig1: First signature.
            sig2: Second signature.

        Returns:
            Estimated Jaccard similarity (0.0-1.0).
        """
        if len(sig1) != len(sig2):
            raise ValueError("Signatures must have same length")

        matches = sum(1 for a, b in zip(sig1, sig2) if a == b)
        return matches / len(sig1)


@dataclass
class DuplicateGroup:
    """A group of similar/duplicate memories."""

    representative_id: str
    representative_preview: str
    members: List[Dict[str, Any]]
    similarity_scores: List[float]
    tag_overlap: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "representative_id": self.representative_id,
            "representative_preview": self.representative_preview,
            "member_count": len(self.members),
            "members": self.members,
            "similarity_scores": [round(s, 4) for s in self.similarity_scores],
            "tag_overlap": round(self.tag_overlap, 2),
        }


def find_duplicates(
    threshold: float = 0.85,
    limit: int = 50,
    project_path: Optional[str] = None,
    min_group_size: int = 2,
    strategy: str = "vector",
) -> Dict[str, Any]:
    """Find groups of similar/duplicate memories.

    Args:
        threshold: Similarity threshold (0.0-1.0). Higher = stricter matching.
        limit: Maximum number of memories to analyze.
        project_path: Optional project path filter.
        min_group_size: Minimum group size to report.
        strategy: Deduplication strategy - "vector" (default), "simhash", or "minhash".

    Returns:
        Dict with duplicate groups and statistics.
    """
    valid_strategies = ["vector", "simhash", "minhash"]
    if strategy not in valid_strategies:
        return {
            "error": f"Invalid strategy: '{strategy}'. Valid options: {valid_strategies}",
            "groups": [],
            "total_groups": 0,
        }

    db = MemoryDatabase()
    try:
        # Get active memories
        memories = db.get_active_memories(limit=limit, project_path=project_path)

        if len(memories) < 2:
            return {
                "groups": [],
                "total_groups": 0,
                "analyzed_count": len(memories),
                "strategy": strategy,
                "message": "Not enough memories to find duplicates.",
            }

        # Use appropriate strategy
        if strategy == "vector":
            groups = _find_duplicates_vector(db, memories, threshold, min_group_size)
        elif strategy == "simhash":
            groups = _find_duplicates_simhash(memories, threshold, min_group_size)
        elif strategy == "minhash":
            groups = _find_duplicates_minhash(memories, threshold, min_group_size)
        else:
            groups = []

        return {
            "groups": [g.to_dict() for g in groups],
            "total_groups": len(groups),
            "analyzed_count": len(memories),
            "threshold": threshold,
            "strategy": strategy,
            "total_duplicates": sum(len(g.members) for g in groups),
        }

    finally:
        db.close()


def _find_duplicates_vector(
    db: MemoryDatabase,
    memories: List[Memory],
    threshold: float,
    min_group_size: int,
) -> List[DuplicateGroup]:
    """Find duplicates using vector similarity (original method)."""
    # Get embedder
    try:
        embedder = get_embedder()
        if isinstance(embedder, NoOpEmbedder):
            return []
    except Exception:
        return []

    # Build embeddings for all memories
    memory_embeddings: Dict[str, List[float]] = {}
    for memory in memories:
        try:
            embedding = embedder.embed(memory.content)
            if is_valid_embedding(embedding, config.embedding_dimension):
                memory_embeddings[memory.id] = embedding
        except Exception:
            continue

    if len(memory_embeddings) < 2:
        return []

    return _find_similar_groups(
        db, memories, memory_embeddings, threshold, min_group_size
    )


def _find_duplicates_simhash(
    memories: List[Memory],
    threshold: float,
    min_group_size: int,
) -> List[DuplicateGroup]:
    """Find duplicates using SimHash.

    SimHash is faster than vector similarity and works well for
    near-duplicate detection without requiring embeddings.
    """
    simhash = SimHash(hash_bits=64)

    # Compute hashes for all memories
    memory_hashes: Dict[str, int] = {}
    memory_map = {m.id: m for m in memories}

    for memory in memories:
        memory_hashes[memory.id] = simhash.compute(memory.content)

    # Find similar pairs
    grouped: Set[str] = set()
    groups: List[DuplicateGroup] = []
    memory_ids = list(memory_hashes.keys())

    for i, mem_id in enumerate(memory_ids):
        if mem_id in grouped:
            continue

        memory = memory_map.get(mem_id)
        if not memory:
            continue

        hash1 = memory_hashes[mem_id]
        similar_ids = []
        similarity_scores = []

        for j in range(i + 1, len(memory_ids)):
            other_id = memory_ids[j]
            if other_id in grouped:
                continue

            hash2 = memory_hashes[other_id]
            sim = simhash.similarity(hash1, hash2)

            if sim >= threshold:
                similar_ids.append(other_id)
                similarity_scores.append(sim)

        if len(similar_ids) >= min_group_size - 1:
            members = []
            all_tags: List[set] = [set(memory.tags)]

            for sim_id, score in zip(similar_ids, similarity_scores):
                sim_memory = memory_map.get(sim_id)
                if sim_memory:
                    preview = (
                        sim_memory.content[:100] + "..."
                        if len(sim_memory.content) > 100
                        else sim_memory.content
                    )
                    members.append(
                        {
                            "id": sim_id,
                            "preview": preview,
                            "tags": sim_memory.tags,
                            "similarity": round(score, 4),
                            "created_at": sim_memory.created_at,
                        }
                    )
                    all_tags.append(set(sim_memory.tags))
                    grouped.add(sim_id)

            # Calculate tag overlap
            tag_overlap = _calculate_tag_overlap(all_tags)
            grouped.add(mem_id)

            rep_preview = (
                memory.content[:100] + "..."
                if len(memory.content) > 100
                else memory.content
            )
            groups.append(
                DuplicateGroup(
                    representative_id=mem_id,
                    representative_preview=rep_preview,
                    members=members,
                    similarity_scores=similarity_scores,
                    tag_overlap=tag_overlap,
                )
            )

    return groups


def _find_duplicates_minhash(
    memories: List[Memory],
    threshold: float,
    min_group_size: int,
) -> List[DuplicateGroup]:
    """Find duplicates using MinHash.

    MinHash estimates Jaccard similarity and is effective for
    detecting content overlap even with different wording.
    """
    minhash = MinHash(num_hashes=128, shingle_size=3)

    # Compute signatures for all memories
    memory_sigs: Dict[str, List[int]] = {}
    memory_map = {m.id: m for m in memories}

    for memory in memories:
        memory_sigs[memory.id] = minhash.compute(memory.content)

    # Find similar pairs
    grouped: Set[str] = set()
    groups: List[DuplicateGroup] = []
    memory_ids = list(memory_sigs.keys())

    for i, mem_id in enumerate(memory_ids):
        if mem_id in grouped:
            continue

        memory = memory_map.get(mem_id)
        if not memory:
            continue

        sig1 = memory_sigs[mem_id]
        similar_ids = []
        similarity_scores = []

        for j in range(i + 1, len(memory_ids)):
            other_id = memory_ids[j]
            if other_id in grouped:
                continue

            sig2 = memory_sigs[other_id]
            sim = minhash.similarity(sig1, sig2)

            if sim >= threshold:
                similar_ids.append(other_id)
                similarity_scores.append(sim)

        if len(similar_ids) >= min_group_size - 1:
            members = []
            all_tags: List[set] = [set(memory.tags)]

            for sim_id, score in zip(similar_ids, similarity_scores):
                sim_memory = memory_map.get(sim_id)
                if sim_memory:
                    preview = (
                        sim_memory.content[:100] + "..."
                        if len(sim_memory.content) > 100
                        else sim_memory.content
                    )
                    members.append(
                        {
                            "id": sim_id,
                            "preview": preview,
                            "tags": sim_memory.tags,
                            "similarity": round(score, 4),
                            "created_at": sim_memory.created_at,
                        }
                    )
                    all_tags.append(set(sim_memory.tags))
                    grouped.add(sim_id)

            # Calculate tag overlap
            tag_overlap = _calculate_tag_overlap(all_tags)
            grouped.add(mem_id)

            rep_preview = (
                memory.content[:100] + "..."
                if len(memory.content) > 100
                else memory.content
            )
            groups.append(
                DuplicateGroup(
                    representative_id=mem_id,
                    representative_preview=rep_preview,
                    members=members,
                    similarity_scores=similarity_scores,
                    tag_overlap=tag_overlap,
                )
            )

    return groups


def _calculate_tag_overlap(all_tags: List[set]) -> float:
    """Calculate Jaccard similarity of tag sets."""
    if not all_tags:
        return 0.0
    intersection = set.intersection(*all_tags) if len(all_tags) > 1 else all_tags[0]
    union = set.union(*all_tags) if all_tags else set()
    return len(intersection) / len(union) if union else 0.0


def _find_similar_groups(
    db: MemoryDatabase,
    memories: List[Memory],
    embeddings: Dict[str, List[float]],
    threshold: float,
    min_group_size: int,
) -> List[DuplicateGroup]:
    """Find groups of similar memories using pairwise comparison."""

    # Build memory lookup
    memory_map = {m.id: m for m in memories}

    # Track which memories are already grouped
    grouped: set = set()
    groups: List[DuplicateGroup] = []

    # Compare each memory against others
    memory_ids = list(embeddings.keys())

    for i, mem_id in enumerate(memory_ids):
        if mem_id in grouped:
            continue

        memory = memory_map.get(mem_id)
        if not memory:
            continue

        embedding = embeddings[mem_id]

        # Search for similar memories
        similar_results = db.search_memories(embedding, limit=20, threshold=threshold)

        # Filter to only include memories in our set
        similar_ids = []
        similarity_scores = []

        for similar_mem, distance in similar_results:
            if similar_mem.id == mem_id:
                continue
            if similar_mem.id in grouped:
                continue
            if similar_mem.id not in embeddings:
                continue

            similarity = 1.0 - distance
            if similarity >= threshold:
                similar_ids.append(similar_mem.id)
                similarity_scores.append(similarity)

        if len(similar_ids) >= min_group_size - 1:
            # Create group with this memory as representative
            members = []
            all_tags: List[set] = [set(memory.tags)]

            for sim_id, score in zip(similar_ids, similarity_scores):
                sim_memory = memory_map.get(sim_id)
                if sim_memory:
                    preview = (
                        sim_memory.content[:100] + "..."
                        if len(sim_memory.content) > 100
                        else sim_memory.content
                    )
                    members.append(
                        {
                            "id": sim_id,
                            "preview": preview,
                            "tags": sim_memory.tags,
                            "similarity": round(score, 4),
                            "created_at": sim_memory.created_at,
                        }
                    )
                    all_tags.append(set(sim_memory.tags))
                    grouped.add(sim_id)

            # Calculate tag overlap (Jaccard similarity)
            if all_tags:
                intersection = (
                    set.intersection(*all_tags) if len(all_tags) > 1 else all_tags[0]
                )
                union = set.union(*all_tags) if all_tags else set()
                tag_overlap = len(intersection) / len(union) if union else 0.0
            else:
                tag_overlap = 0.0

            grouped.add(mem_id)

            rep_preview = (
                memory.content[:100] + "..."
                if len(memory.content) > 100
                else memory.content
            )
            groups.append(
                DuplicateGroup(
                    representative_id=mem_id,
                    representative_preview=rep_preview,
                    members=members,
                    similarity_scores=similarity_scores,
                    tag_overlap=tag_overlap,
                )
            )

    return groups


def merge_memories(
    memory_ids: List[str],
    keep_id: Optional[str] = None,
    merge_tags: bool = True,
    dry_run: bool = True,
) -> Dict[str, Any]:
    """Merge multiple memories into one, superseding the others.

    Args:
        memory_ids: List of memory IDs to merge.
        keep_id: ID of memory to keep. If None, keeps the oldest.
        merge_tags: If True, combine tags from all memories.
        dry_run: If True, show what would happen without making changes.

    Returns:
        Dict with merge results.
    """
    if len(memory_ids) < 2:
        return {"error": "Need at least 2 memory IDs to merge."}

    db = MemoryDatabase()
    try:
        # Fetch all memories
        memories: Dict[str, Memory] = {}
        missing_ids: List[str] = []

        for mem_id in memory_ids:
            memory = db.get_memory(mem_id)
            if memory:
                memories[mem_id] = memory
            else:
                missing_ids.append(mem_id)

        if missing_ids:
            return {
                "error": f"Memory IDs not found: {missing_ids}",
                "found": list(memories.keys()),
            }

        if len(memories) < 2:
            return {"error": "Need at least 2 valid memories to merge."}

        # Determine which memory to keep
        if keep_id:
            if keep_id not in memories:
                return {"error": f"Keep ID '{keep_id}' not in provided memory IDs."}
            keeper = memories[keep_id]
        else:
            # Keep the oldest memory
            keeper = min(memories.values(), key=lambda m: m.created_at)

        # Calculate merged tags
        if merge_tags:
            all_tags = set()
            for memory in memories.values():
                all_tags.update(memory.tags)
            merged_tags = sorted(all_tags)
        else:
            merged_tags = keeper.tags

        # Determine memories to supersede
        to_supersede = [m for m in memories.values() if m.id != keeper.id]

        result = {
            "dry_run": dry_run,
            "keep": {
                "id": keeper.id,
                "preview": keeper.content[:100] + "..."
                if len(keeper.content) > 100
                else keeper.content,
                "original_tags": keeper.tags,
                "merged_tags": merged_tags,
            },
            "supersede": [
                {
                    "id": m.id,
                    "preview": m.content[:100] + "..."
                    if len(m.content) > 100
                    else m.content,
                    "tags": m.tags,
                }
                for m in to_supersede
            ],
            "supersede_count": len(to_supersede),
        }

        if dry_run:
            result["message"] = "Dry run - no changes made. Remove --dry-run to apply."
            return result

        # Apply merge
        embedder = None
        try:
            embedder = get_embedder()
            has_embedder = not isinstance(embedder, NoOpEmbedder)
        except Exception:
            has_embedder = False

        # Update keeper's tags if merging
        if merge_tags and set(merged_tags) != set(keeper.tags):
            keeper.tags = merged_tags
            keeper.updated_at = int(time.time())

            embedding = None
            if has_embedder and embedder is not None:
                try:
                    embedding = embedder.embed(keeper.content)
                except Exception:
                    pass

            db.update_memory(keeper, embedding=embedding)

        # Supersede other memories
        for memory in to_supersede:
            db.conn.execute(
                "UPDATE memories SET superseded_by = ?, updated_at = ? WHERE id = ?",
                (keeper.id, int(time.time()), memory.id),
            )
        db.conn.commit()

        result["message"] = f"Merged {len(to_supersede)} memories into {keeper.id}"
        result["success"] = True

        return result

    finally:
        db.close()


def auto_dedupe(
    threshold: float = 0.95,
    limit: int = 100,
    project_path: Optional[str] = None,
    dry_run: bool = True,
    strategy: str = "vector",
) -> Dict[str, Any]:
    """Automatically find and merge highly similar memories.

    Uses a high threshold (0.95) by default to only merge near-duplicates.

    Args:
        threshold: Similarity threshold (0.0-1.0). Default 0.95 for safety.
        limit: Maximum memories to analyze.
        project_path: Optional project filter.
        dry_run: If True, show what would happen without making changes.
        strategy: Deduplication strategy - "vector" (default), "simhash", or "minhash".

    Returns:
        Dict with auto-dedupe results.
    """
    # Find duplicates first
    dup_result = find_duplicates(
        threshold=threshold,
        limit=limit,
        project_path=project_path,
        min_group_size=2,
        strategy=strategy,
    )

    if "error" in dup_result:
        return dup_result

    groups = dup_result.get("groups", [])

    if not groups:
        return {
            "dry_run": dry_run,
            "message": "No duplicates found at threshold {:.2f}".format(threshold),
            "merged_count": 0,
            "groups_processed": 0,
        }

    merge_results = []
    total_merged = 0

    for group in groups:
        rep_id = group["representative_id"]
        member_ids = [m["id"] for m in group["members"]]
        all_ids = [rep_id] + member_ids

        merge_result = merge_memories(
            memory_ids=all_ids,
            keep_id=rep_id,
            merge_tags=True,
            dry_run=dry_run,
        )

        merge_results.append(
            {
                "group_representative": rep_id,
                "merged_count": len(member_ids),
                "result": merge_result,
            }
        )

        if not dry_run and merge_result.get("success"):
            total_merged += len(member_ids)

    return {
        "dry_run": dry_run,
        "threshold": threshold,
        "groups_processed": len(groups),
        "total_merged": total_merged if not dry_run else 0,
        "would_merge": sum(len(g["members"]) for g in groups) if dry_run else 0,
        "details": merge_results,
        "message": (
            f"Dry run - would merge {sum(len(g['members']) for g in groups)} memories. "
            "Remove --dry-run to apply."
        )
        if dry_run
        else f"Merged {total_merged} duplicate memories.",
    }
