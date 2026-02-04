"""Index health check for GMemory.

Provides comprehensive health diagnostics for all database indexes
including vector, FTS, and tag indexes.
"""

import logging
import time
from typing import Any, Dict, List, Optional

from gmemory.config import config
from gmemory.storage.database import MemoryDatabase

logger = logging.getLogger(__name__)


def check_index_health(verbose: bool = False) -> Dict[str, Any]:
    """Perform comprehensive health check on all indexes.

    Args:
        verbose: If True, include detailed per-index statistics.

    Returns:
        Dict with health status, issues, and recommendations.
    """
    db = MemoryDatabase()
    try:
        health: Dict[str, Any] = {
            "status": "healthy",
            "timestamp": time.time(),
            "checks": {},
            "issues": [],
            "recommendations": [],
        }

        # 1. Check memory counts
        mem_check = _check_memory_counts(db)
        health["checks"]["memories"] = mem_check
        if mem_check.get("issues"):
            health["issues"].extend(mem_check["issues"])

        # 2. Check vector index
        vec_check = _check_vector_index(db, verbose)
        health["checks"]["vector_index"] = vec_check
        if vec_check.get("issues"):
            health["issues"].extend(vec_check["issues"])

        # 3. Check FTS index
        fts_check = _check_fts_index(db, verbose)
        health["checks"]["fts_index"] = fts_check
        if fts_check.get("issues"):
            health["issues"].extend(fts_check["issues"])

        # 4. Check tag index
        tag_check = _check_tag_index(db, verbose)
        health["checks"]["tag_index"] = tag_check
        if tag_check.get("issues"):
            health["issues"].extend(tag_check["issues"])

        # 5. Check dimension consistency
        dim_check = _check_dimension_consistency(db)
        health["checks"]["dimensions"] = dim_check
        if dim_check.get("issues"):
            health["issues"].extend(dim_check["issues"])

        # 6. Check for orphaned records
        orphan_check = _check_orphaned_records(db)
        health["checks"]["orphans"] = orphan_check
        if orphan_check.get("issues"):
            health["issues"].extend(orphan_check["issues"])

        # Determine overall status
        if health["issues"]:
            critical_issues = [
                i for i in health["issues"] if i.get("severity") == "critical"
            ]
            warning_issues = [
                i for i in health["issues"] if i.get("severity") == "warning"
            ]

            if critical_issues:
                health["status"] = "critical"
            elif warning_issues:
                health["status"] = "warning"
            else:
                health["status"] = "info"

        # Generate recommendations
        health["recommendations"] = _generate_recommendations(health["issues"])

        # Summary
        health["summary"] = {
            "total_memories": mem_check.get("total", 0),
            "vector_coverage": vec_check.get("coverage_percent", 0),
            "fts_coverage": fts_check.get("coverage_percent", 0),
            "tag_coverage": tag_check.get("coverage_percent", 0),
            "issue_count": len(health["issues"]),
            "status": health["status"],
        }

        return health

    finally:
        db.close()


def _check_memory_counts(db: MemoryDatabase) -> Dict[str, Any]:
    """Check basic memory table statistics."""
    result: Dict[str, Any] = {"status": "ok", "issues": []}

    try:
        cursor = db.conn.execute("SELECT COUNT(*) FROM memories")
        total = cursor.fetchone()[0]
        result["total"] = total

        # Check for superseded memories
        cursor = db.conn.execute(
            "SELECT COUNT(*) FROM memories WHERE superseded_by IS NOT NULL"
        )
        superseded = cursor.fetchone()[0]
        result["superseded"] = superseded
        result["active"] = total - superseded

        if total == 0:
            result["status"] = "empty"
            result["issues"].append(
                {
                    "type": "empty_database",
                    "severity": "info",
                    "message": "Database is empty. No memories stored yet.",
                }
            )

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        result["issues"].append(
            {
                "type": "memory_table_error",
                "severity": "critical",
                "message": f"Failed to query memories table: {e}",
            }
        )

    return result


