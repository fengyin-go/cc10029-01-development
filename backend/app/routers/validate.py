"""采集校验 分析看板接口：汇总指标、参数运行与结果导出。

质量趋势数据报告的校验结论同步到本模块的校验趋势记录台账，
页面汇总与运行分析只读同一份可见发布批次的记录。
"""
from __future__ import annotations

import csv
import io
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from app.schemas import ActionPayload, ActionResult, EntryPayload
from app.services.validate import ValidateService

router = APIRouter(prefix="/api/validate", tags=["采集校验"])
service = ValidateService()
LIST_FIELDS = ["规则编号", "校验字段", "期望格式", "空值阈值", "重复判定", "异常策略", "阻断级别", "校验批次"]
STATUSES = ["草稿", "待校验", "已启用", "已停用"]


def csv_cell(value: Any) -> str:
    text = str(value) if value is not None else ""
    if text and text[0] in "=+-@":
        text = "'" + text
    return '"' + text.replace('"', '""') + '"'


@router.get("/summary")
def get_summary() -> dict[str, Any]:
    """看板卡片：样本数、异常数与达标率来自质量趋势同步过来的校验趋势记录。"""
    records = service.trend_records()
    total = sum(int(item.get("样本数量", 0)) for item in records)
    abnormal = sum(int(item.get("异常数", 0)) for item in records)
    periods = {str(item.get("统计周期")) for item in records}
    return {"metrics": [
        {"label": "统计周期数", "value": len(periods), "trend": 0},
        {"label": "校验样本数", "value": total, "trend": 0},
        {"label": "异常样本数", "value": abnormal, "trend": 0},
        {"label": "达标率", "value": round((total - abnormal) / total, 6) if total else 0.0, "trend": 0},
    ]}


@router.get("/trend-records")
def list_trend_records() -> dict[str, Any]:
    """校验趋势记录台账（质量趋势数据报告同步而来）。"""
    return {"items": service.trend_records()}


@router.get("/anomaly-records")
def list_anomaly_records() -> dict[str, Any]:
    """采集校验异常处置台账（质量趋势的异常结论回写而来）。"""
    return {"items": service.anomaly_records()}


@router.get("")
def list_results() -> dict[str, Any]:
    return {"items": service.list_results()}


@router.post("/run")
def run_analysis(payload: EntryPayload) -> dict[str, Any]:
    results = service.run_analysis(payload.values)
    return {"items": results}


@router.get("/export")
def export_entries() -> StreamingResponse:
    items = service.list_results()
    buf = io.StringIO(newline="")
    writer = csv.writer(buf)
    all_keys = ["id"]
    if items:
        all_keys = list(items[0].keys())
    writer.writerow(all_keys)
    for item in items:
        writer.writerow([csv_cell(item.get(k, "")) for k in all_keys])
    buf.seek(0)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv; charset=utf-8",
                             headers={"Content-Disposition": "attachment; filename=validate.csv"})


@router.get("/{entry_id}")
def get_entry(entry_id: int) -> dict:
    entry = service.get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"校验规则 {entry_id} 不存在")
    return entry
