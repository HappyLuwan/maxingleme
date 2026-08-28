"""
定时清理任务（用 threading.Timer 实现，无需引入 APScheduler）
- 每 12 小时跑一次 cleanup_expired
- 启动时立即跑一次（补齐 downtime 期间应删的数据）
"""
from __future__ import annotations

import logging
import threading
import time

from app.repository import repo

logger = logging.getLogger(__name__)

# 12 小时执行一次
_INTERVAL_SECONDS = 12 * 3600

_timer: threading.Timer | None = None
_running = False


def _run_once() -> None:
    """执行一次清理，异常兜底，避免打断调度"""
    global _timer
    if not _running:
        return
    try:
        stats = repo.cleanup_expired()
        # cleanup_expired 内部已 log，这里不重复
        _ = stats
    except Exception as e:
        logger.exception("[Cleanup] 清理任务异常：%s", e)
    finally:
        # 再定下一次
        if _running:
            _timer = threading.Timer(_INTERVAL_SECONDS, _run_once)
            _timer.daemon = True
            _timer.start()


def start() -> None:
    """启动清理任务：立即跑一次 + 之后每 12h 一次"""
    global _running, _timer
    if _running:
        return
    _running = True
    # 立即跑一次（异步，不阻塞启动）
    t = threading.Thread(target=_run_once, daemon=True, name="cleanup-first")
    t.start()
    logger.info("[Cleanup] 定时清理已启动，间隔 %d 秒", _INTERVAL_SECONDS)


def stop() -> None:
    """停止清理任务"""
    global _running, _timer
    _running = False
    if _timer is not None:
        try:
            _timer.cancel()
        except Exception:
            pass
        _timer = None
    logger.info("[Cleanup] 定时清理已停止")
