"""质量报告 分析看板服务：汇总指标、运行分析与质量趋势数据报告。

质量报告页面上的结果看板一律读质量趋势的可见发布批次，避免页面上出现一套
随机的“指标值”和落库样本算出来的达标率对不上。
"""
from __future__ import annotations

from typing import Any

from app.store import store
from app.services.quality_trend import service as trend_service

MODULE = "quality"
REQUIRED_FIELDS = ["指标编号", "指标名称", "统计口径"]
STATUS_ORDER = ["草稿", "待校验", "已启用", "已停用"]
ACTION_RULES = {"提交校验": "待校验", "启用配置": "已启用", "停用配置": "已停用"}
NEGATIVE_ACTIONS = ["停用配置"]


class QualityService:
    def trend_reports(self) -> list[dict[str, Any]]:
        """按统计周期倒序列出可见的质量趋势数据报告。"""
        return trend_service.list_reports()

    def list_results(self) -> list[dict[str, Any]]:
        """质量指标列表：样本数量与达标率取最新可见趋势批次的结果。"""
        trend_service.ensure_seed()
        latest: dict[tuple[str, str], dict[str, Any]] = {}
        for report in trend_service.list_reports():
            period = str(report.get("统计周期"))
            detail = trend_service.get_report(period)
            for dataset in (detail or {}).get("datasets", []):
                latest[(period, str(dataset.get("指标编号")))] = dataset
        results: list[dict] = []
        for row in store.rows(MODULE):
            d = dict(row)
            match = latest.get((str(d.get("统计周期")), str(d.get("指标编号"))))
            if match is not None:
                d.update({
                    "样本数量": match.get("样本数量", 0),
                    "达标率": match.get("达标率", 0.0),
                    "达标样本数": match.get("达标样本数", 0),
                    "异常数": match.get("异常数", 0),
                    "规则版本": match.get("规则版本"),
                    "版本号": match.get("版本号"),
                    "发布批次": match.get("发布批次"),
                })
                d["指标值"] = match.get("达标率", 0.0)
                d["对比基准"] = match.get("指标均值", 0.0)
                d["差异"] = round(float(d["指标值"]) - float(d["对比基准"]), 6)
            results.append(d)
        return results

    def run_analysis(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        """按统计周期回放质量趋势：每个统计周期的最新一版一行，可核对达标率。"""
        trend_service.ensure_seed()
        period = str(params.get("统计周期") or "").strip()
        reports = trend_service.list_reports()
        if period:
            reports = [item for item in reports if item.get("统计周期") == period]
        results: list[dict] = []
        for index, report in enumerate(reports, start=1):
            metrics = (trend_service.get_report(str(report.get("统计周期"))) or {}).get("datasets", [])
            results.append({
                "id": index,
                "统计周期": report.get("统计周期"),
                "版本号": report.get("版本号"),
                "规则版本": report.get("规则版本"),
                "样本数量": report.get("样本数量"),
                "异常数": report.get("异常数"),
                "达标率": report.get("达标率"),
                "指标值": report.get("达标率"),
                "指标数量": len(metrics),
                "校验结论": report.get("校验结论"),
            })
        return results

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        return store.find(MODULE, entry_id)
