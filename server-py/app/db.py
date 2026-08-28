"""
数据库层：MySQL 连接池（默认）+ SQLite 兼容（本地开发可选）
- 生产环境走云托管内网 MySQL（DB_BACKEND=mysql）
- 本地开发无 MySQL 时可切 DB_BACKEND=sqlite 走 ./data/mxlm.db
- 启动时自动建表：三张（roast_records / favorites / rate_limits）
"""
from __future__ import annotations

import logging
import os
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, List, Tuple

logger = logging.getLogger(__name__)

# ---------- 后端选择 ----------
_DB_BACKEND = os.getenv("DB_BACKEND", "mysql").strip().lower()

# ---------- MySQL 连接参数 ----------
_MYSQL_HOST = os.getenv("DB_HOST", "127.0.0.1").strip()
_MYSQL_PORT = int(os.getenv("DB_PORT", "3306"))
_MYSQL_USER = os.getenv("DB_USER", "root").strip()
_MYSQL_PASSWORD = os.getenv("DB_PASSWORD", "").strip()
_MYSQL_DATABASE = os.getenv("DB_NAME", "mxlm").strip()
_MYSQL_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))

# ---------- SQLite 兜底参数（本地开发用）----------
_SQLITE_PATH = os.getenv("DB_PATH", "").strip()
if not _SQLITE_PATH:
    _project_root = Path(__file__).parent.parent
    _SQLITE_PATH = str(_project_root / "data" / "mxlm.db")

_lock = threading.RLock()

# ---------- MySQL 实现 ----------
_mysql_pool = None

def _get_mysql_pool():
    """惰性初始化 MySQL 连接池"""
    global _mysql_pool
    if _mysql_pool is not None:
        return _mysql_pool
    with _lock:
        if _mysql_pool is not None:
            return _mysql_pool
        try:
            from mysql.connector import pooling  # type: ignore
        except ImportError as e:
            raise RuntimeError(
                "MySQL 依赖未安装，请 pip install mysql-connector-python，或设置 DB_BACKEND=sqlite"
            ) from e
        _mysql_pool = pooling.MySQLConnectionPool(
            pool_name="mxlm_pool",
            pool_size=_MYSQL_POOL_SIZE,
            pool_reset_session=True,
            host=_MYSQL_HOST,
            port=_MYSQL_PORT,
            user=_MYSQL_USER,
            password=_MYSQL_PASSWORD,
            database=_MYSQL_DATABASE,
            charset="utf8mb4",
            use_unicode=True,
            autocommit=True,
            connection_timeout=10,
        )
        logger.info(
            "[DB] MySQL 连接池就绪 host=%s:%s db=%s pool_size=%s",
            _MYSQL_HOST, _MYSQL_PORT, _MYSQL_DATABASE, _MYSQL_POOL_SIZE,
        )
        return _mysql_pool


class _MySQLCursorAdapter:
    """
    将 mysql-connector 游标适配成 sqlite3.Cursor 风格：
    - execute 后可 .fetchone() / .fetchall() 返回 dict-like 行（支持 row["col"]）
    - execute 返回自身（模拟 sqlite3 的行为），便于链式 .rowcount / .fetchall
    - rowcount 属性一致
    - 关键：连接使用完毕自动归还到连接池
    """
    __slots__ = ("_conn", "_cur", "_last_result")

    def __init__(self, conn, cur):
        self._conn = conn
        self._cur = cur
        self._last_result = None

    def execute(self, sql: str, params: tuple | list | None = None):
        self._cur.execute(sql, tuple(params) if params else None)
        return self

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()

    @property
    def rowcount(self) -> int:
        return int(self._cur.rowcount)

    def close(self):
        try:
            self._cur.close()
        finally:
            try:
                self._conn.close()  # dictionary cursor 归还连接池
            except Exception:
                pass