def _check_vector_index(db: MemoryDatabase, verbose: bool = False) -> Dict[str, Any]:
    """Check vector index health."""
    result: Dict[str, Any] = {"status": "ok", "issues": []}

    try:
        # Count vectors
        cursor = db.conn.execute("SELECT COUNT(*) FROM vec_memories")
        vec_count = cursor.fetchone()[0]
        result["count"] = vec_count

        # Count memories
        cursor = db.conn.execute("SELECT COUNT(*) FROM memories")
        mem_count = cursor.fetchone()[0]
        result["expected"] = mem_count

        # Calculate coverage
        if mem_count > 0:
            coverage = (vec_count / mem_count) * 100
            result["coverage_percent"] = round(coverage, 1)
            result["missing"] = mem_count - vec_count

            if coverage < 100:
                severity = "critical" if coverage < 50 else "warning"
                result["status"] = severity
                result["issues"].append(
                    {
                        "type": "vector_coverage_gap",
                        "severity": severity,
                        "message": f"Vector index missing {mem_count - vec_count} embeddings ({100 - coverage:.1f}% gap)",
                        "fix": "gmemory reindex --target=embeddings --apply",
                    }
                )
        else:
            result["coverage_percent"] = 100
            result["missing"] = 0

        # Check if sqlite-vec is loaded
        if not db._vec_loaded:
            result["status"] = "critical"
            result["issues"].append(
                {
                    "type": "sqlite_vec_not_loaded",
                    "severity": "critical",
                    "message": f"sqlite-vec extension not loaded: {db._vec_load_error}",
                    "fix": "pip install sqlite-vec",
                }
            )

        if verbose and vec_count > 0:
            # Sample check - verify a few vectors are queryable
            try:
                test_vec = [0.0] * config.embedding_dimension
                test_blob = db._serialize_float32(test_vec)
                cursor = db.conn.execute(
                    "SELECT memory_id FROM vec_memories WHERE embedding MATCH ? AND k = 1",
                    (test_blob,),
                )
                cursor.fetchone()
                result["queryable"] = True
            except Exception as e:
                result["queryable"] = False
                result["query_error"] = str(e)
                result["issues"].append(
                    {
                        "type": "vector_query_failed",
                        "severity": "critical",
                        "message": f"Vector index not queryable: {e}",
                        "fix": "gmemory reindex --target=embeddings --apply",
                    }
                )

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        result["issues"].append(
            {
                "type": "vector_index_error",
                "severity": "critical",
                "message": f"Failed to check vector index: {e}",
            }
        )

    return result


def _check_fts_index(db: MemoryDatabase, verbose: bool = False) -> Dict[str, Any]:
    """Check FTS5 index health."""
    result: Dict[str, Any] = {"status": "ok", "issues": []}

    try:
        # Count FTS entries
        cursor = db.conn.execute("SELECT COUNT(*) FROM memories_fts")
        fts_count = cursor.fetchone()[0]
        result["count"] = fts_count

        # Count memories
        cursor = db.conn.execute("SELECT COUNT(*) FROM memories")
        mem_count = cursor.fetchone()[0]
        result["expected"] = mem_count

        # Calculate coverage
        if mem_count > 0:
            coverage = (fts_count / mem_count) * 100
            result["coverage_percent"] = round(coverage, 1)
            result["missing"] = mem_count - fts_count

            if coverage < 100:
                severity = "warning" if coverage > 80 else "critical"
                result["status"] = severity
                result["issues"].append(
                    {
                        "type": "fts_coverage_gap",
                        "severity": severity,
                        "message": f"FTS index missing {mem_count - fts_count} entries ({100 - coverage:.1f}% gap)",
                        "fix": "gmemory reindex --target=fts --apply",
                    }
                )
        else:
            result["coverage_percent"] = 100
            result["missing"] = 0

        if verbose and fts_count > 0:
            # Test FTS query
            try:
                cursor = db.conn.execute(
                    "SELECT memory_id FROM memories_fts WHERE memories_fts MATCH 'test' LIMIT 1"
                )
                result["queryable"] = True
            except Exception as e:
                result["queryable"] = False
                result["query_error"] = str(e)
                # FTS query errors are usually not critical
                result["issues"].append(
                    {
                        "type": "fts_query_warning",
                        "severity": "info",
                        "message": f"FTS test query returned error (may be normal): {e}",
                    }
                )

        # Check FTS integrity
        if verbose:
            try:
                cursor = db.conn.execute(
                    "INSERT INTO memories_fts(memories_fts) VALUES('integrity-check')"
                )
                result["integrity"] = "ok"
            except Exception as e:
                result["integrity"] = "failed"
                result["integrity_error"] = str(e)
                result["issues"].append(
                    {
                        "type": "fts_integrity_failed",
                        "severity": "warning",
                        "message": f"FTS integrity check failed: {e}",
                        "fix": "gmemory reindex --target=fts --apply",
                    }
                )

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        result["issues"].append(
            {
                "type": "fts_index_error",
                "severity": "critical",
                "message": f"Failed to check FTS index: {e}",
            }
        )

    return result


