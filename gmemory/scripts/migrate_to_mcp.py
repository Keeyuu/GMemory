import json
import sqlite3
import hashlib
import struct
import os
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

from gmemory.storage.database import MemoryDatabase
from gmemory.models import Memory as GMemory


def generate_content_hash(content: str) -> str:
    """Generate SHA256 hash of content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def migrate():
    # Initialize GMemory database
    db = MemoryDatabase()

    # Get all active memories (not superseded)
    # We use a large limit to get everything
    memories = db.get_active_memories(limit=1000000)
    print(f"Found {len(memories)} active memories in GMemory.")

    migrated_memories = []

    for gmem in memories:
        # Fetch embedding
        cursor = db.conn.execute(
            "SELECT embedding FROM vec_memories WHERE memory_id = ?", (gmem.id,)
        )
        row = cursor.fetchone()
        embedding = None
        if row and row[0]:
            # Deserialize float32 blob
            blob = row[0]
            dim = len(blob) // 4
            embedding = list(struct.unpack(f"{dim}f", blob))

        # Transform to MCP format
        mcp_mem = {
            "content": gmem.content,
            "content_hash": generate_content_hash(gmem.content),
            "tags": gmem.tags,
            "created_at": float(gmem.created_at),
            "updated_at": float(gmem.updated_at),
            "memory_type": gmem.memory_type or "observation",
            "metadata": {
                "gmemory_id": gmem.id,
                "importance": gmem.importance,
                "agent": gmem.agent,
                "project_name": gmem.project_name,
                "project_path": gmem.project_path,
                "access_count": gmem.access_count,
                "last_accessed_at": float(gmem.last_accessed_at)
                if gmem.last_accessed_at
                else None,
            },
        }

        if embedding:
            mcp_mem["embedding"] = embedding

        migrated_memories.append(mcp_mem)

    # Prepare export container
    export_data = {
        "export_metadata": {
            "source_machine": os.uname().nodename
            if hasattr(os, "uname")
            else os.environ.get("COMPUTERNAME", "unknown"),
            "export_timestamp": datetime.utcnow().isoformat() + "Z",
            "source_service": "GMemory",
            "migration_version": "1.0.0",
        },
        "memories": migrated_memories,
    }

    # Write to file
    output_path = Path("gmemory_migration_to_mcp.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)

    print(f"Successfully migrated {len(migrated_memories)} memories to {output_path}")
    db.close()


if __name__ == "__main__":
    migrate()