# ---------- SQLite 实现（本地开发用）----------
_sqlite_conn: sqlite3.Connection | None = None


def _get_sqlite_conn() -> sqlite3.Connection:
    global _sqlite_conn
    if _sqlite_conn is None:
        Path(_SQLITE_PATH).parent.mkdir(parents=True, exist_ok=True)
        _sqlite_conn = sqlite3.connect(
            _SQLITE_PATH,
            check_same_thread=False,
            isolation_level=None,
            timeout=10.0,
        )
        _sqlite_conn.row_factory = sqlite3.Row
        try:
            _sqlite_conn.execute("PRAGMA journal_mode=WAL")
            _sqlite_conn.execute("PRAGMA synchronous=NORMAL")
            _sqlite_conn.execute("PRAGMA foreign_keys=ON")
        except Exception as e:
            logger.warning("[DB] SQLite PRAGMA 设置失败：%s", e)
    return _sqlite_conn


# ---------- 统一 cursor 上下文 ----------
@contextmanager
def cursor():
    """
    统一游标上下文：
    - MySQL：从连接池借一个连接 + dictionary cursor，退出自动归还
    - SQLite：走进程级单连接 + 大锁
    """
    if _DB_BACKEND == "mysql":
        pool = _get_mysql_pool()
        conn = pool.get_connection()
        cur = conn.cursor(dictionary=True)
        adapter = _MySQLCursorAdapter(conn, cur)
        try:
            yield adapter
        finally:
            adapter.close()
    else:
        with _lock:
            cur = _get_sqlite_conn().cursor()
            try:
                yield cur
            finally:
                cur.close()


