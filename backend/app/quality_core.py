"""质量趋势核心计算：按质量指标口径从已落库采集样本算出可复现的数据集。

这里只做纯计算，不碰数据仓库，方便 seed、服务层和接口层共用同一套口径：
同样的样本 + 同样的规则版本，一定得到同样的达标率。
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

DEFAULT_RULE_VERSION = "RULE-A@1"

# 规则版本是质量趋势报告的一部分：同一统计周期允许先后收到不同规则的结果，
# 但最终只保留一份带规则版本的可见报告。
RULE_DEFINITIONS: dict[str, dict[str, Any]] = {
    "RULE-A@1": {
        "规则版本": "RULE-A@1",
        "规则编号": "RULE-A",
        "规则名称": "规则A-闭区间达标率",
        "规则说明": "样本值落在[阈值下界, 阈值上界]内记为达标",
        "优先级": 1,
        "下界包含": True,
        "上界包含": True,
    },
    "RULE-B@1": {
        "规则版本": "RULE-B@1",
        "规则编号": "RULE-B",
        "规则名称": "规则B-开区间达标率",
        "规则说明": "样本值严格落在(阈值下界, 阈值上界)内才记为达标",
        "优先级": 2,
        "下界包含": False,
        "上界包含": False,
    },
}

RULE_ALIASES = {
    "RULE-A": "RULE-A@1",
    "RULE-A@1": "RULE-A@1",
    "规则A": "RULE-A@1",
    "规则a": "RULE-A@1",
    "A": "RULE-A@1",
    "RULE-B": "RULE-B@1",
    "RULE-B@1": "RULE-B@1",
    "规则B": "RULE-B@1",
    "规则b": "RULE-B@1",
    "B": "RULE-B@1",
}


def resolve_rule(value: Any) -> dict[str, Any] | None:
    """把接口上传来的规则叫法归一到一个确定的规则版本。"""
    text = str(value or "").strip()
    if not text:
        return RULE_DEFINITIONS[DEFAULT_RULE_VERSION]
    key = RULE_ALIASES.get(text)
    if key is None:
        key = RULE_ALIASES.get(text.upper())
    return RULE_DEFINITIONS.get(key) if key else None


def as_float(value: Any, default: float | None = None) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def metric_bounds(metric: dict[str, Any]) -> tuple[float, float]:
    low = as_float(metric.get("阈值下界"), 0.0)
    high = as_float(metric.get("阈值上界"), 1.0)
    if low is None:
        low = 0.0
    if high is None:
        high = 1.0
    if high < low:
        low, high = high, low
    return low, high


def is_sample_passed(value: float, low: float, high: float, rule: dict[str, Any]) -> bool:
    lower_ok = value >= low if rule["下界包含"] else value > low
    upper_ok = value <= high if rule["上界包含"] else value < high
    return lower_ok and upper_ok


def compute_metric_dataset(
    metric: dict[str, Any],
    samples: list[dict[str, Any]],
    period: str,
    rule: dict[str, Any],
) -> dict[str, Any]:
    """按一条质量指标的口径，算出某统计周期的指标数据集行。"""
    low, high = metric_bounds(metric)
    values: list[float] = []
    passed = 0
    for sample in samples:
        value = as_float(sample.get("样本值"))
        if value is None:
            continue
        values.append(value)
        if is_sample_passed(value, low, high, rule):
            passed += 1
    total = len(values)
    rate = round(passed / total, 6) if total else 0.0
    mean = round(sum(values) / total, 6) if total else 0.0
    return {
        "指标编号": str(metric.get("指标编号") or "").strip(),
        "指标名称": str(metric.get("指标名称") or "").strip(),
        "统计口径": str(metric.get("统计口径") or "").strip(),
        "阈值下界": low,
        "阈值上界": high,
        "统计周期": period,
        "样本数量": total,
        "达标样本数": passed,
        "异常数": total - passed,
        "达标率": rate,
        "指标均值": mean,
        "规则版本": rule["规则版本"],
        "规则名称": rule["规则名称"],
    }


def build_bundle(
    *,
    period: str,
    rule: dict[str, Any],
    metrics: list[dict[str, Any]],
    samples: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """把一个统计周期的指标数据集、样本快照和校验结论打包成一个发布批次。"""
    datasets: list[dict[str, Any]] = []
    snapshots: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []

    for metric in metrics:
        metric_id = str(metric.get("指标编号") or "").strip()
        if not metric_id:
            continue
        scoped = [
            sample for sample in samples
            if str(sample.get("指标编号") or "").strip() == metric_id
        ]
        if not scoped:
            continue
        row = compute_metric_dataset(metric, scoped, period, rule)
        datasets.append(row)
        for sample in scoped:
            value = as_float(sample.get("样本值"))
            snapshots.append({
                "样本编号": sample.get("样本编号"),
                "采集批次": sample.get("采集批次"),
                "指标编号": metric_id,
                "统计周期": period,
                "样本值": value,
                "落库时间": sample.get("落库时间"),
                "迟到": bool(sample.get("迟到")),
                "是否达标": is_sample_passed(
                    value if value is not None else float("nan"),
                    row["阈值下界"], row["阈值上界"], rule,
                ),
            })
        records.append({
            "统计周期": period,
            "指标编号": metric_id,
            "指标名称": row["指标名称"],
            "样本数量": row["样本数量"],
            "异常数": row["异常数"],
            "达标率": row["达标率"],
            "规则版本": rule["规则版本"],
            "校验结论": "异常" if row["异常数"] > 0 else "正常",
        })

    if not datasets:
        return None

    total = sum(int(row["样本数量"]) for row in datasets)
    passed = sum(int(row["达标样本数"]) for row in datasets)
    rate = round(passed / total, 6) if total else 0.0
    report = {
        "统计周期": period,
        "规则版本": rule["规则版本"],
        "规则编号": rule["规则编号"],
        "规则名称": rule["规则名称"],
        "规则说明": rule["规则说明"],
        "规则优先级": int(rule["优先级"]),
        "样本数量": total,
        "达标样本数": passed,
        "异常数": total - passed,
        "达标率": rate,
    }
    return {"report": report, "datasets": datasets, "snapshots": snapshots, "records": records}


def sample_fingerprint(period: str, rule: dict[str, Any], snapshots: list[dict[str, Any]]) -> str:
    """样本指纹用于幂等：同一份样本再次送交时只写入一份报告。"""
    canonical = {
        "统计周期": period,
        "规则版本": rule["规则版本"],
        "样本": sorted(
            (
                {
                    "样本编号": snap.get("样本编号"),
                    "指标编号": snap.get("指标编号"),
                    "样本值": snap.get("样本值"),
                }
                for snap in snapshots
            ),
            key=lambda item: str(item.get("样本编号")),
        ),
    }
    encoded = json.dumps(canonical, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:20]
