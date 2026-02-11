"""Tests for fetch_unprocessed_sessions command."""

from unittest.mock import MagicMock, patch

from gmemory.commands.fetch import fetch_unprocessed_sessions
from gmemory.models import Message, Session


def _build_session(idx: int) -> Session:
    return Session(
        session_id=f"ses-{idx}",
        agent="opencode",
        project_path=f"C:/repo/{idx}",
        project_name=f"repo-{idx}",
        started_at=f"t-{idx}",
        messages=[Message(role="user", content=f"msg-{idx}")],
    )


@patch("gmemory.commands.fetch.ScannerRegistry.create")
def test_fetch_unprocessed_sessions_pagination_and_counts(
    mock_create: MagicMock,
) -> None:
    scanner = MagicMock()
    scanner.count_unprocessed.return_value = 5
    scanner.get_unprocessed_sessions.return_value = [
        _build_session(i) for i in range(5)
    ]
    mock_create.return_value = scanner

    result = fetch_unprocessed_sessions(
        limit=2,
        agent="opencode",
        scanner_type="opencode",
        offset=1,
    )

    assert result["total_pending"] == 5
    assert result["remaining"] == 5
    assert result["returned"] == 2
    assert result["remaining_after_page"] == 2
    assert result["offset"] == 1
    assert result["has_more"] is True
    assert result["next_cursor"] == "3"
    assert len(result["sessions"]) == 2
    assert result["sessions"][0]["session_id"] == "ses-1"


@patch("gmemory.commands.fetch.ScannerRegistry.create")
def test_fetch_unprocessed_sessions_cursor_priority_and_compact(
    mock_create: MagicMock,
) -> None:
    scanner = MagicMock()
    scanner.count_unprocessed.return_value = 4
    scanner.get_unprocessed_sessions.return_value = [
        _build_session(i) for i in range(4)
    ]
    mock_create.return_value = scanner

    result = fetch_unprocessed_sessions(
        limit=2,
        scanner_type="opencode",
        offset=0,
        cursor="2",
        compact=True,
    )

    assert result["offset"] == 2
    assert result["returned"] == 2
    assert result["has_more"] is False
    assert result["next_cursor"] is None

    session = result["sessions"][0]
    assert session["session_id"] == "ses-2"
    assert session["agent"] == "opencode"
    assert session["project_path"] == "C:/repo/2"
    assert session["project_name"] == "repo-2"
    assert session["started_at"] == "t-2"
    assert session["message_count"] == 1
    assert "messages" not in session


def test_fetch_unprocessed_sessions_invalid_offset_returns_error() -> None:
    result = fetch_unprocessed_sessions(limit=2, scanner_type="opencode", offset=-1)

    assert "error" in result
    assert "offset must be a non-negative integer" in result["error"]
    assert result["sessions"] == []


def test_fetch_unprocessed_sessions_invalid_cursor_returns_error() -> None:
    result = fetch_unprocessed_sessions(limit=2, scanner_type="opencode", cursor="abc")

    assert "error" in result
    assert "cursor must be a non-negative integer" in result["error"]
    assert result["sessions"] == []


@patch("gmemory.commands.fetch.ScannerRegistry.list_scanners")
@patch("gmemory.commands.fetch.ScannerRegistry.create")
def test_fetch_unprocessed_sessions_multi_scanner_cross_boundary(
    mock_create: MagicMock,
    mock_list_scanners: MagicMock,
) -> None:
    scanner_a = MagicMock()
    scanner_a.count_unprocessed.return_value = 3
    scanner_a.get_unprocessed_sessions.return_value = [
        Session(
            session_id=f"a-{i}",
            agent="scanner-a",
            project_path="C:/repo/a",
            project_name="repo-a",
            started_at=f"ta-{i}",
            messages=[Message(role="user", content=f"a-{i}")],
        )
        for i in range(3)
    ]

    scanner_b = MagicMock()
    scanner_b.count_unprocessed.return_value = 3
    scanner_b.get_unprocessed_sessions.return_value = [
        Session(
            session_id=f"b-{i}",
            agent="scanner-b",
            project_path="C:/repo/b",
            project_name="repo-b",
            started_at=f"tb-{i}",
            messages=[Message(role="assistant", content=f"b-{i}")],
        )
        for i in range(3)
    ]

    mock_list_scanners.return_value = ["scanner-a", "scanner-b"]

    def _create_side_effect(name: str, agent: str, incremental: bool) -> MagicMock:
        assert incremental is True
        if name == "scanner-a":
            return scanner_a
        if name == "scanner-b":
            return scanner_b
        raise AssertionError(f"unexpected scanner: {name}")

    mock_create.side_effect = _create_side_effect

    result = fetch_unprocessed_sessions(limit=4, scanner_type="all", offset=2)

    assert result["total_pending"] == 6
    assert result["remaining"] == 6
    assert result["offset"] == 2
    assert result["returned"] == 4
    assert result["remaining_after_page"] == 0
    assert result["has_more"] is False
    assert result["next_cursor"] is None
    assert [item["session_id"] for item in result["sessions"]] == [
        "a-2",
        "b-0",
        "b-1",
        "b-2",
    ]


@patch("gmemory.commands.fetch.ScannerRegistry.list_scanners")
@patch("gmemory.commands.fetch.ScannerRegistry.create")
def test_fetch_unprocessed_sessions_multi_scanner_cursor_page_transition(
    mock_create: MagicMock,
    mock_list_scanners: MagicMock,
) -> None:
    scanner_a = MagicMock()
    scanner_a.count_unprocessed.return_value = 2
    scanner_a.get_unprocessed_sessions.return_value = [
        Session(
            session_id=f"a-{i}",
            agent="scanner-a",
            project_path="C:/repo/a",
            project_name="repo-a",
            started_at=f"ta-{i}",
            messages=[Message(role="user", content=f"a-{i}")],
        )
        for i in range(2)
    ]

    scanner_b = MagicMock()
    scanner_b.count_unprocessed.return_value = 3
    scanner_b.get_unprocessed_sessions.return_value = [
        Session(
            session_id=f"b-{i}",
            agent="scanner-b",
            project_path="C:/repo/b",
            project_name="repo-b",
            started_at=f"tb-{i}",
            messages=[Message(role="assistant", content=f"b-{i}")],
        )
        for i in range(3)
    ]

    mock_list_scanners.return_value = ["scanner-a", "scanner-b"]

    def _create_side_effect(name: str, agent: str, incremental: bool) -> MagicMock:
        assert incremental is True
        return scanner_a if name == "scanner-a" else scanner_b

    mock_create.side_effect = _create_side_effect

    first_page = fetch_unprocessed_sessions(limit=2, scanner_type="all", offset=0)
    assert first_page["offset"] == 0
    assert first_page["returned"] == 2
    assert first_page["has_more"] is True
    assert first_page["next_cursor"] == "2"
    assert [item["session_id"] for item in first_page["sessions"]] == ["a-0", "a-1"]

    second_page = fetch_unprocessed_sessions(
        limit=2,
        scanner_type="all",
        offset=0,
        cursor=first_page["next_cursor"],
    )
    assert second_page["offset"] == 2
    assert second_page["returned"] == 2
    assert second_page["has_more"] is True
    assert second_page["next_cursor"] == "4"
    assert [item["session_id"] for item in second_page["sessions"]] == ["b-0", "b-1"]
