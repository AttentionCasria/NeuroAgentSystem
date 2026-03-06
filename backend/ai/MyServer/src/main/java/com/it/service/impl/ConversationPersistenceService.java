package com.it.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;

import com.it.po.uo.Cont;
import com.it.pojo.Talk;
import com.it.service.IContService;
import com.it.service.ITalkService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;

@Service
@RequiredArgsConstructor
@Slf4j
@Transactional
public class ConversationPersistenceService {

    private final IContService contService;
    private final ITalkService talkService;

    @Transactional
    public void persistConversation(Long userId, Long talkId, String question, String answer, String summary, String title) {
        LocalDateTime now = LocalDateTime.now();

        // 保存用户问题
        Cont userCont = new Cont();
        userCont.setUserId(userId);
        userCont.setTalkId(talkId);
        userCont.setContent(question);
        userCont.setCreateTime(now);
        contService.save(userCont);

        // 保存AI回答
        Cont aiCont = new Cont();
        aiCont.setUserId(userId);
        aiCont.setTalkId(talkId);
        aiCont.setContent(answer);
        aiCont.setCreateTime(now);
        contService.save(aiCont);

        // 可选：如果有summary，可以保存到另一个字段或单独的Cont，但根据代码兼容，暂不处理

        // 加载历史（可选，用于验证或日志）
        List<Cont> history = contService.list(new LambdaQueryWrapper<Cont>()
                .eq(Cont::getUserId, userId)
                .eq(Cont::getTalkId, talkId)
                .orderByAsc(Cont::getId));

        // 更新Talk
        Talk talk = talkService.getById(talkId);
        if (talk != null) {
            // 只在默认标题时更新
            if ("新对话".equals(talk.getTitle())
                    && title != null
                    && !title.isBlank()) {

                talk.setTitle(title);
                log.info("更新对话标题：talkId={}, title={}", talkId, title);
            }
            // 设置content为answer（或summary，如果有）
            String finalContent = summary != null && !summary.isEmpty() ? summary : answer;
            talk.setContent(finalContent);
            talk.setUpdateTime(now);
            talkService.updateById(talk);
        } else {
            log.warn("Talk不存在，无法更新: talkId={}", talkId);
        }
        // 清除历史缓存
        String historyKey = "chat:history:" + userId + ":" + talkId;
    }
}