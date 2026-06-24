from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def percentile_interpretation(samples: int) -> str:
    if samples < 20:
        return (
            f"samples={samples}에서는 현재 ceil 기반 percentile 계산상 p95/p99가 max와 같아지기 쉽다. "
            "large 기본값을 100으로 올려 tail latency가 단일 outlier에 과하게 끌려가지 않도록 한다."
        )
    return (
        f"samples={samples}에서는 p95가 정렬값의 95번째 샘플, p99가 99번째 샘플에 가까워진다. "
        "단일 max와 tail percentile을 분리해서 해석할 수 있다."
    )


def explain_postgres_sql(
    session: Session,
    *,
    label: str,
    sql: str,
    params: Mapping[str, Any],
    query_shape: str,
    index_decision: str,
    data_analysis: str,
) -> dict[str, Any]:
    raw_plan = session.execute(
        text(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {sql}"),
        dict(params),
    ).scalar_one()
    plan_document = raw_plan[0] if isinstance(raw_plan, list) else raw_plan
    plan = plan_document["Plan"]
    nodes = list(_walk_postgres_plan(plan))
    scan_nodes = [node for node in nodes if "Scan" in str(node.get("Node Type", ""))]
    node_types = sorted({str(node.get("Node Type", "")) for node in nodes if node.get("Node Type")})
    indexes = sorted({str(node["Index Name"]) for node in scan_nodes if node.get("Index Name")})
    has_index_scan = any(
        "Index" in str(node.get("Node Type", "")) or "Bitmap" in str(node.get("Node Type", ""))
        for node in scan_nodes
    )
    has_seq_scan = any("Seq Scan" == str(node.get("Node Type", "")) for node in scan_nodes)
    if has_index_scan:
        scan_type = "index_scan"
    elif has_seq_scan:
        scan_type = "seq_scan"
    else:
        scan_type = str(plan.get("Node Type", "unknown")).lower().replace(" ", "_")
    return {
        "label": label,
        "queryShape": query_shape,
        "scanType": scan_type,
        "indexUsed": has_index_scan,
        "indexes": indexes,
        "nodeTypes": node_types,
        "actualRows": int(sum(float(node.get("Actual Rows", 0)) for node in scan_nodes) or float(plan.get("Actual Rows", 0))),
        "estimatedRows": int(sum(float(node.get("Plan Rows", 0)) for node in scan_nodes) or float(plan.get("Plan Rows", 0))),
        "bufferHits": int(sum(int(node.get("Shared Hit Blocks", 0)) for node in nodes)),
        "bufferReads": int(sum(int(node.get("Shared Read Blocks", 0)) for node in nodes)),
        "planningMs": float(plan_document.get("Planning Time", 0.0)),
        "executionMs": float(plan_document.get("Execution Time", 0.0)),
        "indexDecision": index_decision,
        "dataAnalysis": data_analysis,
    }


async def explain_mongo_find(
    collection: Any,
    *,
    label: str,
    filter_query: Mapping[str, Any],
    sort: Mapping[str, int] | None,
    limit: int | None = None,
    query_shape: str,
    index_decision: str,
    data_analysis: str,
) -> dict[str, Any]:
    command: dict[str, Any] = {
        "find": collection.name,
        "filter": dict(filter_query),
    }
    if sort:
        command["sort"] = dict(sort)
    if limit is not None:
        command["limit"] = limit

    explain = await collection.database.command(
        "explain",
        command,
        verbosity="executionStats",
    )
    execution = explain.get("executionStats", {})
    query_planner = explain.get("queryPlanner", {})
    winning_plan = query_planner.get("winningPlan", {})
    stages = list(_walk_plan(winning_plan))
    indexes = sorted({str(stage["indexName"]) for stage in stages if stage.get("indexName")})
    stage_names = sorted({str(stage.get("stage", "")) for stage in stages if stage.get("stage")})
    if "IDHACK" in stage_names and not indexes:
        indexes = ["_id_"]
    return {
        "label": label,
        "queryShape": query_shape,
        "scanType": "index_scan" if "IXSCAN" in stage_names or "IDHACK" in stage_names else "collection_scan",
        "indexUsed": bool(indexes),
        "indexes": indexes,
        "nodeTypes": stage_names,
        "actualRows": int(execution.get("nReturned", 0)),
        "docsExamined": int(execution.get("totalDocsExamined", 0)),
        "keysExamined": int(execution.get("totalKeysExamined", 0)),
        "executionMs": float(execution.get("executionTimeMillis", 0)),
        "indexDecision": index_decision,
        "dataAnalysis": data_analysis,
    }


def _walk_plan(plan: Any):
    if isinstance(plan, dict):
        yield plan
        for key in ("inputStage", "inputStages", "shards", "winningPlan", "queryPlan"):
            child = plan.get(key)
            if child is None:
                continue
            if isinstance(child, list):
                for item in child:
                    yield from _walk_plan(item)
            else:
                yield from _walk_plan(child)
    elif isinstance(plan, list):
        for item in plan:
            yield from _walk_plan(item)


def _walk_postgres_plan(plan: Mapping[str, Any]):
    yield plan
    for child in plan.get("Plans", []):
        yield from _walk_postgres_plan(child)
