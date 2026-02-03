from gmemory.scanner.opencode import OpenCodeScanner
from pathlib import Path
import json


def main():
    print("Initializing OpenCodeScanner...")
    scanner = OpenCodeScanner()

    print(f"Scanning directory: {scanner.base_dir}")
    if not scanner.base_dir.exists():
        print(f"WARNING: Base directory {scanner.base_dir} does not exist.")
        return

    print("Fetching unprocessed sessions (limit=5)...")
    sessions = scanner.get_unprocessed_sessions(limit=5)

    print(f"Found {len(sessions)} unprocessed sessions.")

    if sessions:
        first_session = sessions[0]
        print("\n--- First Session Details ---")
        print(f"ID: {first_session.session_id}")
        print(f"Project: {first_session.project_name}")
        print(f"Started At: {first_session.started_at}")
        print(f"Message Count: {len(first_session.messages)}")

        if first_session.messages:
            first_msg = first_session.messages[0]
            print("\n--- First Message ---")
            print(f"Role: {first_msg.role}")
            print(f"Content (first 100 chars): {first_msg.content[:100]}...")
    else:
        print(
            "No sessions found. This might be because all sessions are already processed or the storage is empty."
        )


if __name__ == "__main__":
    main()
