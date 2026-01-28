package com.it.service.impl;


import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.it.mapper.QuesMapper;
import com.it.po.uo.Cont;
import com.it.po.uo.QuesParam;
import com.it.pojo.AiResponse;
import com.it.po.vo.AnswerVO;
import com.it.pojo.Talk;
import com.it.service.IContService;
import com.it.service.IQuesService;
import com.it.service.ITalkService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;
import org.springframework.web.client.RestTemplate;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;

@Service
@RequiredArgsConstructor
@Slf4j
public class QuesServiceImpl implements IQuesService {

    private final ITalkService talkService;
    private final IContService contService;
    private final RestTemplate restTemplate;
    private final StringRedisTemplate stringRedisTemplate;
    // ✅ 新增：用于 List<String> 和 JSON 字符串互转
    private final ObjectMapper objectMapper;

    @Value("${ai.api.url}")
    private String aiApiUrl;

    @Override
    @Transactional(rollbackFor = Exception.class)
    public AnswerVO getQues(QuesParam quesParam, Integer userId, String token) {

        Integer talkId = quesParam.getTalkId();
        String question = quesParam.getQuestion();

        String now = LocalDateTime.now()
                .format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"));

        Talk talk = null;
        String preSummary = "";

        /* ================= 1️⃣ 校验是否为历史对话（防越权） ================= */
        if (talkId != null) {
            String redisSummary = stringRedisTemplate.opsForValue().get("talk:" + userId + ":" + talkId);
            if (redisSummary != null) {
                preSummary = redisSummary;
            } else {
                talk = talkService.getOne(
                        new LambdaQueryWrapper<Talk>()
                                .eq(Talk::getId, talkId)
                                .eq(Talk::getUserId, userId)
                );
                if (talk != null) {
                    preSummary = talk.getContent();
                }
                if (preSummary != null) {
                    stringRedisTemplate.opsForValue().set("talk:" + talkId + ":" + userId, preSummary);
                }
            }
        }

        /* ================= 2️⃣ 调用 AI（不在事务关键路径） ================= */

        AiResponse aiResponse = callFastAPI(question, preSummary, token);

        stringRedisTemplate.opsForValue().set("talk:" + talkId + ":" + userId, aiResponse.getSummary(), 1, TimeUnit.HOURS);

        /* ================= 3️⃣ 落库 ================= */
        return saveChat(talk, userId, question, aiResponse, now);
    }

    /**
     * 数据库存储逻辑（单一职责）
     */
    private AnswerVO saveChat(
            Talk talk,
            Integer userId,
            String question,
            AiResponse aiResponse,
            String now
    ) {

        // 3.1 新对话
        if (talk == null) {
            talk = Talk.builder()
                    .userId(userId)
                    .title(aiResponse.getName())
                    .content(aiResponse.getSummary())
                    .createTime(now)
                    .updateTime(now)
                    .build();

            talkService.save(talk);
        }
        // 3.2 老对话
        else {
            talk.setContent(aiResponse.getSummary());
            talk.setUpdateTime(now);
            talkService.updateById(talk);
        }

        // 3.3 插入用户问题
        contService.save(buildCont(userId, talk.getId(), question, now));

        // 3.4 插入 AI 回答
        contService.save(buildCont(userId, talk.getId(), aiResponse.getResult(), now));

        String key  = "user:history:content:" + userId + ":" + talk.getId();
        stringRedisTemplate.opsForList().rightPushAll(key, List.of(question, aiResponse.getResult()));
        stringRedisTemplate.expire(key, 1, TimeUnit.HOURS);

        // 3.5 返回结果
        AnswerVO vo = new AnswerVO();
        vo.setTalkId(talk.getId());
        vo.setTitle(talk.getTitle());
        vo.setContent(aiResponse.getResult());

        return vo;
    }

    private Cont buildCont(Integer userId, Integer talkId, String content, String now) {
        Cont cont = new Cont();
        cont.setUserId(userId);
        cont.setTalkId(talkId);
        cont.setContent(content);
        cont.setCreateTime(now);
        return cont;
    }

    /**
     * AI 调用
     */
    private AiResponse callFastAPI(String question, String preAnswer, String token) {

        Map<String, Object> request = Map.of(
                "question", question,
                "round", 2,
                "all_info", preAnswer,
                "token", token
        );

        try {
            return restTemplate.postForObject(aiApiUrl, request, AiResponse.class);
        } catch (Exception e) {
            log.error("调用 FastAPI 失败: {}", e.getMessage(), e);
            return AiResponse.fail("AI 服务暂不可用");
        }
    }

    /**
     * 获取历史内容（如果你还要这个接口）
     */
    @Override
    public List<String> getPreContent(Integer userId, Integer talkId) {
        String key = "user:history:content:" + userId + ":" + talkId;

        // 1. 尝试从 Redis List 结构中获取所有元素
        // range(key, 0, -1) 表示从第一个(0)拿到最后一个(-1)
        List<String> cacheList = stringRedisTemplate.opsForList().range(key, 0, -1);

        if (cacheList != null && !cacheList.isEmpty()) {
            // 命中缓存，刷新过期时间
            stringRedisTemplate.expire(key, 1, TimeUnit.HOURS);
            return cacheList;
        }

        // 2. 缓存未命中，查数据库 (原有逻辑)
        List<String> dbResult = contService.list(
                new LambdaQueryWrapper<Cont>()
                        .eq(Cont::getUserId, userId)
                        .eq(Cont::getTalkId, talkId)
                        .orderByAsc(Cont::getId)
        ).stream().map(Cont::getContent).toList();

        // 3. 写入 Redis List
        // rightPushAll 会将 dbResult 中的元素一条一条地推入 Redis 的 List 中
        if (dbResult != null && !dbResult.isEmpty()) {
            stringRedisTemplate.delete(key); // 写入前先删除旧 key，防止追加重复数据或类型冲突
            stringRedisTemplate.opsForList().rightPushAll(key, dbResult);
            stringRedisTemplate.expire(key, 1, TimeUnit.HOURS);
        }

        return dbResult;
    }

}