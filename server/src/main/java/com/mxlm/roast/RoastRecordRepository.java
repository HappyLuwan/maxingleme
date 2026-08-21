package com.mxlm.roast;

import cn.hutool.core.util.IdUtil;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

/**
 * 骂醒记录仓库（内存版）
 * <p>
 * 存储生成的骂醒记录，供后续生成卡片时读取。
 * <p>
 * TTL：默认 30 分钟自动清理，避免内存无限增长。
 * 未来可替换为 Redis / MySQL 实现。
 */
@Slf4j
@Repository
public class RoastRecordRepository {

    private static final long TTL_MINUTES = 30;

    private final ConcurrentHashMap<String, RoastRecord> store = new ConcurrentHashMap<>();

    /** 定时清理过期数据 */
    private final ScheduledExecutorService cleaner = Executors.newSingleThreadScheduledExecutor(r -> {
        Thread t = new Thread(r, "roast-record-cleaner");
        t.setDaemon(true);
        return t;
    });

    public RoastRecordRepository() {
        cleaner.scheduleAtFixedRate(this::cleanExpired, 5, 5, TimeUnit.MINUTES);
    }

    /**
     * 保存骂醒记录，自动生成 ID
     */
    public RoastRecord save(RoastRecord record) {
        if (record.getRoastId() == null) {
            record.setRoastId(IdUtil.fastSimpleUUID());
        }
        if (record.getCreatedAt() == null) {
            record.setCreatedAt(LocalDateTime.now());
        }
        store.put(record.getRoastId(), record);
        return record;
    }

    /**
     * 根据 ID 获取记录
     */
    public RoastRecord findById(String roastId) {
        return store.get(roastId);
    }

    /**
     * 清理过期记录
     */
    private void cleanExpired() {
        LocalDateTime threshold = LocalDateTime.now().minusMinutes(TTL_MINUTES);
        int before = store.size();
        store.entrySet().removeIf(e -> e.getValue().getCreatedAt().isBefore(threshold));
        int after = store.size();
        if (before != after) {
            log.info("[RoastRecordRepository] 清理过期记录 {} 条，当前剩余 {} 条", before - after, after);
        }
    }
}
