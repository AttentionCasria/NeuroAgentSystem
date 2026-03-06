package com.it.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.toolkit.IdWorker;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import com.it.po.uo.Cont;
import com.it.pojo.Talk;
import com.it.service.AIStreamingService;
import com.it.service.IContService;
import com.it.service.ITalkService;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.redisson.api.RRateLimiter;
import org.redisson.api.RSemaphore;
import org.redisson.api.RateIntervalUnit;
import org.redisson.api.RateType;
import org.redisson.api.RedissonClient;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.script.DefaultRedisScript;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Slf4j
public class AIStreamingServiceImpl implements AIStreamingService {

    private final WebClient webClient;
    private final StringRedisTemplate stringRedisTemplate;
    private final RedissonClient redissonClient;
    private final ITalkService talkService;
    private final IContService contService;
    private final ConversationPersistenceService conversationPersistenceService;

    private final ObjectMapper objectMapper = new ObjectMapper()
            .registerModule(new JavaTimeModule())
            .disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS);

    private static final long CACHE_TTL = 1;
    private static final String HISTORY_KEY_PREFIX = "chat:history:";
    private static final DateTimeFormatter TIME_FORMATTER = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    private static final String SEMAPHORE_KEY = "ai:concurrent";
    private static final int SEMAPHORE_PERMITS = 20;

    @PostConstruct
    public void init() {
        try {
            RSemaphore semaphore = redissonClient.getSemaphore(SEMAPHORE_KEY);
            semaphore.trySetPermits(SEMAPHORE_PERMITS);
            log.info("初始化 semaphore 完成: key={}, permits={}", SEMAPHORE_KEY, SEMAPHORE_PERMITS);
        } catch (Exception e) {
            log.warn("初始化 semaphore 失败: {}", e.getMessage(), e);
        }
    }

    @Transactional
    @Override
    public Long createNewTalk(Long userId) {
        LocalDateTime now = LocalDateTime.now();
        Long talkId = IdWorker.getId();
        Talk talk = Talk.builder()
                .id(talkId)
                .userId(userId)
                .title("新对话")
                .content("")
                .createTime(now)
                .updateTime(now)
                .build();

        log.info("准备保存 Talk: {}", talk);

        try {
            boolean saved = talkService.save(talk);
            log.info("talkService.save 返回: {} (talkId={})", saved, talkId);
            if (!saved) {
                throw new RuntimeException("创建新对话失败");
            }
        } catch (Exception e) {
            log.error("保存 Talk 异常: {}", e.getMessage(), e);
            throw e;
        }

        return talkId;
    }

    @Override
    public String getResumeContent(Long userId, Long talkId) {
        String key = buildRedisKey(userId, talkId);
        try {
            List<String> list = stringRedisTemplate.opsForList().range(key, 0, -1);
            if (list == null || list.isEmpty()) {
                log.debug("Redis list 为空或不存在: key={}", key);
                return null;
            }
            log.debug("Redis list 命中: key={}, size={}, sample={}", key, list.size(), list.get(0));
            return String.join("", list);
        } catch (Exception e) {
            log.error("读取 resume content 失败 userId:{} talkId:{} err:{}", userId, talkId, e.getMessage(), e);
            return null;
        }
    }

    @Transactional(readOnly = true)
    @Override
    public List<String> getPreContent(Long userId, Long talkId) {
        return getCachedHistory(userId, talkId).stream()
                .map(Cont::getContent)
                .collect(Collectors.toList());
    }

    private boolean tryAcquire(String key, int rate, int seconds) {
        try {
            RRateLimiter limiter = redissonClient.getRateLimiter(key);
            limiter.trySetRate(RateType.OVERALL, rate, seconds, RateIntervalUnit.SECONDS);
            boolean ok = limiter.tryAcquire();
            log.debug("限流 tryAcquire: key={}, rate={}, seconds={}, result={}", key, rate, seconds, ok);
            return ok;
        } catch (Exception e) {
            log.warn("限流器操作失败: key={}, err={}", key, e.getMessage(), e);
            return false;
        }
    }

    private Long incrWithExpire(String key, long expireSeconds) {
        String script = "local v = redis.call('incr', KEYS[1]); " +
                "if tonumber(v) == 1 then redis.call('expire', KEYS[1], ARGV[1]); end; return v;";
        DefaultRedisScript<Long> redisScript = new DefaultRedisScript<>(script, Long.class);
        try {
            Long v = stringRedisTemplate.execute(redisScript, Collections.singletonList(key), String.valueOf(expireSeconds));
            log.debug("incrWithExpire: key={}, expire={}, value={}", key, expireSeconds, v);
            return v;
        } catch (Exception e) {
            log.error("执行 incrWithExpire 失败: key={}, err={}", key, e.getMessage(), e);
            return null;
        }
    }

    @Override
    public Flux<String> streamChat(Long userId,
                                   Long talkId,
                                   String question,
                                   String token) {

        if (userId == null) {
            return Flux.just(buildError("未登录"));
        }

        // ========= 1️⃣ 自动创建对话 =========
        if (talkId == null || talkService.getById(talkId) == null) {
            talkId = createNewTalk(userId);
            log.info("自动创建新对话: userId={}, talkId={}", userId, talkId);
        }

        final Long finalTalkId = talkId;

        // ========= 2️⃣ 构建上下文 =========
        String historyText = buildHistoryContext(userId, finalTalkId);

        Map<String, Object> request = Map.of(
                "question", question,
                "round", 2,
                "all_info", historyText,
                "token", token
        );

        StringBuilder fullAnswer = new StringBuilder();
        final String[] generatedTitle = {null};

        return webClient.post()
                .uri("/model/get_result")
                .bodyValue(request)
                .retrieve()
                .bodyToFlux(String.class)

                .filter(line -> line != null && !line.trim().isEmpty())
                .map(String::trim)
                .map(line -> line.startsWith("data:")
                        ? line.substring(5).trim()
                        : line)
                .filter(line -> !line.isEmpty())
                .filter(line -> !"[DONE]".equalsIgnoreCase(line))

                .flatMap(line -> {
                    try {
                        JsonNode json = objectMapper.readTree(line);

                        // ====== 错误处理 ======
                        if (json.has("error")) {
                            return Flux.just(buildError(json.get("error").asText()));
                        }

                        // ====== 标题生成 ======
                        if (json.has("name") && generatedTitle[0] == null) {
                            generatedTitle[0] = json.get("name").asText();
                            tryUpdateTalkTitle(finalTalkId, generatedTitle[0]);
                        }

                        // ====== 正文流 ======
                        if (json.has("result")) {
                            String chunk = json.get("result").asText();
                            fullAnswer.append(chunk);

                            Map<String, Object> resp = new HashMap<>();
                            resp.put("type", "chunk");
                            resp.put("talkId", finalTalkId.toString());
                            resp.put("title", generatedTitle[0]);
                            resp.put("content", chunk);

                            return Flux.just(objectMapper.writeValueAsString(resp));
                        }

                        return Flux.empty();

                    } catch (Exception e) {
                        log.error("解析AI返回失败", e);
                        return Flux.empty();
                    }
                }, 1)

                .concatWith(Mono.fromCallable(() -> {

                    String finalTitle = generatedTitle[0];

                    if (finalTitle == null || finalTitle.isBlank()) {
                        finalTitle = buildTitleFromQuestion(question);
                        tryUpdateTalkTitle(finalTalkId, finalTitle);
                    }

                    log.info("准备持久化 - question: '{}', answer length: {}, talkId: {}",
                            question, fullAnswer.length(), finalTalkId);

                    if (question != null && !question.trim().isEmpty() && fullAnswer.length() > 0) {
                        conversationPersistenceService.persistConversation(
                                userId,
                                finalTalkId,
                                question,
                                fullAnswer.toString(),
                                "",
                                finalTitle
                        );
                        stringRedisTemplate.delete("chat:history:" + userId + ":" + finalTalkId);
                    }

                    Map<String, Object> done = new HashMap<>();
                    done.put("type", "done");
                    done.put("talkId", finalTalkId.toString());
                    done.put("title", finalTitle);

                    return objectMapper.writeValueAsString(done);
                }))

// ✅ 关键修复：发生异常也必须发 done
                .onErrorResume(e -> {
                    log.error("流式生成异常", e);

                    try {
                        Map<String, Object> error = new HashMap<>();
                        error.put("type", "error");
                        error.put("talkId", finalTalkId.toString());
                        error.put("message", e.getMessage() == null ? "AI 服务异常" : e.getMessage());

                        Map<String, Object> done = new HashMap<>();
                        done.put("type", "done");
                        done.put("talkId", finalTalkId.toString());
                        done.put("title", "异常结束");

                        return Flux.just(
                                objectMapper.writeValueAsString(error),
                                objectMapper.writeValueAsString(done)
                        );
                    } catch (Exception ex) {
                        return Flux.just("{\"type\":\"done\"}");
                    }
                })

                .doFinally(signal -> log.info("流完成: signal={}", signal));
    }
    private String buildError(String msg) {
        try {
            Map<String, Object> err = new HashMap<>();
            err.put("type", "error");
            err.put("message", msg);
            return objectMapper.writeValueAsString(err);
        } catch (Exception e) {
            return "{\"type\":\"error\",\"message\":\"系统错误\"}";
        }
    }

    @Override
    public Talk getTalkById(Long talkId) {
        if (talkId == null) return null;
        return talkService.getById(talkId);
    }

    @Transactional
    public void tryUpdateTalkTitle(Long talkId, String title) {
        if (talkId == null) return;
        if (title == null || title.trim().isEmpty()) return;

        try {
            Talk talk = talkService.getById(talkId);
            if (talk == null) return;

            // 只在还是“新对话”时更新，避免覆盖用户修改的标题
            if ("新对话".equals(talk.getTitle())) {
                talk.setTitle(title.trim());
                talkService.updateById(talk);
            }
        } catch (Exception e) {
            log.warn("更新对话标题失败: talkId={}, err={}", talkId, e.getMessage(), e);
        }
    }

    private String buildTitleFromQuestion(String question) {
        if (question == null) return "咨询";
        String t = question.trim().replaceAll("\\s+", " ");
        if (t.isEmpty()) return "咨询";
        return t.substring(0, Math.min(t.length(), 12));
    }

    private String buildHistoryContext(Long userId, Long talkId) {
        List<Cont> history = getCachedHistory(userId, talkId);
        if (history == null || history.isEmpty()) return "";

        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < history.size(); i++) {
            sb.append(i % 2 == 0 ? "user: " : "assistant: ")
                    .append(history.get(i).getContent()).append("\n");
        }
        return sb.toString();
    }

    private boolean allowAICircuit() {
        String state = stringRedisTemplate.opsForValue().get("ai:circuit");
        log.debug("检查熔断开关状态: {}", state);
        return !"open".equals(state);
    }

    private List<Cont> getCachedHistory(Long userId, Long talkId) {
        String key = buildHistoryKey(userId, talkId);
        String json = stringRedisTemplate.opsForValue().get(key);

        if (json != null && !json.isEmpty()) {
            try {
                List<Cont> cached = objectMapper.readValue(json, new com.fasterxml.jackson.core.type.TypeReference<>() {});
                log.debug("历史缓存命中: key={}, size={}", key, cached == null ? 0 : cached.size());
                return cached;
            } catch (Exception e) {
                log.error("解析历史记录缓存失败，将降级查询数据库", e);
            }
        } else {
            log.debug("历史缓存未命中: key={}", key);
        }

        return reloadHistoryToCache(userId, talkId);
    }

    private List<Cont> reloadHistoryToCache(Long userId, Long talkId) {
        List<Cont> history = contService.list(
                new LambdaQueryWrapper<Cont>()
                        .eq(Cont::getUserId, userId)
                        .eq(Cont::getTalkId, talkId)
                        .orderByAsc(Cont::getId)
        );

        log.debug("从 DB 加载历史记录: userId={}, talkId={}, size={}", userId, talkId, history == null ? 0 : history.size());

        try {
            String key = buildHistoryKey(userId, talkId);
            // 先删除旧缓存，再设置新缓存
            stringRedisTemplate.delete(key);
            stringRedisTemplate.opsForValue().set(key, objectMapper.writeValueAsString(history), 1, TimeUnit.HOURS);
            log.debug("历史记录已写入缓存: key={}", key);
        } catch (Exception e) {
            log.error("写入历史记录缓存失败", e);
        }

        return history;
    }

    private String buildRedisKey(Long userId, Long talkId) {
        return "chat:stream:" + userId + ":" + talkId;
    }

    private String buildHistoryKey(Long userId, Long talkId) {
        return HISTORY_KEY_PREFIX + userId + ":" + talkId;
    }
}