# ---------- 建表（两个方言分别维护）----------
_SCHEMA_MYSQL: List[str] = [
    # 骂醒记录：核心业务表（roast_id 是 hex uuid，32 位）
    """
    CREATE TABLE IF NOT EXISTS roast_records (
        roast_id     VARCHAR(64) NOT NULL,
        openid       VARCHAR(64) DEFAULT NULL,
        user_input   TEXT NOT NULL,
        content      TEXT NOT NULL,
        style        VARCHAR(32) NOT NULL,
        provider     VARCHAR(32) DEFAULT NULL,
        created_at   DOUBLE NOT NULL,
        PRIMARY KEY (roast_id),
        KEY idx_records_openid_created (openid, created_at),
        KEY idx_records_created (created_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS favorites (
        openid       VARCHAR(64) NOT NULL,
        roast_id     VARCHAR(64) NOT NULL,
        created_at   DOUBLE NOT NULL,
        PRIMARY KEY (openid, roast_id),
        KEY idx_favorites_openid_created (openid, created_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS rate_limits (
        openid       VARCHAR(64) NOT NULL,
        day          VARCHAR(10) NOT NULL,
        count        INT NOT NULL DEFAULT 0,
        PRIMARY KEY (openid, day)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS card_events (
        id           BIGINT NOT NULL AUTO_INCREMENT,
        openid       VARCHAR(64) DEFAULT NULL,
        roast_id     VARCHAR(64) DEFAULT NULL,
        template     VARCHAR(32) NOT NULL,
        event        VARCHAR(16) NOT NULL,
        created_at   DOUBLE NOT NULL,
        PRIMARY KEY (id),
        KEY idx_events_template_event (template, event),
        KEY idx_events_created (created_at),
        KEY idx_events_openid (openid)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
]

_SCHEMA_SQLITE: List[str] = [
    """
    CREATE TABLE IF NOT EXISTS roast_records (
        roast_id     TEXT PRIMARY KEY,
        openid       TEXT,
        user_input   TEXT NOT NULL,
        content      TEXT NOT NULL,
        style        TEXT NOT NULL,
        provider     TEXT,
        created_at   REAL NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_records_openid_created ON roast_records(openid, created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_records_created ON roast_records(created_at)",
    """
    CREATE TABLE IF NOT EXISTS favorites (
        openid       TEXT NOT NULL,
        roast_id     TEXT NOT NULL,
        created_at   REAL NOT NULL,
        PRIMARY KEY (openid, roast_id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_favorites_openid_created ON favorites(openid, created_at DESC)",
    """
    CREATE TABLE IF NOT EXISTS rate_limits (
        openid       TEXT NOT NULL,
        day          TEXT NOT NULL,
        count        INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (openid, day)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS card_events (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        openid       TEXT,
        roast_id     TEXT,
        template     TEXT NOT NULL,
        event        TEXT NOT NULL,
        created_at   REAL NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_events_template_event ON card_events(template, event)",
    "CREATE INDEX IF NOT EXISTS idx_events_created ON card_events(created_at)",
    "CREATE INDEX IF NOT EXISTS idx_events_openid ON card_events(openid)",
]


def init_db() -> None:
    """启动时初始化：建表 + 建索引"""
    schema = _SCHEMA_MYSQL if _DB_BACKEND == "mysql" else _SCHEMA_SQLITE
    with cursor() as cur:
        for sql in schema:
            cur.execute(sql)
    logger.info("[DB] 初始化完成 backend=%s", _DB_BACKEND)


def db_path() -> str:
    """返回当前存储标识（MySQL 返回 host:port/db，SQLite 返回文件路径）"""
    if _DB_BACKEND == "mysql":
        return f"mysql://{_MYSQL_HOST}:{_MYSQL_PORT}/{_MYSQL_DATABASE}"
    return _SQLITE_PATH


def db_backend() -> str:
    return _DB_BACKEND


def close_db() -> None:
    """关闭连接（服务停止时调用）"""
    global _sqlite_conn, _mysql_pool
    with _lock:
        if _sqlite_conn is not None:
            try:
                _sqlite_conn.close()
            except Exception:
                pass
            _sqlite_conn = None
        # MySQL 连接池由 connector 内部管理，直接置空即可
        _mysql_pool = None


# ---------- SQL 方言辅助 ----------
def upsert_records_sql() -> str:
    """幂等写入骂醒记录（PK 冲突时更新）"""
    if _DB_BACKEND == "mysql":
        return (
            "INSERT INTO roast_records (roast_id, openid, user_input, content, style, provider, created_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s) "
            "ON DUPLICATE KEY UPDATE "
            "openid=VALUES(openid), user_input=VALUES(user_input), content=VALUES(content), "
            "style=VALUES(style), provider=VALUES(provider), created_at=VALUES(created_at)"
        )
    return (
        "INSERT INTO roast_records (roast_id, openid, user_input, content, style, provider, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(roast_id) DO UPDATE SET "
        "openid=excluded.openid, user_input=excluded.user_input, content=excluded.content, "
        "style=excluded.style, provider=excluded.provider, created_at=excluded.created_at"
    )


def insert_favorite_sql() -> str:
    """收藏幂等插入（已存在则忽略）"""
    if _DB_BACKEND == "mysql":
        return "INSERT IGNORE INTO favorites (openid, roast_id, created_at) VALUES (%s, %s, %s)"
    return "INSERT OR IGNORE INTO favorites (openid, roast_id, created_at) VALUES (?, ?, ?)"


def upsert_rate_limit_sql() -> str:
    """限流计数原子 +1"""
    if _DB_BACKEND == "mysql":
        return (
            "INSERT INTO rate_limits (openid, day, count) VALUES (%s, %s, 1) "
            "ON DUPLICATE KEY UPDATE count = count + 1"
        )
    return (
        "INSERT INTO rate_limits (openid, day, count) VALUES (?, ?, 1) "
        "ON CONFLICT(openid, day) DO UPDATE SET count = count + 1"
    )


def ph() -> str:
    """占位符：MySQL 用 %s，SQLite 用 ?"""
    return "%s" if _DB_BACKEND == "mysql" else "?"
