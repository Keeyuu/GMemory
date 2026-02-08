"""Tests for GitHub Copilot scanner."""

import json
from pathlib import Path
import gmemory.config as cfg

from gmemory.storage.database import MemoryDatabase

from gmemory.scanner.copilot import CopilotScanner


def _create_workspace_chat(
    tmp_path: Path, workspace_hash: str, session_id: str
) -> Path:
    workspace_dir = tmp_path / workspace_hash
    chat_dir = workspace_dir / "chatSessions"
    chat_dir.mkdir(parents=True)
    workspace_file = workspace_dir / "workspace.json"
    workspace_file.write_text(json.dumps({"folder": "file:///c%3A/Code/demo/project"}))
    session_file = chat_dir / f"{session_id}.json"
    session_file.write_text(
        json.dumps(
            {
                "sessionId": session_id,
                "creationDate": 1770209806613,
                "requests": [
                    {
                        "requestId": "request_1",
                        "message": {"text": "Hello Copilot"},
                        "response": [
                            {"kind": "thinking", "value": "..."},
                            {"value": "Hi there"},
                            {"kind": "toolInvocationSerialized", "value": "tool"},
                        ],
                    },
                    {
                        "requestId": "request_2",
                        "message": {"text": "Second question"},
                        "response": [
                            {"value": "Second answer"},
                        ],
                    },
                ],
            }
        )
    )
    return session_file


def test_copilot_scanner_reads_chat_sessions(tmp_path):
    _create_workspace_chat(tmp_path, "workspace1", "session-1")
    scanner = CopilotScanner(base_dir=tmp_path, incremental=False)

    sessions = scanner.get_unprocessed_sessions(limit=5)

    assert len(sessions) == 1
    session = sessions[0]
    assert session.session_id == "session-1"
    assert session.project_path.endswith("\\Code\\demo\\project")
    assert session.project_name == "project"
    assert session.started_at == "1770209806613"
    assert [m.role for m in session.messages] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]
    assert session.messages[0].content == "Hello Copilot"
    assert session.messages[1].content == "Hi there"
    assert session.messages[2].content == "Second question"
    assert session.messages[3].content == "Second answer"


def test_copilot_scanner_count_sessions(tmp_path):
    _create_workspace_chat(tmp_path, "workspace1", "session-1")
    _create_workspace_chat(tmp_path, "workspace2", "session-2")
    scanner = CopilotScanner(base_dir=tmp_path, incremental=False)

    assert scanner.count_sessions() == 2


def test_copilot_scanner_skips_when_version_unchanged(tmp_path):
    original_path = cfg.config._config["storage"]["db_path"]
    cfg.config._config["storage"]["db_path"] = str(tmp_path / "copilot-scanner.db")
    try:
        session_id = "session-1"
        session_file = _create_workspace_chat(tmp_path, "workspace1", session_id)
        scanner = CopilotScanner(base_dir=tmp_path, incremental=False)
        session_data = json.loads(session_file.read_text(encoding="utf-8"))
        source_updated_at, session_hash = scanner._compute_session_version(session_data)

        db = MemoryDatabase()
        try:
            db.mark_session_processed(
                agent=scanner.agent,
                session_id=session_id,
                source_updated_at=source_updated_at,
                session_hash=session_hash,
                processor="default",
            )
        finally:
            db.close()

        sessions = scanner.get_unprocessed_sessions(limit=5)
        assert sessions == []
    finally:
        cfg.config._config["storage"]["db_path"] = original_path


def test_copilot_scanner_reprocesses_when_hash_changes(tmp_path):
    original_path = cfg.config._config["storage"]["db_path"]
    cfg.config._config["storage"]["db_path"] = str(tmp_path / "copilot-scanner.db")
    try:
        session_id = "session-1"
        session_file = _create_workspace_chat(tmp_path, "workspace1", session_id)
        scanner = CopilotScanner(base_dir=tmp_path, incremental=False)

        old_data = json.loads(session_file.read_text(encoding="utf-8"))
        source_updated_at, old_hash = scanner._compute_session_version(old_data)

        db = MemoryDatabase()
        try:
            db.mark_session_processed(
                agent=scanner.agent,
                session_id=session_id,
                source_updated_at=source_updated_at,
                session_hash=old_hash,
                processor="default",
            )
        finally:
            db.close()

        updated = old_data
        updated["requests"][0]["message"]["text"] = "Hello Copilot updated"
        session_file.write_text(json.dumps(updated), encoding="utf-8")

        sessions = scanner.get_unprocessed_sessions(limit=5)
        assert len(sessions) == 1
        assert sessions[0].session_id == session_id
    finally:
        cfg.config._config["storage"]["db_path"] = original_path
