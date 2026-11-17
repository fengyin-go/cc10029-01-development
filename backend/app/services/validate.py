"""采集校验 分析看板服务：汇总指标、运行分析并同步质量趋势的校验结论。

质量趋势数据报告的校验结论会同步到这里的校验趋势记录和采集校验异常处置台账；
本模块只读取可见发布批次的记录，不会看到已经被取代的半份数据。
"""
from __future__ import annotations

from typing import Any

from app.quality_core import as_float
from app.services.quality_trend import service as trend_service
from app.store import store

MODULE = "validate"
REQUIRED_FIELDS = ["规则编号", "校验字段", "期望格式"]
STATUS_ORDER = ["草稿", "待校验", "已启用", "已停用"]
ACTION_RULES = {"提交校验": "待校验", "启用配置": "已启用", "停用配置": "已停用"}
NEGATIVE_ACTIONS = ["停用配置"]


class ValidateService:
    def trend_records(self) -> list[dict[str, Any]]:
        return trend_service.list_trend_records()

    def anomaly_records(self) -> list[dict[str, Any]]:
        return trend_service.list_anomaly_records()

    def list_results(self) -> list[dict[str, Any]]:
        rows = store.rows(MODULE)
        results: list[dict] = []
        for row in rows:
            d = dict(row)
            records = [
                item for item in self.trend_records()
                if str(item.get("指标编号")) in str(d.get("校验字段"))
            ]
            d["趋势记录数"] = len(records)
            d["指标值"] = round(sum(float(item.get("达标率", 0)) for item in records) / len(records), 6) if records else 0.0
            d["对比基准"] = round(as_float(d.get("空值阈值"), 0.0) or 0.0, 6)
            d["差异"] = round(d["指标值"] - d["对比基准"], 6)
            results.append(d)
        return results

    def run_analysis(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        """按统计周期回放质量趋势的校验结论，异常数与达标率回到同一窗口。"""
        period = str(params.get("统计周期") or "").strip()
        records = self.trend_records()
        if period:
            records = [item for item in records if item.get("统计周期") == period]
        grouped: dict[str, dict[str, Any]] = {}
        for item in records:
            key = str(item.get("统计周期"))
            bucket = grouped.setdefault(key, {
                "id": len(grouped) + 1,
                "统计周期": key,
                "版本号": 0,
                "规则版本": item.get("规则版本"),
                "样本数量": 0,
                "异常数": 0,
                "达标样本数": 0,
                "指标值": 0.0,
                "达标率": 0.0,
                "校验结论": "正常",
            })
            bucket["样本数量"] += int(item.get("样本数量", 0))
            bucket["异常数"] += int(item.get("异常数", 0))
            bucket["规则版本"] = item.get("规则版本")
        for bucket in grouped.values():
            total = int(bucket["样本数量"])
            abnormal = int(bucket["异常数"])
            passed = total - abnormal
            bucket["达标样本数"] = passed
            bucket["达标率"] = round(passed / total, 6) if total else 0.0
            bucket["指标值"] = bucket["达标率"]
            bucket["校验结论"] = "异常" if abnormal > 0 else "正常"
            bucket["版本号"] = len([
                item for item in trend_service.list_reports()
                if item.get("统计周期") == bucket["统计周期"]
            ])
        return sorted(grouped.values(), key=lambda item: str(item["统计周期"]), reverse=True)

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        return store.find(MODULE, entry_id)
