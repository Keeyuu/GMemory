from typing import Dict, Any
from gmemory.storage.database import MemoryDatabase


def delete_memory(mem_id: str) -> Dict[str, Any]:
    """
    Delete a memory by its ID.

    Args:
        mem_id: The ID of the memory to delete.

    Returns:
        Dict containing:
        - id: The ID of the deleted memory.
        - deleted: Boolean indicating success.

    Raises:
        ValueError: If memory with mem_id is not found.
    """
    db = None
    try:
        db = MemoryDatabase()

        # Check if memory exists
        if not db.get_memory(mem_id):
            raise ValueError(f"Memory with ID {mem_id} not found.")

        # Delete the memory
        db.delete_memory(mem_id)

        return {
            "id": mem_id,
            "deleted": True,
        }

    except Exception as e:
        raise e
    finally:
        if db:
            db.close()
