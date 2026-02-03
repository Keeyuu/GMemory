# Usage Verification Snippet for gmemory.commands.search
# This snippet demonstrates how to use the search_memories function.

from gmemory.commands.search import search_memories


def example_usage():
    # 1. Simple search
    results = search_memories(query="vector database", limit=5)
    print(f"Found {results['total']} memories:")
    for res in results["results"]:
        print(f"[{res['similarity']:.2f}] {res['content'][:50]}...")

    # 2. Filtered search
    results = search_memories(
        query="python performance",
        project_path="/home/user/code/myproject",
        tags=["optimization", "database"],
        limit=3,
    )
    print(f"\nFiltered search found {results['total']} memories.")


if __name__ == "__main__":
    print(
        "This is a usage snippet. Execution depends on a configured environment (Ollama, SQLite+Vec)."
    )
    # example_usage()
