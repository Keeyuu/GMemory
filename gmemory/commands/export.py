"""Export commands for GMemory.

Provides functionality to export memories and reports to Markdown/JSON.
"""

import json
import time
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path

from gmemory.storage.database import MemoryDatabase
from gmemory.commands.session_report import get_session_report, get_session_detail


def _format_timestamp(ts: int) -> str:
    """Format Unix timestamp to ISO date string."""
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def _format_date(ts: int) -> str:
    """Format Unix timestamp to date only."""
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d")


def export_session(
    session_id: str,
    format: str = "markdown",
    include_content: bool = True,
    output_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Export a session's memories to Markdown or JSON.

    Args:
        session_id: Session ID to export.
        format: Output format - "markdown" or "json".
        include_content: If True, include full memory content.
        output_path: Optional file path to write output.

    Returns:
        Dict with export results and content.
    """
    # Get session detail
    detail = get_session_detail(session_id, include_content=include_content)

    if "error" in detail:
        return detail

    if format == "json":
        content = json.dumps(detail, indent=2, ensure_ascii=False)
    else:  # markdown
        content = _format_session_markdown(detail, include_content)

    result = {
        "session_id": session_id,
        "format": format,
        "memory_count": detail.get("memory_count", 0),
    }

    if output_path:
        try:
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            result["output_path"] = str(path.absolute())
            result["message"] = f"Exported to {path}"
        except Exception as e:
            result["error"] = f"Failed to write file: {e}"
            result["content"] = content
    else:
        result["content"] = content

    return result


def _format_session_markdown(detail: Dict[str, Any], include_content: bool) -> str:
    """Format session detail as Markdown."""
    lines = []

    session_id = detail.get("session_id", "unknown")
    lines.append(f"# Session: {session_id}")
    lines.append("")

    # Metadata
    lines.append("## Metadata")
    lines.append("")
    lines.append(f"- **Memory Count**: {detail.get('memory_count', 0)}")
    lines.append(f"- **Project**: {detail.get('project_path', 'N/A')}")

    if detail.get("first_memory_at"):
        lines.append(
            f"- **First Memory**: {_format_timestamp(detail['first_memory_at'])}"
        )
    if detail.get("last_memory_at"):
        lines.append(
            f"- **Last Memory**: {_format_timestamp(detail['last_memory_at'])}"
        )

    # Tags
    if detail.get("all_tags"):
        lines.append(f"- **Tags**: {', '.join(detail['all_tags'])}")

    # Importance breakdown
    if detail.get("importance_breakdown"):
        breakdown = detail["importance_breakdown"]
        parts = [f"{k}: {v}" for k, v in breakdown.items() if v > 0]
        if parts:
            lines.append(f"- **Importance**: {', '.join(parts)}")

    lines.append("")

    # Memories
    memories = detail.get("memories", [])
    if memories:
        lines.append("## Memories")
        lines.append("")

        for i, mem in enumerate(memories, 1):
            lines.append(f"### {i}. {mem.get('id', 'unknown')}")
            lines.append("")

            # Memory metadata
            tags = mem.get("tags", [])
            if tags:
                lines.append(f"**Tags**: `{', '.join(tags)}`")

            importance = mem.get("importance", "medium")
            created = mem.get("created_at")
            if created:
                lines.append(
                    f"**Created**: {_format_timestamp(created)} | **Importance**: {importance}"
                )

            lines.append("")

            # Content
            if include_content:
                content = mem.get("content", "")
                lines.append("```")
                lines.append(content)
                lines.append("```")
            else:
                preview = mem.get("preview", "")
                lines.append(f"> {preview}")

            lines.append("")

    # Footer
    lines.append("---")
    lines.append(f"*Exported from GMemory on {_format_timestamp(int(time.time()))}*")

    return "\n".join(lines)


def export_report(
    format: str = "markdown",
    limit: int = 20,
    project_path: Optional[str] = None,
    since_days: Optional[int] = None,
    output_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Export session aggregation report to Markdown or JSON.

    Args:
        format: Output format - "markdown" or "json".
        limit: Maximum sessions to include.
        project_path: Optional project filter.
        since_days: Only include sessions from last N days.
        output_path: Optional file path to write output.

    Returns:
        Dict with export results and content.
    """
    # Get session report
    report = get_session_report(
        limit=limit,
        project_path=project_path,
        include_empty=False,
        since_days=since_days,
    )

    if "error" in report:
        return report

    if format == "json":
        content = json.dumps(report, indent=2, ensure_ascii=False)
    else:  # markdown
        content = _format_report_markdown(report, since_days)

    result = {
        "format": format,
        "session_count": report.get("session_count", 0),
        "total_memories": report.get("total_memories", 0),
    }

    if output_path:
        try:
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            result["output_path"] = str(path.absolute())
            result["message"] = f"Exported to {path}"
        except Exception as e:
            result["error"] = f"Failed to write file: {e}"
            result["content"] = content
    else:
        result["content"] = content

    return result


def _format_report_markdown(report: Dict[str, Any], since_days: Optional[int]) -> str:
    """Format session report as Markdown."""
    lines = []

    lines.append("# GMemory Session Report")
    lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- **Total Sessions**: {report.get('session_count', 0)}")
    lines.append(f"- **Total Memories**: {report.get('total_memories', 0)}")

    if since_days:
        lines.append(f"- **Time Range**: Last {since_days} days")

    lines.append("")

    # Sessions table
    sessions = report.get("sessions", [])
    if sessions:
        lines.append("## Sessions")
        lines.append("")
        lines.append("| Session ID | Memories | Tags | Importance | Last Updated |")
        lines.append("|------------|----------|------|------------|--------------|")

        for sess in sessions:
            sess_id = sess.get("session_id", "unknown")
            # Truncate session ID for display
            display_id = sess_id[:20] + "..." if len(sess_id) > 20 else sess_id

            mem_count = sess.get("memory_count", 0)

            # Top tags
            tags = sess.get("top_tags", [])[:3]
            tags_str = ", ".join(tags) if tags else "-"

            # Importance summary
            importance = sess.get("importance_breakdown", {})
            imp_parts = []
            for level in ["high", "medium", "low"]:
                if importance.get(level, 0) > 0:
                    imp_parts.append(f"{level[0].upper()}:{importance[level]}")
            imp_str = " ".join(imp_parts) if imp_parts else "-"

            # Last updated
            last_updated = sess.get("last_memory_at")
            date_str = _format_date(last_updated) if last_updated else "-"

            lines.append(
                f"| `{display_id}` | {mem_count} | {tags_str} | {imp_str} | {date_str} |"
            )

        lines.append("")

    # Tag distribution
    if sessions:
        all_tags: Dict[str, int] = {}
        for sess in sessions:
            for tag in sess.get("top_tags", []):
                all_tags[tag] = all_tags.get(tag, 0) + 1

        if all_tags:
            lines.append("## Tag Distribution")
            lines.append("")
            sorted_tags = sorted(all_tags.items(), key=lambda x: x[1], reverse=True)[
                :15
            ]
            for tag, count in sorted_tags:
                lines.append(f"- `{tag}`: {count} sessions")
            lines.append("")

    # Footer
    lines.append("---")
    lines.append(f"*Generated by GMemory on {_format_timestamp(int(time.time()))}*")

    return "\n".join(lines)


def export_memories(
    memory_ids: Optional[List[str]] = None,
    project_path: Optional[str] = None,
    tags: Optional[List[str]] = None,
    limit: int = 100,
    format: str = "markdown",
    output_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Export memories to Markdown or JSON.

    Args:
        memory_ids: Specific memory IDs to export. If None, use filters.
        project_path: Filter by project path.
        tags: Filter by tags (memory must have all tags).
        limit: Maximum memories to export.
        format: Output format - "markdown" or "json".
        output_path: Optional file path to write output.

    Returns:
        Dict with export results and content.
    """
    db = MemoryDatabase()
    try:
        memories = []

        if memory_ids:
            # Export specific memories
            for mem_id in memory_ids:
                memory = db.get_memory(mem_id)
                if memory:
                    memories.append(memory)
        else:
            # Export by filters
            all_memories = db.get_active_memories(
                limit=limit, project_path=project_path
            )

            if tags:
                tag_set = set(tags)
                memories = [m for m in all_memories if tag_set.issubset(set(m.tags))]
            else:
                memories = all_memories

        if not memories:
            return {
                "error": "No memories found matching criteria.",
                "memory_count": 0,
            }

        # Convert to dicts
        memory_dicts = []
        for m in memories:
            memory_dicts.append(
                {
                    "id": m.id,
                    "content": m.content,
                    "tags": m.tags,
                    "importance": m.importance,
                    "memory_type": m.memory_type,
                    "project_path": m.project_path,
                    "created_at": m.created_at,
                    "updated_at": m.updated_at,
                }
            )

        if format == "json":
            content = json.dumps(
                {"memories": memory_dicts, "count": len(memory_dicts)},
                indent=2,
                ensure_ascii=False,
            )
        else:
            content = _format_memories_markdown(memory_dicts)

        result = {
            "format": format,
            "memory_count": len(memories),
        }

        if output_path:
            try:
                path = Path(output_path)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
                result["output_path"] = str(path.absolute())
                result["message"] = f"Exported {len(memories)} memories to {path}"
            except Exception as e:
                result["error"] = f"Failed to write file: {e}"
                result["content"] = content
        else:
            result["content"] = content

        return result

    finally:
        db.close()


def _format_memories_markdown(memories: List[Dict[str, Any]]) -> str:
    """Format memories list as Markdown."""
    lines = []

    lines.append("# GMemory Export")
    lines.append("")
    lines.append(f"**Total Memories**: {len(memories)}")
    lines.append("")

    for i, mem in enumerate(memories, 1):
        lines.append(f"## {i}. {mem.get('id', 'unknown')}")
        lines.append("")

        # Metadata
        tags = mem.get("tags", [])
        if tags:
            lines.append(f"**Tags**: `{', '.join(tags)}`")

        importance = mem.get("importance", "medium")
        created = mem.get("created_at")
        project = mem.get("project_path", "")

        meta_parts = [f"**Importance**: {importance}"]
        if created:
            meta_parts.append(f"**Created**: {_format_timestamp(created)}")
        if project:
            meta_parts.append(f"**Project**: {project}")

        lines.append(" | ".join(meta_parts))
        lines.append("")

        # Content
        content = mem.get("content", "")
        lines.append("```")
        lines.append(content)
        lines.append("```")
        lines.append("")

    # Footer
    lines.append("---")
    lines.append(f"*Exported from GMemory on {_format_timestamp(int(time.time()))}*")

    return "\n".join(lines)
