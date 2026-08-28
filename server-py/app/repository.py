"""
骂醒记录 & 收藏 & 限流：SQLite 持久化实现
- 从内存版升级为 SQLite，容器/服务重启数据不丢
- 保留原 RoastRecord dataclass 结构，roast.py/card.py 使用方无需改动
- 新增：
  - list_history(openid, page, size)  分页历史列表
  - delete(openid, roast_id)          删除历史（同时清理相关收藏）
  - add_favorite / remove_favorite / list_favorites / is_favorite
  - incr_daily_count / get_daily_count 每日限流计数
  - cleanup_expired 定时任务用：清 90 天前 & 单用户超 500 条
"""
from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

from app.db import (
    cursor,
    insert_favorite_sql,
    ph,
    upsert_rate_limit_sql,
    upsert_records_sql,
)
from app.enums import RoastStyle

logger = logging.getLogger(__name__)

# ---------- 业务策略常量 ----------
HISTORY_RETENTION_DAYS = 90         # 历史记录保留 90 天
HISTORY_MAX_PER_USER = 500          # 单用户最多 500 条历史
DAILY_ROAST_LIMIT = 20              # 每人每天最多 20 次骂醒（成本可控 + 珍惜感）


@dataclass
class RoastRecord:
    """骂醒记录（与老版内存 dataclass 保持字段兼容）"""
    roast_id: str
    user_input: str
    content: str
    style: RoastStyle
    openid: Optional[str] = None
    provider: Optional[str] = None
    created_at: float = field(default_factory=time.time)


@dataclass
class FavoriteRecord:
    """收藏 = 记录本身 + 收藏时间"""
    record: RoastRecord
    favorited_at: float


