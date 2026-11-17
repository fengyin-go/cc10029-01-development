"""质量趋势数据报告接口：按统计周期生成、读取趋势报告和样本依据。

列表接口延续 `{ items, total, page, size }` 的返回结构；生成报告沿用动作接口的
`{ ok, message }`，额外带上生成的报告与样本快照，方便质量报告页面直接展示。
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.schemas import ActionPayload, ActionResult, EntryPayload, PageResult
from app.services.quality_trend import service

router = APIRouter(prefix="/api/quality/trends", tags=["质量报告"])


@router.get("", response_model=PageResult[dict])
def list_reports(
    period: str | None = Query(default=None, description="统计周期，如 2026-11"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=200),
) -> PageResult[dict]:
    """列出可见的质量趋势数据报告，每个统计周期只出现一份。"""
    items = service.list_reports()
    if period:
        items = [item for item in items if item.get("统计周期") == period]
    total = len(items)
    start = (page - 1) * size
    return PageResult(items=items[start:start + size], total=total, page=page, size=size)


@router.get("/periods")
def list_periods() -> dict[str, Any]:
    """可选统计周期，供操作者切换窗口。"""
    return {"items": service.list_periods()}


@router.get("/ledger/trends")
def list_trend_ledger() -> dict[str, Any]:
    """采集校验侧的校验趋势记录台账：只返回可见发布批次的记录。"""
    return {"items": service.list_trend_records()}


@router.get("/ledger/anomalies")
def list_anomaly_ledger() -> dict[str, Any]:
    """采集校验异常处置台账：质量趋势里的异常结论先落这里再处置。"""
    return {"items": service.list_anomaly_records()}


@router.get("/{period}")
def get_report(period: str) -> dict:
    """读取某统计周期的完整报告：指标数据集、样本快照、迟到样本和台账。"""
    detail = service.get_report(period)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"统计周期 {period} 没有质量趋势数据报告")
    return detail


@router.post("")
def publish_report(payload: EntryPayload) -> ActionResult:
    """用已落库样本计算并发布某统计周期的质量趋势数据报告。

    `values.统计周期` 必填，`values.规则版本` 可选（默认规则A@1），
    `values.样本` 可选：带上时先按样本编号归入该统计周期再重算。
    迟到样本改用 `/late-samples`，避免把旧周期的样本混进新周期的窗口。
    """
    ok, message, report = service.publish(payload.values)
    return ActionResult(ok=ok, message=message, entry=report)


@router.post("/{period}/late-samples")
def add_late_sample(period: str, payload: EntryPayload) -> ActionResult:
    """把迟到样本归入它所属的统计周期，只重算这一个周期的报告。"""
    values = dict(payload.values)
    values.setdefault("统计周期", period)
    ok, message, report = service.add_late_sample(values)
    return ActionResult(ok=ok, message=message, entry=report)


@router.post("/ledger/anomalies/{record_id}/actions")
def dispose_anomaly(record_id: int, payload: ActionPayload) -> ActionResult:
    """处置采集校验异常台账中的单条结论。"""
    ok, message = service.dispose_anomaly(record_id, payload.action.strip(), payload.remark or "")
    return ActionResult(ok=ok, message=message)
