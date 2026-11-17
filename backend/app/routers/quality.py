"""质量报告 分析看板接口：汇总指标、参数运行与结果导出。

质量趋势数据报告由质量报告提供视图：`/api/quality/trends` 在列表呈现，
本模块的汇总与运行分析读同一份可见发布批次。
"""
from __future__ import annotations

import csv
import io
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas import EntryPayload
from app.services.quality import QualityService

router = APIRouter(prefix="/api/quality", tags=["质量报告"])
service = QualityService()
LIST_FIELDS = ["指标编号", "指标名称", "统计口径", "阈值下界", "阈值上界", "统计周期", "样本数量", "达标率"]
STATUSES = ["草稿", "待校验", "已启用", "已停用"]


def csv_cell(value: Any) -> str:
    text = str(value) if value is not None else ""
    if text and text[0] in "=+-@":
        text = "'" + text
    return '"' + text.replace('"', '""') + '"'


@router.get("/summary")
def get_summary() -> dict[str, Any]:
    """看板卡片：样本数量、异常数与达标率都取最新可见趋势批次。"""
    reports = service.trend_reports()
    latest = reports[0] if reports else {}
    return {"metrics": [
        {"label": "统计周期", "value": latest.get("统计周期", "—"), "trend": 0},
        {"label": "样本数量", "value": latest.get("样本数量", 0), "trend": 0},
        {"label": "异常数", "value": latest.get("异常数", 0), "trend": 0},
        {"label": "达标率", "value": latest.get("达标率", 0.0), "trend": 0},
    ]}


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
                             headers={"Content-Disposition": "attachment; filename=quality.csv"})


@router.get("/{entry_id}")
def get_entry(entry_id: int) -> dict:
    entry = service.get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"质量指标 {entry_id} 不存在")
    return entry