def _check_tag_index(db: MemoryDatabase, verbose: bool = False) -> Dict[str, Any]:
    """Check tag vector index health."""
    result: Dict[str, Any] = {"status": "ok", "issues": []}

    try:
        # Check if tag index exists
        cursor = db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='vec_tags'"
        )
        if not cursor.fetchone():
            result["exists"] = False
            result["count"] = 0
            result["coverage_percent"] = 0
            result["issues"].append(
                {
                    "type": "tag_index_missing",
                    "severity": "info",
                    "message": "Tag index table does not exist. Run migration or reindex.",
                    "fix": "gmemory reindex --target=tags --apply",
                }
            )
            return result

        result["exists"] = True

        # Count tag vectors
        cursor = db.conn.execute("SELECT COUNT(*) FROM vec_tags")
        tag_count = cursor.fetchone()[0]
        result["count"] = tag_count

        # Count memories with tags
        cursor = db.conn.execute(
            "SELECT COUNT(*) FROM memories WHERE tags IS NOT NULL AND tags != ''"
        )
        tagged_count = cursor.fetchone()[0]
        result["expected"] = tagged_count

        # Calculate coverage
        if tagged_count > 0:
            coverage = (tag_count / tagged_count) * 100
            result["coverage_percent"] = round(coverage, 1)
            result["missing"] = tagged_count - tag_count

            if coverage < 100:
                result["status"] = "warning"
                result["issues"].append(
                    {
                        "type": "tag_coverage_gap",
                        "severity": "warning",
                        "message": f"Tag index missing {tagged_count - tag_count} entries ({100 - coverage:.1f}% gap)",
                        "fix": "gmemory reindex --target=tags --apply",
                    }
                )
        else:
            result["coverage_percent"] = 100 if tag_count == 0 else 0
            result["missing"] = 0

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        # Tag index errors are not critical
        result["issues"].append(
            {
                "type": "tag_index_error",
                "severity": "warning",
                "message": f"Failed to check tag index: {e}",
            }
        )

    return result


def _check_dimension_consistency(db: MemoryDatabase) -> Dict[str, Any]:
    """Check that vector dimensions are consistent."""
    result: Dict[str, Any] = {"status": "ok", "issues": []}

    result["configured_dimension"] = config.embedding_dimension
    result["model"] = config.embedding_model

    try:
        # Try to query with configured dimension
        cursor = db.conn.execute("SELECT COUNT(*) FROM vec_memories")
        count = cursor.fetchone()[0]

        if count > 0:
            test_vec = [0.0] * config.embedding_dimension
            test_blob = db._serialize_float32(test_vec)
            try:
                cursor = db.conn.execute(
                    "SELECT memory_id FROM vec_memories WHERE embedding MATCH ? AND k = 1",
                    (test_blob,),
                )
                cursor.fetchone()
                result["dimension_match"] = True
            except Exception as e:
                error_msg = str(e).lower()
                if "dimension" in error_msg or "vector" in error_msg:
                    result["dimension_match"] = False
                    result["status"] = "critical"
                    result["issues"].append(
                        {
                            "type": "dimension_mismatch",
                            "severity": "critical",
                            "message": f"Vector dimension mismatch. Config: {config.embedding_dimension}, but index has different dimension.",
                            "fix": "gmemory reindex --target=embeddings --apply",
                        }
                    )
                else:
                    result["dimension_match"] = "unknown"
                    result["check_error"] = str(e)
        else:
            result["dimension_match"] = "n/a"

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)

    return result


