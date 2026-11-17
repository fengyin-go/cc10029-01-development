"""内存数据仓库：给每个业务模块准备一份可筛选、可流转的示例数据。

真实项目里这里会换成数据库访问层；当前实现只依赖标准库，保证克隆下来就能起。

质量趋势相关的采集样本、发布批次、指标数据集、样本快照和校验台账放在内部表里：
它们同属一条质量发布链路，必须能在一个事务里一起提交、一起回退，且不参与运营概览
的模块统计。
"""
from __future__ import annotations

import copy
import threading
from contextlib import contextmanager
from typing import Any, Iterator

from app.seed import SEED_ROWS

# 质量趋势链路的内部表：不参与 overview 的业务模块汇总。
INTERNAL_TABLES = (
    "quality_samples",
    "quality_trend_releases",
    "quality_trend_datasets",
    "quality_trend_snapshots",
    "validate_trend_records",
    "validate_anomaly_records",
)


class Store:
    def __init__(self) -> None:
        self._tables: dict[str, list[dict[str, Any]]] = {
            name: [dict(row) for row in rows] for name, rows in SEED_ROWS.items()
        }
        for name in INTERNAL_TABLES:
            self._tables.setdefault(name, [])
        # 质量趋势的写入是“发布批次”级别的事务，用同一把锁串行化，避免两个规则
        # 同时发布同一统计周期时互相看到对方的半份数据。
        self._lock = threading.RLock()

    def module_names(self) -> list[str]:
        return sorted(name for name in self._tables if name not in INTERNAL_TABLES)

    def rows(self, module: str) -> list[dict[str, Any]]:
        return self._tables.setdefault(module, [])

    def find(self, module: str, entry_id: int) -> dict[str, Any] | None:
        for row in self.rows(module):
            if int(row.get("id", 0)) == entry_id:
                return row
        return None

    def next_id(self, module: str) -> int:
        rows = self.rows(module)
        return max((int(row.get("id", 0)) for row in rows), default=0) + 1

    @contextmanager
    def locked(self) -> Iterator[None]:
        """只读取一致快照：和发布事务共用一把锁，避免读到写了一半的批次。"""
        with self._lock:
            yield

    @contextmanager
    def transaction(self, tables: tuple[str, ...] | list[str] | None = None) -> Iterator[None]:
        """把一组表的写入包成一个原子操作：任何异常都恢复事务开始前的内容。

        恢复是就地替换列表内容，已经拿到列表引用的调用方不会看到悬空对象。
        锁保证同一时刻只有一个发布事务在改这批表。
        """
        with self._lock:
            names = tuple(tables) if tables is not None else tuple(self._tables)
            backup = {name: copy.deepcopy(self._tables.get(name, [])) for name in names}
            try:
                yield
            except Exception:
                for name in names:
                    rows = self._tables.setdefault(name, [])
                    rows[:] = backup[name]
                raise

    def overview(self) -> dict[str, object]:
        modules: list[dict[str, object]] = []
        for name in self.module_names():
            rows = self.rows(name)
            modules.append({
                "name": name,
                "created": len(rows),
                "pending": sum(1 for row in rows if row.get("pending")),
                "abnormal": sum(1 for row in rows if row.get("abnormal")),
            })
        cards = [
            {"label": "业务模块", "value": len(modules)},
            {"label": "今日新增", "value": sum(int(item["created"]) for item in modules)},
            {"label": "待处理", "value": sum(int(item["pending"]) for item in modules)},
            {"label": "异常量", "value": sum(int(item["abnormal"]) for item in modules)},
        ]
        return {"cards": cards, "modules": modules}


store = Store()
