package com.it.controller;

import com.it.pojo.Result;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/monitor")
@RequiredArgsConstructor
@Slf4j
public class MonitorController {

    private final StringRedisTemplate stringRedisTemplate;

    @GetMapping("/rate-limit/status")
    public Result getRateLimitStatus() {
        Map<String, Object> status = new HashMap<>();
        
        try {
            // 获取失败次数
            String failureCountStr = stringRedisTemplate.opsForValue().get("login:failure:count");
            long failureCount = failureCountStr != null ? Long.parseLong(failureCountStr) : 0;
            
            // 获取成功次数
            String successCountStr = stringRedisTemplate.opsForValue().get("login:success:count");
            long successCount = successCountStr != null ? Long.parseLong(successCountStr) : 0;
            
            // 获取熔断器状态
            String circuitBreakerState = stringRedisTemplate.opsForValue().get("login:circuit:breaker");
            if (circuitBreakerState == null) {
                circuitBreakerState = "closed";
            }
            
            // 计算失败率
            long totalRequests = failureCount + successCount;
            double failureRate = totalRequests > 0 ? (double) failureCount / totalRequests * 100 : 0;
            
            status.put("failureCount", failureCount);
            status.put("successCount", successCount);
            status.put("totalRequests", totalRequests);
            status.put("failureRate", String.format("%.2f%%", failureRate));
            status.put("circuitBreakerState", circuitBreakerState);
            
            return Result.success(status);
        } catch (Exception e) {
            log.error("获取限流状态异常", e);
            return Result.error("获取状态失败");
        }
    }
    
    @GetMapping("/rate-limit/reset")
    public Result resetRateLimit() {
        try {
            // 清除所有计数器
            stringRedisTemplate.delete("login:failure:count");
            stringRedisTemplate.delete("login:success:count");
            stringRedisTemplate.delete("login:circuit:breaker");
            stringRedisTemplate.delete("login:circuit:half:open:time");
            stringRedisTemplate.delete("login:failure:window");
            stringRedisTemplate.delete("login:response:time:success");
            stringRedisTemplate.delete("login:response:time:failure");
            
            return Result.success("重置成功");
        } catch (Exception e) {
            log.error("重置限流状态异常", e);
            return Result.error("重置失败");
        }
    }
}