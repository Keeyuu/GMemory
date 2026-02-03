from dataclasses import dataclass, field, asdict
from typing import List, Optional, Any, Dict
import json
import time


@dataclass
class Message:
    """Represents a single message in a session."""

    role: str
    content: str

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "Message":
        return cls(**data)


@dataclass
class Session:
    """Represents a conversation session from an agent."""

    session_id: str
    agent: str
    project_path: str
    project_name: str
    started_at: str
    messages: List[Message] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Session":
        messages = [
            Message.from_dict(m) if isinstance(m, dict) else m
            for m in data.get("messages", [])
        ]
        return cls(
            session_id=data["session_id"],
            agent=data["agent"],
            project_path=data["project_path"],
            project_name=data["project_name"],
            started_at=data["started_at"],
            messages=messages,
        )


@dataclass
class Memory:
    """Represents a refined memory entry."""

    id: str
    content: str
    tags: List[str] = field(default_factory=list)
    importance: str = "medium"
    memory_type: Optional[str] = None
    agent: str = "opencode"
    source_session_id: Optional[str] = None
    project_path: Optional[str] = None
    project_name: Optional[str] = None
    created_at: int = field(default_factory=lambda: int(time.time()))
    updated_at: int = field(default_factory=lambda: int(time.time()))

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Memory":
        tags = data.get("tags", [])
        if isinstance(tags, str):
            try:
                tags = json.loads(tags)
            except json.JSONDecodeError:
                tags = [t.strip() for t in tags.split(",") if t.strip()]

        return cls(
            id=data["id"],
            content=data["content"],
            tags=tags,
            importance=data.get("importance", "medium"),
            memory_type=data.get("memory_type"),
            agent=data.get("agent", "opencode"),
            source_session_id=data.get("source_session_id"),
            project_path=data.get("project_path"),
            project_name=data.get("project_name"),
            created_at=data.get("created_at", int(time.time())),
            updated_at=data.get("updated_at", int(time.time())),
        )


@dataclass
class ProcessedSession:
    """Represents a session that has been processed and refined."""

    agent: str
    session_id: str
    processed_at: int = field(default_factory=lambda: int(time.time()))

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProcessedSession":
        return cls(**data)