def _check_orphaned_records(db: MemoryDatabase) -> Dict[str, Any]:
    """Check for orphaned records in index tables."""
    result: Dict[str, Any] = {"status": "ok", "issues": []}

    try:
        # Check for orphaned vectors (vectors without memories)
        cursor = db.conn.execute("""
            SELECT COUNT(*) FROM vec_memories 
            WHERE memory_id NOT IN (SELECT id FROM memories)
        """)
        orphaned_vectors = cursor.fetchone()[0]
        result["orphaned_vectors"] = orphaned_vectors

        # Check for orphaned FTS entries
        cursor = db.conn.execute("""
            SELECT COUNT(*) FROM memories_fts 
            WHERE memory_id NOT IN (SELECT id FROM memories)
        """)
        orphaned_fts = cursor.fetchone()[0]
        result["orphaned_fts"] = orphaned_fts

        # Check for orphaned tag vectors
        try:
            cursor = db.conn.execute("""
                SELECT COUNT(*) FROM vec_tags 
                WHERE memory_id NOT IN (SELECT id FROM memories)
            """)
            orphaned_tags = cursor.fetchone()[0]
            result["orphaned_tags"] = orphaned_tags
        except Exception:
            result["orphaned_tags"] = 0

        total_orphans = orphaned_vectors + orphaned_fts + result["orphaned_tags"]
        result["total_orphans"] = total_orphans

        if total_orphans > 0:
            result["status"] = "warning"
            result["issues"].append(
                {
                    "type": "orphaned_records",
                    "severity": "warning",
                    "message": f"Found {total_orphans} orphaned index records (vec: {orphaned_vectors}, fts: {orphaned_fts}, tags: {result['orphaned_tags']})",
                    "fix": "gmemory compact --rebuild-fts",
                }
            )

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)

    return result


def _generate_recommendations(issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate prioritized recommendations based on issues."""
    recommendations = []
    seen_fixes = set()

    # Sort issues by severity
    severity_order = {"critical": 0, "warning": 1, "info": 2}
    sorted_issues = sorted(
        issues, key=lambda x: severity_order.get(x.get("severity", "info"), 3)
    )

    for issue in sorted_issues:
        fix = issue.get("fix")
        if fix and fix not in seen_fixes:
            seen_fixes.add(fix)
            recommendations.append(
                {
                    "priority": len(recommendations) + 1,
                    "issue": issue.get("type"),
                    "severity": issue.get("severity"),
                    "action": issue.get("message"),
                    "command": fix,
                }
            )

    return recommendations


def quick_health_check() -> Dict[str, Any]:
    """Perform a quick health check (less detailed, faster).

    Returns:
        Dict with basic health status.
    """
    db = MemoryDatabase()
    try:
        # Quick counts
        cursor = db.conn.execute("SELECT COUNT(*) FROM memories")
        mem_count = cursor.fetchone()[0]

        cursor = db.conn.execute("SELECT COUNT(*) FROM vec_memories")
        vec_count = cursor.fetchone()[0]

        cursor = db.conn.execute("SELECT COUNT(*) FROM memories_fts")
        fts_count = cursor.fetchone()[0]

        # Determine status
        issues = []
        if mem_count > 0:
            vec_coverage = vec_count / mem_count
            fts_coverage = fts_count / mem_count

            if vec_coverage < 0.5:
                issues.append("critical: vector index < 50% coverage")
            elif vec_coverage < 1.0:
                issues.append("warning: vector index incomplete")

            if fts_coverage < 0.8:
                issues.append("warning: FTS index incomplete")

        status = "healthy"
        if any("critical" in i for i in issues):
            status = "critical"
        elif any("warning" in i for i in issues):
            status = "warning"

        return {
            "status": status,
            "memories": mem_count,
            "vectors": vec_count,
            "fts_entries": fts_count,
            "vec_loaded": db._vec_loaded,
            "issues": issues if issues else None,
        }

    finally:
        db.close()
