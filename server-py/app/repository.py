"""
骂醒记录（内存存储 + TTL 清理）
对应 Java 的 RoastRecord + RoastRecordRepository
"""
from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

from app.enums import RoastStyle

logger = logging.getLogger(__name__)

# TTL：记录保留 1 小时（够用户生成卡片即可）
_TTL_SECONDS = 3600


@dataclass
class RoastRecord:
    roast_id: str
    user_input: str
    content: str
    style: RoastStyle
    openid: Optional[str] = None
    provider: Optional[str] = None
    created_at: float = field(default_factory=time.time)


class RoastRecordRepository:
    """内存 KV：roast_id -> RoastRecord，自动 TTL 清理"""

    def __init__(self) -> None:
        self._store: dict[str, RoastRecord] = {}
        self._lock = threading.Lock()

    def save(self, record: RoastRecord) -> RoastRecord:
        if not record.roast_id:
            record.roast_id = uuid.uuid4().hex
        with self._lock:
            self._store[record.roast_id] = record
        self._gc()
        return record

    def find_by_id(self, roast_id: str) -> Optional[RoastRecord]:
        with self._lock:
            r = self._store.get(roast_id)
        if r is None:
            return None
        if time.time() - r.created_at > _TTL_SECONDS:
            with self._lock:
                self._store.pop(roast_id, None)
            return None
        return r

    def _gc(self) -> None:
        """惰性 GC：过期条目清理"""
        now = time.time()
        with self._lock:
            expired = [k for k, v in self._store.items() if now - v.created_at > _TTL_SECONDS]
            for k in expired:
                self._store.pop(k, None)
        if expired:
            logger.debug("[RoastRecordRepository] 清理过期记录 %d 条", len(expired))


# 全局单例
repo = RoastRecordRepository()
