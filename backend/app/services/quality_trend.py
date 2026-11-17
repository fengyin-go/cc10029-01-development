"""质量趋势数据报告服务：把已落库采集样本按质量指标口径算成可复现的结果。

核心约束都收在这里：
- 指标数据集、样本快照、校验台账在同一个发布批次里落库，接口只按发布批次读取，
  不会出现“只有指标数字没有样本依据”的窗口；
- 同一统计周期只保留一份可见报告，规则口径冲突时按规则优先级定版；
- 迟到样本只重算它所属的统计周期，其它周期的版本保持不变；
- 重复送交同一份样本只写一份，后续请求直接读已存在的结果。
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any

from app.quality_core import (
    DEFAULT_RULE_VERSION,
    RULE_DEFINITIONS,
    as_float,
    build_bundle,
    resolve_rule,
    sample_fingerprint,
)
from app.seed import SEED_QUALITY_SAMPLES
from app.store import store

MODULE = "quality"
SAMPLE_TABLE = "quality_samples"
RELEASE_TABLE = "quality_trend_releases"
DATASET_TABLE = "quality_trend_datasets"
SNAPSHOT_TABLE = "quality_trend_snapshots"
TREND_LEDGER = "validate_trend_records"
ANOMALY_LEDGER = "validate_anomaly_records"
TREND_TABLES = (
    SAMPLE_TABLE,
    RELEASE_TABLE,
    DATASET_TABLE,
    SNAPSHOT_TABLE,
    TREND_LEDGER,
    ANOMALY_LEDGER,
)


def now_text() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def metric_definitions() -> list[dict[str, Any]]:
    return [dict(row) for row in store.rows(MODULE)]


def periods() -> list[str]:
    found = {
        str(row.get("统计周期") or "").strip()
        for table in (SAMPLE_TABLE, RELEASE_TABLE)
        for row in store.rows(table)
    }
    return sorted(period for period in found if period)


def _visible_release(period: str) -> dict[str, Any] | None:
    visible = [
        row for row in store.rows(RELEASE_TABLE)
        if row.get("统计周期") == period and row.get("可见")
    ]
    return visible[-1] if visible else None


def _release_rows(period: str) -> list[dict[str, Any]]:
    return [
        row for row in store.rows(RELEASE_TABLE)
        if row.get("统计周期") == period
    ]


def _report_summary(release: dict[str, Any]) -> dict[str, Any]:
    batch = int(release["id"])
    datasets = [
        row for row in store.rows(DATASET_TABLE) if int(row.get("发布批次", 0)) == batch
    ]
    snapshots = [
        row for row in store.rows(SNAPSHOT_TABLE) if int(row.get("发布批次", 0)) == batch
    ]
    return {
        "统计周期": release.get("统计周期"),
        "版本号": release.get("版本号"),
        "发布批次": batch,
        "规则版本": release.get("规则版本"),
        "规则编号": release.get("规则编号"),
        "规则名称": release.get("规则名称"),
        "规则说明": release.get("规则说明"),
        "样本数量": release.get("样本数量", 0),
        "达标样本数": release.get("达标样本数", 0),
        "异常数": release.get("异常数", 0),
        "达标率": release.get("达标率", 0.0),
        "迟到样本数": sum(1 for row in snapshots if row.get("迟到")),
        "指标数量": len(datasets),
        "指标版本标识": f"{release.get('统计周期')}#v{release.get('版本号')}",
        "校验结论": "异常" if int(release.get("异常数", 0)) > 0 else "正常",
        "创建时间": release.get("创建时间"),
        "备注": release.get("备注", ""),
    }


def _ledger_rows(table: str, batch: int) -> list[dict[str, Any]]:
    return [
        dict(row) for row in store.rows(table) if int(row.get("发布批次", 0)) == batch
    ]


def _period_samples(period: str) -> list[dict[str, Any]]:
    return [
        dict(row) for row in store.rows(SAMPLE_TABLE)
        if str(row.get("统计周期") or "").strip() == period
    ]


def _write_bundle(bundle: dict[str, Any], *, period: str, rule_version: str,
                  version: int, remark: str, fail_at: str | None = None) -> dict[str, Any]:
    """把一份完整报告写进发布批次；调用方必须已经处在事务里。

    可见标记在这一步统一切换：上一版先置为不可见，新批次照常落库，
    任何一步抛错都会由 store.transaction 整批回滚。

    `fail_at` 只给验收用：`after-datasets` 时故意在写完指标数据集、还没写样本快照
    的位置抛错，用来验证不会留下“有指标数字没有样本依据”的半份数据。
    """
    for row in store.rows(RELEASE_TABLE):
        if row.get("统计周期") == period and row.get("可见"):
            row["可见"] = False
            row["已取代"] = True
    release_id = store.next_id(RELEASE_TABLE)
    report = dict(bundle["report"])
    release = {
        "id": release_id,
        "统计周期": period,
        "版本号": version,
        "规则版本": rule_version,
        "规则编号": report["规则编号"],
        "规则名称": report["规则名称"],
        "规则说明": report["规则说明"],
        "规则优先级": report["规则优先级"],
        "样本数量": report["样本数量"],
        "达标样本数": report["达标样本数"],
        "异常数": report["异常数"],
        "达标率": report["达标率"],
        "样本指纹": sample_fingerprint(period, RULE_DEFINITIONS[rule_version], bundle["snapshots"]),
        "可见": True,
        "已取代": False,
        "创建时间": now_text(),
        "备注": remark,
    }
    store.rows(RELEASE_TABLE).append(release)

    for item in bundle["datasets"]:
        row = dict(item)
        row["id"] = store.next_id(DATASET_TABLE)
        row["发布批次"] = release_id
        store.rows(DATASET_TABLE).append(row)

    if fail_at == "after-datasets":
        raise RuntimeError(f"统计周期 {period} 的指标数据集已写出，样本快照落库失败")

    for item in bundle["snapshots"]:
        row = dict(item)
        row["id"] = store.next_id(SNAPSHOT_TABLE)
        row["发布批次"] = release_id
        store.rows(SNAPSHOT_TABLE).append(row)

    for item in bundle["records"]:
        trend = dict(item)
        trend["id"] = store.next_id(TREND_LEDGER)
        trend["发布批次"] = release_id
        trend["版本号"] = version
        trend["来源"] = "质量趋势数据报告"
        trend["同步时间"] = release["创建时间"]
        store.rows(TREND_LEDGER).append(trend)
        if int(item.get("异常数", 0)) > 0:
            anomaly = {
                "id": store.next_id(ANOMALY_LEDGER),
                "发布批次": release_id,
                "版本号": version,
                "统计周期": period,
                "指标编号": item.get("指标编号"),
                "指标名称": item.get("指标名称"),
                "样本数量": item.get("样本数量"),
                "异常数": item.get("异常数"),
                "达标率": item.get("达标率"),
                "指标版本标识": f"{period}#v{version}",
                "规则版本": item.get("规则版本"),
                "异常结论": f"{item.get('指标名称')}在统计周期 {period} 有 {item.get('异常数')} 条样本未达标",
                "处置状态": "待处置",
                "处置人": "",
                "处置时间": "",
                "来源": "质量趋势数据报告",
                "记录时间": release["创建时间"],
            }
            store.rows(ANOMALY_LEDGER).append(anomaly)
    return release


def _next_version(period: str) -> int:
    rows = _release_rows(period)
    return max((int(row.get("版本号", 0)) for row in rows), default=0) + 1


def _bundle_for(period: str, rule_version: str) -> dict[str, Any] | None:
    return build_bundle(
        period=period,
        rule=RULE_DEFINITIONS[rule_version],
        metrics=metric_definitions(),
        samples=_period_samples(period),
    )


def _upsert_sample(sample: dict[str, Any]) -> None:
    """按样本编号在所属统计周期内更新；样本编号不存在时新增。"""
    code = str(sample.get("样本编号") or "").strip()
    for row in store.rows(SAMPLE_TABLE):
        if str(row.get("样本编号") or "").strip() != code:
            continue
        if row.get("统计周期") != sample.get("统计周期"):
            raise ValueError(
                f"迟到样本 {code} 已归属统计周期 {row.get('统计周期')}，"
                "只允许修改其所属统计周期"
            )
        row.update(sample)
        return
    entry = dict(sample)
    entry["id"] = store.next_id(SAMPLE_TABLE)
    store.rows(SAMPLE_TABLE).append(entry)


def _normalise_sample(raw: dict[str, Any], period: str, index: int) -> dict[str, Any]:
    metric_id = str(raw.get("指标编号") or "").strip()
    if not metric_id:
        raise ValueError(f"第 {index} 条样本缺少指标编号")
    value = as_float(raw.get("样本值"))
    if value is None:
        raise ValueError(f"第 {index} 条样本的样本值「{raw.get('样本值')}」不是数字，无法计算质量趋势")
    sample_code = str(raw.get("样本编号") or "").strip()
    if not sample_code:
        sample_code = f"SMP-{period.replace('-', '')}-{metric_id}-{index:03d}"
    sample_period = str(raw.get("统计周期") or period).strip()
    if sample_period != period:
        raise ValueError(
            f"第 {index} 条样本归属统计周期 {sample_period}，与本次送交的 {period} 不一致"
        )
    return {
        "样本编号": sample_code,
        "采集批次": str(raw.get("采集批次") or "").strip(),
        "指标编号": metric_id,
        "统计周期": period,
        "样本值": value,
        "落库时间": str(raw.get("落库时间") or now_text()),
        "迟到": bool(raw.get("迟到")),
    }


def _outcomes_differ(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return (
        int(left.get("异常数", 0)) != int(right.get("异常数", 0))
        or round(float(left.get("达标率", 0.0)), 6) != round(float(right.get("达标率", 0.0)), 6)
        or int(left.get("样本数量", 0)) != int(right.get("样本数量", 0))
    )


class _Reject(Exception):
    """发布过程中的业务拒绝：抛出后由事务整批回滚，再把说明交回接口层。"""


class _Handled(Exception):
    """幂等命中或口径冲突：整批回退（不产生新版本），带着既有报告返回。"""

    def __init__(self, ok: bool, message: str, report: dict[str, Any] | None) -> None:
        super().__init__(message)
        self.ok = ok
        self.message = message
        self.report = report


class QualityTrendService:
    def __init__(self) -> None:
        self._seed_lock = threading.Lock()
        self._seeded = False

    # ---------- 初始化 ----------
    def ensure_seed(self) -> None:
        """首启时用已落库样本生成每个统计周期的第一版趋势报告。"""
        if self._seeded:
            return
        with self._seed_lock:
            if self._seeded:
                return
            with store.transaction(TREND_TABLES):
                if not store.rows(SAMPLE_TABLE):
                    for item in SEED_QUALITY_SAMPLES:
                        row = dict(item)
                        row["id"] = store.next_id(SAMPLE_TABLE)
                        store.rows(SAMPLE_TABLE).append(row)
                if not store.rows(RELEASE_TABLE):
                    for period in periods():
                        bundle = _bundle_for(period, DEFAULT_RULE_VERSION)
                        if bundle is None:
                            continue
                        _write_bundle(
                            bundle,
                            period=period,
                            rule_version=DEFAULT_RULE_VERSION,
                            version=1,
                            remark="初始发布：按已落库采集样本生成",
                        )
            self._seeded = True

    # ---------- 读取 ----------
    # 读也要拿同一把锁：发布批次是多表一起写的，读取必须看到同一时刻的完整快照，
    # 不能读到“指标数据集已换新版、样本快照还是旧版”的中间态。
    def list_reports(self) -> list[dict[str, Any]]:
        self.ensure_seed()
        with store.locked():
            reports: list[dict[str, Any]] = []
            for period in reversed(periods()):
                release = _visible_release(period)
                if release is None:
                    continue
                reports.append(_report_summary(release))
            return reports

    def list_periods(self) -> list[str]:
        self.ensure_seed()
        with store.locked():
            return list(reversed(periods()))

    def get_report(self, period: str) -> dict[str, Any] | None:
        self.ensure_seed()
        with store.locked():
            return self._get_report_unlocked(period)

    def _get_report_unlocked(self, period: str) -> dict[str, Any] | None:
        release = _visible_release(period)
        if release is None:
            return None
        summary = _report_summary(release)
        batch = int(release["id"])
        datasets = [
            dict(row) for row in store.rows(DATASET_TABLE)
            if int(row.get("发布批次", 0)) == batch
        ]
        for dataset in datasets:
            dataset["版本号"] = release.get("版本号")
            dataset["指标版本标识"] = f"{period}#v{release.get('版本号')}"
        samples = [
            dict(row) for row in store.rows(SNAPSHOT_TABLE)
            if int(row.get("发布批次", 0)) == batch
        ]
        late_samples = [row for row in samples if row.get("迟到")]
        return {
            "report": summary,
            "datasets": datasets,
            "samples": samples,
            "lateSamples": late_samples,
            "trendRecords": _ledger_rows(TREND_LEDGER, batch),
            "anomalyRecords": _ledger_rows(ANOMALY_LEDGER, batch),
            "periods": list(reversed(periods())),
        }

    def list_trend_records(self) -> list[dict[str, Any]]:
        """采集校验侧读取校验趋势记录：只返回可见发布批次的记录。"""
        self.ensure_seed()
        with store.locked():
            visible = {int(row["id"]) for row in store.rows(RELEASE_TABLE) if row.get("可见")}
            return [
                dict(row) for row in store.rows(TREND_LEDGER)
                if int(row.get("发布批次", 0)) in visible
            ]

    def list_anomaly_records(self) -> list[dict[str, Any]]:
        self.ensure_seed()
        with store.locked():
            visible = {int(row["id"]) for row in store.rows(RELEASE_TABLE) if row.get("可见")}
            return [
                dict(row) for row in store.rows(ANOMALY_LEDGER)
                if int(row.get("发布批次", 0)) in visible
            ]

    # ---------- 发布 ----------
    def publish(self, values: dict[str, Any]) -> tuple[bool, str, dict[str, Any] | None]:
        """登记发布请求：整批成功才对外可见，业务拒绝或落库失败都回退。

        `模拟落库失败` 只用于验收事务回退：在写发布批次时主动抛错，
        指标数据集、样本快照和校验台账保持一致，不留下半份数据。
        """
        self.ensure_seed()
        period = str(values.get("统计周期") or "").strip()
        if not period:
            return False, "缺少统计周期，无法生成质量趋势数据报告", None
        rule = resolve_rule(values.get("规则版本") or values.get("规则") or values.get("规则编号"))
        if rule is None:
            return False, f"规则版本「{values.get('规则版本')}」不受支持", None
        raw_samples = values.get("样本") or values.get("samples") or []
        if isinstance(raw_samples, dict):
            raw_samples = [raw_samples]
        if not isinstance(raw_samples, list):
            return False, "样本必须是数组", None
        try:
            samples = [
                _normalise_sample(raw, period, index)
                for index, raw in enumerate(raw_samples, start=1)
                if isinstance(raw, dict)
            ]
        except ValueError as error:
            return False, str(error), None
        settled = {
            str(row.get("样本编号")): str(row.get("统计周期"))
            for row in store.rows(SAMPLE_TABLE)
        }
        for sample in samples:
            owner = settled.get(sample["样本编号"])
            if owner and owner != period:
                return (
                    False,
                    f"样本 {sample['样本编号']} 已归属统计周期 {owner}，不允许改挂到 {period}",
                    None,
                )
        remark = str(values.get("备注") or "").strip()

        try:
            result = self._publish_in_transaction(
                values=values,
                period=period,
                rule=rule,
                samples=samples,
                remark=remark,
            )
        except _Reject as reject:
            return False, str(reject), None
        except _Handled as handled:
            return handled.ok, handled.message, handled.report
        except Exception as error:  # noqa: BLE001 - 事务已回滚，这里只负责给出可读结论
            return False, f"质量趋势数据报告落库失败，已回退：{error}", None
        return result

    def _publish_in_transaction(
        self,
        *,
        values: dict[str, Any],
        period: str,
        rule: dict[str, Any],
        samples: list[dict[str, Any]],
        remark: str,
    ) -> tuple[bool, str, dict[str, Any] | None]:
        with store.transaction(TREND_TABLES):
            for sample in samples:
                _upsert_sample(sample)
            bundle = _bundle_for(period, rule["规则版本"])
            if bundle is None:
                raise _Reject(f"统计周期 {period} 没有可用的采集样本，质量趋势数据报告未生成")

            existing = _visible_release(period)
            if existing is not None:
                fingerprint = sample_fingerprint(period, rule, bundle["snapshots"])
                if existing.get("样本指纹") == fingerprint:
                    report = self.get_report(period)
                    raise _Handled(True, "质量趋势数据报告已存在，读取既有结果", report)
                if (
                    existing.get("规则版本") != rule["规则版本"]
                    and _outcomes_differ(existing, bundle["report"])
                ):
                    # 口径冲突：只允许展示一个带规则版本的完整报告。
                    # 规则优先级数字越小越优先；同级则保留先发布的版本。
                    if int(rule["优先级"]) >= int(existing.get("规则优先级", 99)):
                        report = self.get_report(period)
                        raise _Handled(
                            True,
                            f"统计周期 {period} 已存在规则 {existing.get('规则版本')} 的报告，"
                            "口径冲突时保留该版本",
                            report,
                        )

            if str(values.get("模拟落库失败") or values.get("simulateFailure") or "").strip():
                raise _Reject(f"统计周期 {period} 的质量趋势数据报告落库失败，已回退")
            version = _next_version(period)
            _write_bundle(
                bundle,
                period=period,
                rule_version=rule["规则版本"],
                version=version,
                remark=remark or f"按规则 {rule['规则版本']} 从已落库样本生成",
                fail_at="after-datasets" if str(values.get("模拟部分落库失败") or "").strip() else None,
            )
            report = self.get_report(period)
        return True, f"统计周期 {period} 的质量趋势数据报告已发布（第 {version} 版）", report

    # ---------- 迟到样本 ----------
    def add_late_sample(self, values: dict[str, Any]) -> tuple[bool, str, dict[str, Any] | None]:
        self.ensure_seed()
        period = str(values.get("统计周期") or values.get("归属统计周期") or "").strip()
        if not period:
            return False, "迟到样本必须声明所属统计周期", None
        metric_id = str(values.get("指标编号") or "").strip()
        if not metric_id:
            return False, "迟到样本缺少指标编号", None
        if not any(str(metric.get("指标编号")) == metric_id for metric in metric_definitions()):
            return False, f"指标 {metric_id} 不存在，迟到样本无法归属", None
        sample_code = str(values.get("样本编号") or "").strip()
        if sample_code:
            for row in store.rows(SAMPLE_TABLE):
                if str(row.get("样本编号")) == sample_code and row.get("统计周期") != period:
                    return (
                        False,
                        f"迟到样本 {sample_code} 已归属统计周期 {row.get('统计周期')}，"
                        "只允许修改其所属统计周期",
                        None,
                    )
        try:
            sample = _normalise_sample({**values, "统计周期": period}, period, 1)
        except ValueError as error:
            return False, str(error), None
        sample["迟到"] = True

        visible = _visible_release(period)
        rule_version = str(visible.get("规则版本")) if visible else DEFAULT_RULE_VERSION
        if rule_version not in RULE_DEFINITIONS:
            rule_version = DEFAULT_RULE_VERSION

        try:
            with store.transaction(TREND_TABLES):
                _upsert_sample(sample)
                bundle = _bundle_for(period, rule_version)
                if bundle is None:
                    raise _Reject(f"统计周期 {period} 仍没有可用样本")
                version = _next_version(period)
                _write_bundle(
                    bundle,
                    period=period,
                    rule_version=rule_version,
                    version=version,
                    remark=f"迟到样本 {sample['样本编号']} 归入统计周期 {period} 后重算",
                )
        except _Reject as reject:
            return False, str(reject), None
        except Exception as error:  # noqa: BLE001 - 事务已回滚
            return False, f"迟到样本落库失败，已回退：{error}", None
        return True, f"迟到样本已归入统计周期 {period} 并重算第 {version} 版报告", self.get_report(period)

    # ---------- 异常处置台账 ----------
    def dispose_anomaly(self, record_id: int, action: str, operator: str) -> tuple[bool, str]:
        self.ensure_seed()
        with store.transaction((ANOMALY_LEDGER,)):
            visible = {int(row["id"]) for row in store.rows(RELEASE_TABLE) if row.get("可见")}
            for row in store.rows(ANOMALY_LEDGER):
                if int(row.get("id", 0)) != record_id:
                    continue
                if int(row.get("发布批次", 0)) not in visible:
                    return False, "该异常记录所属的质量趋势版本已被取代，不允许处置"
                row["处置状态"] = action or "已处置"
                row["处置人"] = operator or "值班管理员"
                row["处置时间"] = now_text()
                return True, f"异常记录 {record_id} 处置状态：{row['处置状态']}"
        return False, f"异常记录 {record_id} 不存在"


service = QualityTrendService()
