package com.it.pojo;

import org.springframework.stereotype.Service;

import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

@Service
public class TokenBlacklistService {
    // 使用ConcurrentHashMap保证线程安全
    private final Set<String> blacklistedTokens = ConcurrentHashMap.newKeySet();

    /**
     * 将token加入黑名单
     */
    public void addToBlacklist(String token) {
        blacklistedTokens.add(token);
    }

    /**
     * 检查token是否在黑名单中
     */
    public boolean isBlacklisted(String token) {
        return blacklistedTokens.contains(token);
    }
}