class RoastRecordRepository:
    """
    SQLite Repository：
    - save() 幂等（PK 冲突时更新，兼容极小概率的 UUID 碰撞）
    - find_by_id() 用于卡片生成读记录（不限 openid，因分享链接可能被其他人访问）
    """

    # ---------- 骂醒记录 CRUD ----------
    def save(self, record: RoastRecord) -> RoastRecord:
        if not record.roast_id:
            record.roast_id = uuid.uuid4().hex
        with cursor() as cur:
            cur.execute(
                upsert_records_sql(),
                (
                    record.roast_id,
                    record.openid,
                    record.user_input,
                    record.content,
                    record.style.key,
                    record.provider,
                    record.created_at,
                ),
            )
        return record

    def find_by_id(self, roast_id: str) -> Optional[RoastRecord]:
        p = ph()
        with cursor() as cur:
            row = cur.execute(
                f"SELECT * FROM roast_records WHERE roast_id={p}",
                (roast_id,),
            ).fetchone()
        return self._row_to_record(row) if row else None

    def list_history(self, openid: str, page: int = 1, size: int = 20) -> tuple[list[RoastRecord], int]:
        """
        分页返回某用户历史。返回 (records, total)。
        page 从 1 开始，size 建议 20，最大 100。
        """
        page = max(1, page)
        size = max(1, min(100, size))
        offset = (page - 1) * size
        p = ph()
        with cursor() as cur:
            total_row = cur.execute(
                f"SELECT COUNT(*) AS c FROM roast_records WHERE openid={p}",
                (openid,),
            ).fetchone()
            total = _first_col(total_row)
            rows = cur.execute(
                f"""
                SELECT * FROM roast_records
                WHERE openid={p}
                ORDER BY created_at DESC
                LIMIT {p} OFFSET {p}
                """,
                (openid, size, offset),
            ).fetchall()
        return [self._row_to_record(r) for r in rows], int(total)

    def delete(self, openid: str, roast_id: str) -> bool:
        """删除单条历史（同时清对应收藏）；只允许删自己的"""
        p = ph()
        with cursor() as cur:
            r = cur.execute(
                f"DELETE FROM roast_records WHERE roast_id={p} AND openid={p}",
                (roast_id, openid),
            )
            affected = r.rowcount
            # 同时清收藏
            cur.execute(
                f"DELETE FROM favorites WHERE roast_id={p} AND openid={p}",
                (roast_id, openid),
            )
        return affected > 0

    # ---------- 收藏 ----------
    def add_favorite(self, openid: str, roast_id: str) -> bool:
        """收藏：需要该 roast 存在。返回是否是新增（重复收藏返回 False 但不报错）"""
        now = time.time()
        p = ph()
        with cursor() as cur:
            # 校验 record 存在
            exists = cur.execute(
                f"SELECT 1 AS x FROM roast_records WHERE roast_id={p}",
                (roast_id,),
            ).fetchone()
            if not exists:
                return False
            r = cur.execute(
                insert_favorite_sql(),
                (openid, roast_id, now),
            )
            return r.rowcount > 0

    def remove_favorite(self, openid: str, roast_id: str) -> bool:
        p = ph()
        with cursor() as cur:
            r = cur.execute(
                f"DELETE FROM favorites WHERE openid={p} AND roast_id={p}",
                (openid, roast_id),
            )
        return r.rowcount > 0

    def is_favorite(self, openid: str, roast_id: str) -> bool:
        p = ph()
        with cursor() as cur:
            r = cur.execute(
                f"SELECT 1 AS x FROM favorites WHERE openid={p} AND roast_id={p}",
                (openid, roast_id),
            ).fetchone()
        return r is not None

    def list_favorites(self, openid: str, page: int = 1, size: int = 20) -> tuple[list[FavoriteRecord], int]:
        """分页收藏列表，JOIN 记录表。返回 (favorites, total)。"""
        page = max(1, page)
        size = max(1, min(100, size))
        offset = (page - 1) * size
        p = ph()
        with cursor() as cur:
            total_row = cur.execute(
                f"SELECT COUNT(*) AS c FROM favorites WHERE openid={p}",
                (openid,),
            ).fetchone()
            total = _first_col(total_row)
            rows = cur.execute(
                f"""
                SELECT r.*, f.created_at AS favorited_at
                FROM favorites f
                JOIN roast_records r ON r.roast_id = f.roast_id
                WHERE f.openid={p}
                ORDER BY f.created_at DESC
                LIMIT {p} OFFSET {p}
                """,
                (openid, size, offset),
            ).fetchall()
        favs: list[FavoriteRecord] = []
        for r in rows:
            record = self._row_to_record(r)
            favs.append(FavoriteRecord(record=record, favorited_at=float(r["favorited_at"])))
        return favs, int(total)

    # ---------- 每日限流 ----------
    def incr_daily_count(self, openid: str, day: Optional[str] = None) -> int:
        """
        原子性 +1 并返回当日累计次数。
        day 格式 'YYYY-MM-DD'，缺省用今日。
        """
        d = day or date.today().isoformat()
        p = ph()
        with cursor() as cur:
            cur.execute(upsert_rate_limit_sql(), (openid, d))
            row = cur.execute(
                f"SELECT count FROM rate_limits WHERE openid={p} AND day={p}",
                (openid, d),
            ).fetchone()
        return int(row["count"]) if row else 0

    def get_daily_count(self, openid: str, day: Optional[str] = None) -> int:
        d = day or date.today().isoformat()
        p = ph()
        with cursor() as cur:
            row = cur.execute(
                f"SELECT count FROM rate_limits WHERE openid={p} AND day={p}",
                (openid, d),
            ).fetchone()
        return int(row["count"]) if row else 0

    def decr_daily_count(self, openid: str, day: Optional[str] = None) -> None:
        """写库失败等场景回滚计数"""
        d = day or date.today().isoformat()
        p = ph()
        with cursor() as cur:
            cur.execute(
                f"UPDATE rate_limits SET count = GREATEST(count - 1, 0) WHERE openid={p} AND day={p}"
                if p == "%s" else
                f"UPDATE rate_limits SET count = MAX(count - 1, 0) WHERE openid={p} AND day={p}",
                (openid, d),
            )

    # ---------- 定时清理 ----------
    def cleanup_expired(self) -> dict:
        """
        清理策略：
        1) 全表：删除 90 天前的 roast_records（连同 favorites 里的孤儿一起清）
        2) 每用户：只保留最新 500 条历史（收藏不受此限制）
        3) 限流表：清理 3 天前的日计数（无需长期保留）
        返回删除统计。
        """
        stats = {"expired_by_age": 0, "trimmed_by_quota": 0, "rate_limit_purged": 0}
        p = ph()

        threshold = time.time() - HISTORY_RETENTION_DAYS * 86400
        with cursor() as cur:
            # 1) 过期清理（roast_records 删了要连带清 favorites，因为无 FK）
            expired_ids = [
                r["roast_id"] for r in cur.execute(
                    f"SELECT roast_id FROM roast_records WHERE created_at < {p}",
                    (threshold,),
                ).fetchall()
            ]
            if expired_ids:
                placeholders = ",".join([p] * len(expired_ids))
                cur.execute(f"DELETE FROM roast_records WHERE roast_id IN ({placeholders})", expired_ids)
                cur.execute(f"DELETE FROM favorites WHERE roast_id IN ({placeholders})", expired_ids)
                stats["expired_by_age"] = len(expired_ids)

            # 2) 每用户配额清理：找出超过 500 条的用户，删掉最老的
            users = cur.execute(
                f"SELECT openid, COUNT(*) AS c FROM roast_records WHERE openid IS NOT NULL GROUP BY openid HAVING c > {p}",
                (HISTORY_MAX_PER_USER,),
            ).fetchall()
            for row in users:
                user_openid, c = row["openid"], int(row["c"])
                over = c - HISTORY_MAX_PER_USER
                # 找到最老的 over 条 roast_id
                olds = cur.execute(
                    f"""
                    SELECT roast_id FROM roast_records
                    WHERE openid={p}
                    ORDER BY created_at ASC
                    LIMIT {p}
                    """,
                    (user_openid, over),
                ).fetchall()
                old_ids = [r["roast_id"] for r in olds]
                if old_ids:
                    placeholders = ",".join([p] * len(old_ids))
                    # 仅删非收藏项，收藏是用户主动珍藏的，永久保留
                    cur.execute(
                        f"""
                        DELETE FROM roast_records
                        WHERE roast_id IN ({placeholders})
                          AND roast_id NOT IN (SELECT roast_id FROM favorites WHERE openid={p})
                        """,
                        old_ids + [user_openid],
                    )
                    stats["trimmed_by_quota"] += cur.rowcount

            # 3) 限流表：3 天前的日计数无用了
            cutoff = (date.today().toordinal() - 3)
            # 用文本比较也 OK（YYYY-MM-DD 字符串可字典序比较）
            cutoff_str = date.fromordinal(cutoff).isoformat()
            r = cur.execute(f"DELETE FROM rate_limits WHERE day < {p}", (cutoff_str,))
            stats["rate_limit_purged"] = r.rowcount

        if any(v for v in stats.values()):
            logger.info("[Cleanup] 清理完成：%s", stats)
        return stats

    # ---------- 卡片埋点 ----------
    ALLOWED_EVENTS = ("generate", "save", "share")

    def log_card_event(
        self,
        template: str,
        event: str,
        openid: Optional[str] = None,
        roast_id: Optional[str] = None,
    ) -> bool:
        """
        记录一次卡片事件。
        - template: 卡片 key（tarot / rx / ...）
        - event: 事件类型（generate / save / share）
        - openid / roast_id: 可空（generate 事件后端自动带；save/share 前端调用带）
        返回 True 表示写入成功；参数不合法或写库失败返回 False（不抛，静默）。
        """
        if not template or event not in self.ALLOWED_EVENTS:
            return False
        p = ph()
        try:
            with cursor() as cur:
                cur.execute(
                    f"INSERT INTO card_events (openid, roast_id, template, event, created_at) "
                    f"VALUES ({p}, {p}, {p}, {p}, {p})",
                    (openid, roast_id, template, event, time.time()),
                )
            return True
        except Exception as e:
            logger.warning("[Analytics] 埋点写入失败 template=%s event=%s err=%s", template, event, e)
            return False

    def stats_by_template(self, days: int = 7) -> list[dict]:
        """
        近 N 天各模板的三个事件汇总。
        返回结构：[
          {"template": "tarot", "generate": 120, "save": 30, "share": 12,
           "saveRate": 0.25, "shareRate": 0.10},
          ...
        ]
        按 generate 数降序排列，便于一眼看出最受欢迎的卡片。
        """
        days = max(1, min(365, days))
        threshold = time.time() - days * 86400
        p = ph()
        with cursor() as cur:
            rows = cur.execute(
                f"""
                SELECT template, event, COUNT(*) AS c
                FROM card_events
                WHERE created_at >= {p}
                GROUP BY template, event
                """,
                (threshold,),
            ).fetchall()
        # 聚合成 {template: {generate: n, save: n, share: n}}
        agg: dict[str, dict[str, int]] = {}
        for r in rows:
            t = r["template"]
            e = r["event"]
            c = int(r["c"])
            agg.setdefault(t, {"generate": 0, "save": 0, "share": 0})
            if e in agg[t]:
                agg[t][e] = c
        result: list[dict] = []
        for t, counts in agg.items():
            gen = counts["generate"]
            save = counts["save"]
            share = counts["share"]
            result.append({
                "template": t,
                "generate": gen,
                "save": save,
                "share": share,
                "saveRate": round(save / gen, 3) if gen else 0.0,
                "shareRate": round(share / gen, 3) if gen else 0.0,
            })
        # 按生成数降序，其次按保存数
        result.sort(key=lambda x: (x["generate"], x["save"]), reverse=True)
        return result

    # ---------- Admin 查询 ----------
    def overview(self) -> dict:
        """
        后台概览：总用户数、总骂醒数、今日骂醒数、总收藏数、今日新增用户。
        用户数以 roast_records 里的 distinct openid 估算（跳过 dev-anon）。
        """
        p = ph()
        today = date.today().isoformat()
        today_ts = _today_start_ts()
        with cursor() as cur:
            total_users = _first_col(cur.execute(
                f"SELECT COUNT(DISTINCT openid) AS c FROM roast_records "
                f"WHERE openid IS NOT NULL AND openid <> {p}",
                ("dev-anon",),
            ).fetchone())
            total_roasts = _first_col(cur.execute(
                "SELECT COUNT(*) AS c FROM roast_records"
            ).fetchone())
            today_roasts = _first_col(cur.execute(
                f"SELECT COUNT(*) AS c FROM roast_records WHERE created_at >= {p}",
                (today_ts,),
            ).fetchone())
            total_favorites = _first_col(cur.execute(
                "SELECT COUNT(*) AS c FROM favorites"
            ).fetchone())
            today_new_users = _first_col(cur.execute(
                f"""
                SELECT COUNT(*) AS c FROM (
                    SELECT openid, MIN(created_at) AS first_seen
                    FROM roast_records
                    WHERE openid IS NOT NULL AND openid <> {p}
                    GROUP BY openid
                ) t WHERE t.first_seen >= {p}
                """,
                ("dev-anon", today_ts),
            ).fetchone())
        return {
            "totalUsers": int(total_users),
            "totalRoasts": int(total_roasts),
            "todayRoasts": int(today_roasts),
            "totalFavorites": int(total_favorites),
            "todayNewUsers": int(today_new_users),
            "today": today,
        }

    def admin_list_records(
        self,
        page: int = 1,
        size: int = 20,
        style: Optional[str] = None,
        favorited_only: bool = False,
        since_ts: Optional[float] = None,
        until_ts: Optional[float] = None,
    ) -> tuple[list[dict], int]:
        """
        Admin 用：分页查询全量骂醒记录（跨用户），可按风格 / 时间范围 / 仅收藏筛选。
        返回原始 dict 行（含 openid 全字段），是否脱敏由调用方决定。
        """
        page = max(1, page)
        size = max(1, min(100, size))
        offset = (page - 1) * size
        p = ph()

        where = ["1=1"]
        params: list = []
        if style:
            where.append(f"r.style={p}")
            params.append(style)
        if since_ts is not None:
            where.append(f"r.created_at>={p}")
            params.append(since_ts)
        if until_ts is not None:
            where.append(f"r.created_at<{p}")
            params.append(until_ts)

        join = ""
        if favorited_only:
            join = "INNER JOIN favorites f ON f.roast_id = r.roast_id"

        where_sql = " AND ".join(where)

        count_sql = f"SELECT COUNT(DISTINCT r.roast_id) AS c FROM roast_records r {join} WHERE {where_sql}"
        list_sql = (
            f"SELECT DISTINCT r.roast_id, r.openid, r.user_input, r.content, r.style, r.provider, r.created_at "
            f"FROM roast_records r {join} WHERE {where_sql} "
            f"ORDER BY r.created_at DESC LIMIT {p} OFFSET {p}"
        )
        with cursor() as cur:
            total = _first_col(cur.execute(count_sql, tuple(params)).fetchone())
            rows = cur.execute(list_sql, tuple(params + [size, offset])).fetchall()

        # 转成 dict，方便 admin 层灵活脱敏
        result = [
            {
                "roastId": r["roast_id"],
                "openid": r["openid"],
                "userInput": r["user_input"],
                "content": r["content"],
                "style": r["style"],
                "provider": r["provider"],
                "createdAt": float(r["created_at"]),
            }
            for r in rows
        ]
        return result, int(total)

    def admin_get_record(self, roast_id: str) -> Optional[dict]:
        """Admin 查询单条完整记录 + 是否被收藏"""
        p = ph()
        with cursor() as cur:
            row = cur.execute(
                f"SELECT * FROM roast_records WHERE roast_id={p}",
                (roast_id,),
            ).fetchone()
            if not row:
                return None
            fav_row = cur.execute(
                f"SELECT COUNT(*) AS c FROM favorites WHERE roast_id={p}",
                (roast_id,),
            ).fetchone()
            fav_count = int(_first_col(fav_row))
        return {
            "roastId": row["roast_id"],
            "openid": row["openid"],
            "userInput": row["user_input"],
            "content": row["content"],
            "style": row["style"],
            "provider": row["provider"],
            "createdAt": float(row["created_at"]),
            "favoriteCount": fav_count,
        }

    # ---------- 内部工具 ----------
    @staticmethod
    def _row_to_record(row) -> RoastRecord:
        return RoastRecord(
            roast_id=row["roast_id"],
            openid=row["openid"],
            user_input=row["user_input"],
            content=row["content"],
            style=RoastStyle.from_key(row["style"]),
            provider=row["provider"],
            created_at=float(row["created_at"]),
        )


def _first_col(row):
    """
    兼容 MySQL dictionary cursor（返回 dict）与 SQLite Row（支持索引 0）。
    统一取第一列值。
    """
    if row is None:
        return 0
    if isinstance(row, dict):
        # MySQL dictionary cursor：COUNT(*) 若无别名 key 是 'COUNT(*)'；
        # 我们统一在 SQL 里加 AS c 别名，这里优先取 'c'
        if "c" in row:
            return row["c"]
        # 兜底：取第一个 value
        return next(iter(row.values()))
    # sqlite3.Row 支持索引
    return row[0]


def _today_start_ts() -> float:
    """今日 00:00 的 unix 时间戳（本地时区）"""
    now = datetime.now()
    start = datetime(now.year, now.month, now.day)
    return start.timestamp()


# 全局单例
repo = RoastRecordRepository()
