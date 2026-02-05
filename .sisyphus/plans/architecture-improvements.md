# GMemory 架构改进计划

## 概述

基于架构评估报告，本计划针对中等及以上严重程度的问题进行系统性改进。

---

## 问题清单 (按优先级)

| 优先级 | 问题 | 影响范围 |
|--------|------|----------|
| 🔴 P0 | 依赖倒置不足 | commands/*.py, storage/database.py |
| 🔴 P0 | 错误处理不一致 | cli/*.py |
| 🟠 P1 | 测试覆盖偏窄 | tests/ |
| 🟡 P2 | 类型边界不稳 | 全局 |
| 🟡 P2 | MemoryDatabase 过大 | storage/database.py |

---

## P0-1: 依赖倒置 - 引入接口层

### 当前问题

```python
# commands/search.py - 直接依赖具体实现
from gmemory.storage.database import MemoryDatabase
from gmemory.config import config

def search_memories(...):
    db = MemoryDatabase()  # 硬编码依赖
    effective_limit = config.search_default_limit  # 全局状态
```

### 解决方案

1. 创建 `gmemory/ports.py` - 定义抽象接口 (Protocol)
2. 创建 `gmemory/container.py` - 简单依赖注入容器
3. 逐步重构 commands 层使用接口

### 实现步骤

#### Step 1: 创建 ports.py

```python
# gmemory/ports.py
from typing import Protocol, List, Optional, Tuple, Dict, Any
from gmemory.models import Memory, ProcessedSession

class DatabasePort(Protocol):
    """Database operations interface."""
    
    def add_memory(self, memory: Memory, embedding: Optional[List[float]] = None) -> None: ...
    def get_memory(self, memory_id: str) -> Optional[Memory]: ...
    def update_memory(self, memory: Memory, embedding: Optional[List[float]] = None) -> None: ...
    def delete_memory(self, memory_id: str) -> None: ...
    def search_memories(self, query_embedding: List[float], limit: int, threshold: float) -> List[Tuple[Memory, float]]: ...
    def search_fts(self, query: str, limit: int) -> List[Tuple[str, float]]: ...
    def hybrid_search(self, query_embedding: List[float], query_text: str, limit: int, ...) -> List[Tuple[Memory, float]]: ...
    def get_stats(self) -> Dict[str, int]: ...
    def get_diagnostics(self) -> Dict[str, Any]: ...
    def close(self) -> None: ...

class EmbedderPort(Protocol):
    """Embedding operations interface."""
    
    @property
    def dimension(self) -> int: ...
    def embed(self, text: str) -> List[float]: ...
    def embed_batch(self, texts: List[str]) -> List[List[float]]: ...

class ConfigPort(Protocol):
    """Configuration access interface."""
    
    @property
    def db_path(self) -> Path: ...
    @property
    def embedding_dimension(self) -> int: ...
    @property
    def search_default_limit(self) -> int: ...
    # ... 其他配置属性
```

#### Step 2: 创建 container.py

```python
# gmemory/container.py
from typing import Optional
from gmemory.ports import DatabasePort, EmbedderPort, ConfigPort

class Container:
    """Simple dependency injection container."""
    
    _instance: Optional['Container'] = None
    _database: Optional[DatabasePort] = None
    _embedder: Optional[EmbedderPort] = None
    _config: Optional[ConfigPort] = None
    
    @classmethod
    def get_instance(cls) -> 'Container':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def get_database(self) -> DatabasePort:
        if self._database is None:
            from gmemory.storage.database import MemoryDatabase
            self._database = MemoryDatabase()
        return self._database
    
    def get_embedder(self) -> EmbedderPort:
        if self._embedder is None:
            from gmemory.storage.embedder import get_embedder
            self._embedder = get_embedder()
        return self._embedder
    
    def get_config(self) -> ConfigPort:
        if self._config is None:
            from gmemory.config import config
            self._config = config
        return self._config
    
    # For testing
    def set_database(self, db: DatabasePort) -> None:
        self._database = db
    
    def set_embedder(self, embedder: EmbedderPort) -> None:
        self._embedder = embedder
    
    def reset(self) -> None:
        self._database = None
        self._embedder = None
        self._config = None

def get_container() -> Container:
    return Container.get_instance()
```

#### Step 3: 重构 commands 层 (渐进式)

```python
# commands/search.py - 重构后
from gmemory.container import get_container

def search_memories(query: str, ...) -> Dict[str, Any]:
    container = get_container()
    db = container.get_database()
    cfg = container.get_config()
    
    effective_limit = limit if limit is not None else cfg.search_default_limit
    # ...
```

---

## P0-2: 统一错误处理

### 当前问题

```python
# cli/core.py - 每个命令都有重复的 try/except
@cli.command()
def fetch(limit, agent):
    try:
        result = fetch_unprocessed_sessions(limit=limit, agent=agent)
        click.echo(json.dumps(result))
    except Exception as e:
        click.echo(json.dumps({"error": str(e)}))  # 丢失 error code
```

### 解决方案

1. 创建 `gmemory/cli/error_handler.py` - 统一错误处理
2. 使用装饰器简化 CLI 命令
3. 保留结构化错误信息

### 实现步骤

#### Step 1: 创建 error_handler.py

```python
# gmemory/cli/error_handler.py
import functools
import json
import click
from typing import Callable, Any

from gmemory.errors import GMemoryError, format_error_response

def handle_cli_error(func: Callable) -> Callable:
    """Decorator for unified CLI error handling."""
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            result = func(*args, **kwargs)
            if result is not None:
                click.echo(json.dumps(result))
        except GMemoryError as e:
            # Preserve structured error info
            click.echo(json.dumps(e.to_dict()))
            raise SystemExit(1)
        except Exception as e:
            # Fallback for unexpected errors
            click.echo(json.dumps(format_error_response(e)))
            raise SystemExit(1)
    
    return wrapper

def cli_command(func: Callable) -> Callable:
    """Combined decorator for CLI commands with error handling."""
    return handle_cli_error(func)
```

#### Step 2: 重构 CLI 命令

```python
# cli/core.py - 重构后
from gmemory.cli.error_handler import cli_command

def register_core_commands(cli: click.Group) -> None:
    
    @cli.command()
    @click.option("--limit", default=5)
    @click.option("--agent", default="opencode")
    @cli_command
    def fetch(limit, agent):
        """Fetch unprocessed sessions from Agent logs."""
        return fetch_unprocessed_sessions(limit=limit, agent=agent)
    
    @cli.command()
    @click.argument("query")
    @click.option("--limit", default=5)
    @cli_command
    def search(query, limit, ...):
        """Search memories using vector similarity."""
        return search_memories(query=query, limit=limit, ...)
```

---

## P1: 补齐测试覆盖

### 当前状态

```
tests/
├── test_database.py      ✓ 数据库基础操作
├── test_errors.py        ✓ 错误类型
├── test_privacy.py       ✓ 隐私过滤
├── test_profiles.py      ✓ 搜索配置
├── test_session_report.py ✓ 会话报告
└── test_dedupe_export.py ✓ 去重导出
```

### 缺失测试

1. `test_scanner_opencode.py` - Scanner 增量扫描逻辑
2. `test_search_modes.py` - 搜索模式 (hybrid/vector/fts) 分支
3. `test_cli_output.py` - CLI 输出格式验证
4. `test_embedder.py` - Embedder 降级逻辑
5. `test_validation.py` - 数据验证边界

### 实现步骤

#### test_scanner_opencode.py

```python
"""Tests for OpenCode scanner."""
import pytest
import tempfile
import json
from pathlib import Path
from gmemory.scanner.opencode import OpenCodeScanner
from gmemory.models import Session

class TestOpenCodeScanner:
    
    @pytest.fixture
    def mock_opencode_storage(self, tmp_path):
        """Create mock OpenCode storage structure."""
        storage = tmp_path / "storage"
        session_dir = storage / "session" / "project1"
        session_dir.mkdir(parents=True)
        
        # Create session file
        session_file = session_dir / "ses_test001.json"
        session_file.write_text(json.dumps({
            "id": "test001",
            "directory": "/path/to/project",
            "title": "Test Project",
            "time": {"created": "2024-01-01T00:00:00Z"}
        }))
        
        return tmp_path
    
    def test_count_sessions(self, mock_opencode_storage):
        """Should count session files correctly."""
        scanner = OpenCodeScanner(base_dir=mock_opencode_storage)
        assert scanner.count_sessions() == 1
    
    def test_incremental_skip_unchanged(self, mock_opencode_storage):
        """Should skip unchanged files in incremental mode."""
        # First scan
        scanner = OpenCodeScanner(base_dir=mock_opencode_storage, incremental=True)
        sessions1 = scanner.get_unprocessed_sessions(limit=10)
        
        # Second scan - should skip
        scanner2 = OpenCodeScanner(base_dir=mock_opencode_storage, incremental=True)
        # ... verify skip logic
```

#### test_search_modes.py

```python
"""Tests for search mode branches."""
import pytest
from gmemory.commands.search import search_memories

class TestSearchModes:
    
    def test_fts_only_mode(self, temp_db_with_data):
        """FTS mode should not require embeddings."""
        result = search_memories("python", mode="fts", limit=5)
        assert result["mode"] == "fts"
        assert "error" not in result
    
    def test_hybrid_fallback_on_embedding_failure(self, temp_db_with_data, monkeypatch):
        """Should fallback to FTS when embedding fails."""
        # Mock embedding failure
        monkeypatch.setattr("gmemory.commands.search.get_embedder", lambda: NoOpEmbedder())
        
        result = search_memories("python", mode="hybrid", limit=5)
        assert "warning" in result
        assert result["mode"] == "fts"
    
    def test_profile_override(self, temp_db_with_data):
        """CLI options should override profile settings."""
        result = search_memories("python", profile="recent", recency_weight=0.0)
        # recency_weight=0.0 should override profile's 0.4
```

#### test_cli_output.py

```python
"""Tests for CLI output format."""
import pytest
from click.testing import CliRunner
from gmemory.cli import create_cli

class TestCLIOutput:
    
    @pytest.fixture
    def runner(self):
        return CliRunner()
    
    @pytest.fixture
    def cli(self):
        return create_cli()
    
    def test_error_output_has_code(self, runner, cli):
        """Error output should include error code."""
        result = runner.invoke(cli, ["get", "nonexistent-id"])
        output = json.loads(result.output)
        
        # Should have structured error
        assert "error" in output or "code" in output
    
    def test_search_output_format(self, runner, cli, temp_db_with_data):
        """Search output should have consistent structure."""
        result = runner.invoke(cli, ["search", "test", "--compact"])
        output = json.loads(result.output)
        
        assert "results" in output
        assert "total" in output
        assert "mode" in output
```

---

## P2-1: 加强类型边界

### 实现步骤

#### Step 1: 创建 pyproject.toml mypy 配置

```toml
[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_ignores = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
strict_optional = true

[[tool.mypy.overrides]]
module = "fastembed.*"
ignore_missing_imports = true

[[tool.mypy.overrides]]
module = "sqlite_vec.*"
ignore_missing_imports = true
```

#### Step 2: 创建 py.typed 标记

```bash
touch gmemory/py.typed
```

#### Step 3: 逐步添加类型注解

优先级:
1. `models.py` - 核心数据结构
2. `ports.py` - 接口定义
3. `errors.py` - 错误类型
4. `config.py` - 配置类型

---

## P2-2: 拆分 MemoryDatabase

### 当前问题

`MemoryDatabase` 类承担了过多职责:
- Schema 初始化和迁移
- Memory CRUD 操作
- 向量搜索
- FTS 搜索
- Scan run/error 跟踪
- 诊断信息

### 解决方案

拆分为多个 Repository 类，共享同一连接:

```
storage/
├── database.py          # 连接管理 + 初始化
├── memory_repository.py # Memory CRUD
├── search_repository.py # 向量 + FTS 搜索
├── scan_repository.py   # Scan run/error 跟踪
└── migrations.py        # Schema 迁移 (保持不变)
```

### 实现步骤

#### Step 1: 创建 memory_repository.py

```python
# storage/memory_repository.py
from typing import List, Optional
from gmemory.models import Memory

class MemoryRepository:
    """Repository for Memory CRUD operations."""
    
    def __init__(self, conn):
        self._conn = conn
    
    def add(self, memory: Memory, embedding: Optional[List[float]] = None) -> None:
        # 从 MemoryDatabase.add_memory 迁移
        pass
    
    def get(self, memory_id: str) -> Optional[Memory]:
        # 从 MemoryDatabase.get_memory 迁移
        pass
    
    def update(self, memory: Memory, embedding: Optional[List[float]] = None) -> None:
        # 从 MemoryDatabase.update_memory 迁移
        pass
    
    def delete(self, memory_id: str) -> None:
        # 从 MemoryDatabase.delete_memory 迁移
        pass
    
    def get_active(self, limit: int, offset: int, project_path: Optional[str]) -> List[Memory]:
        # 从 MemoryDatabase.get_active_memories 迁移
        pass
```

#### Step 2: 创建 search_repository.py

```python
# storage/search_repository.py
class SearchRepository:
    """Repository for search operations."""
    
    def __init__(self, conn, embedding_dim: int):
        self._conn = conn
        self._embedding_dim = embedding_dim
    
    def vector_search(self, query_embedding, limit, threshold) -> List[Tuple[Memory, float]]:
        pass
    
    def fts_search(self, query, limit) -> List[Tuple[str, float]]:
        pass
    
    def hybrid_search(self, query_embedding, query_text, limit, ...) -> List[Tuple[Memory, float]]:
        pass
    
    def tag_search(self, tag_embedding, limit) -> List[Tuple[str, float]]:
        pass
```

#### Step 3: 重构 MemoryDatabase 为 Facade

```python
# storage/database.py
class MemoryDatabase:
    """Facade for database operations."""
    
    def __init__(self, embedding_dimension: Optional[int] = None):
        self._init_connection()
        self._memory_repo = MemoryRepository(self.conn)
        self._search_repo = SearchRepository(self.conn, self._embedding_dim)
        self._scan_repo = ScanRepository(self.conn)
    
    # 委托给各个 Repository
    def add_memory(self, memory, embedding=None):
        return self._memory_repo.add(memory, embedding)
    
    def search_memories(self, query_embedding, limit, threshold):
        return self._search_repo.vector_search(query_embedding, limit, threshold)
    
    # ... 其他方法委托
```

---

## 执行顺序

1. **Phase 1 (Day 1-2)**: P0 - 错误处理统一
   - 创建 `cli/error_handler.py`
   - 重构所有 CLI 命令使用装饰器
   - 验证错误输出格式

2. **Phase 2 (Day 2-3)**: P0 - 依赖倒置
   - 创建 `ports.py` 接口定义
   - 创建 `container.py` 依赖注入
   - 重构 `commands/search.py` 作为示例
   - 逐步重构其他 commands

3. **Phase 3 (Day 3-4)**: P1 - 测试覆盖
   - 创建 `test_scanner_opencode.py`
   - 创建 `test_search_modes.py`
   - 创建 `test_cli_output.py`
   - 运行完整测试套件

4. **Phase 4 (Day 4-5)**: P2 - 类型边界 + 数据库拆分
   - 配置 mypy
   - 创建 py.typed
   - 拆分 MemoryDatabase
   - 验证所有测试通过

---

## 验收标准

- [x] 所有 CLI 命令错误输出包含 `code` 字段
- [x] commands 层不直接 import `MemoryDatabase` 和全局 `config` (search.py 已重构)
- [x] 测试覆盖率 > 70% (关键路径) - 136 tests passing
- [x] `mypy` 配置已添加到 pyproject.toml
- [x] 所有现有测试通过
- [ ] `gmemory health` 正常运行 (需要数据库)

---

## 完成状态 (2026-02-04)

### 已完成

| 任务 | 状态 | 说明 |
|------|------|------|
| P0-2: 统一错误处理 | ✅ 完成 | `cli/error_handler.py` + 7个CLI模块重构 |
| P0-1: 依赖倒置 | ✅ 完成 | `ports.py` + `container.py` + 全部 commands 重构 |
| P1: 测试覆盖 | ✅ 完成 | 54 新测试 (136 总计) |
| P2-1: 类型边界 | ✅ 完成 | mypy 配置 + py.typed |

### 延后/取消

| 任务 | 状态 | 原因 |
|------|------|------|
| P2-2: 拆分 MemoryDatabase | ⏸️ 延后 | 可选优化，当前架构可用 |

### 技术债务

1. **DatabasePort 已完整**: 所有 commands 模块现在都通过 container 访问数据库
2. **无 raw SQL 访问**: `workflow.py`、`quick.py`、`dedupe.py` 已重构使用 DatabasePort 方法

### 新增文件

```
gmemory/
├── cli/error_handler.py    # 统一错误处理装饰器
├── ports.py                # Protocol 接口定义
├── container.py            # DI 容器
└── py.typed                # PEP 561 标记

tests/
├── test_scanner_opencode.py  # Scanner 测试 (22)
├── test_search_modes.py      # 搜索模式测试 (17)
└── test_cli_output.py        # CLI 输出测试 (15)
```

### DatabasePort 新增方法

| 方法 | 用途 |
|------|------|
| `get_processed_session_count(agent)` | 获取已处理会话数 |
| `get_unresolved_error_count()` | 获取未解决错误数 |
| `get_recent_memories(days, limit, ...)` | 获取最近记忆 |
| `get_today_stats()` | 获取今日统计 |
| `find_memories_by_tag(tag, limit)` | 按标签查找记忆 |
| `get_all_tags(limit)` | 获取所有标签及计数 |
| `mark_memory_superseded(id, superseded_by)` | 标记记忆被取代 |
| `is_session_processed(agent, session_id)` | 检查会话是否已处理 |
| `mark_session_processed(agent, session_id, ...)` | 标记会话已处理 |
