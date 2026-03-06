package com.it.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.it.mapper.InitialPageMapper;
import com.it.po.uo.Cont;
import com.it.po.vo.InitialPageVO;
import com.it.pojo.Talk; // 确保引入正确的实体类（对应数据库表）
import com.it.service.IContService;
import com.it.service.IInitialPageService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.stream.Collectors;

@Service
@Transactional
@RequiredArgsConstructor
@Slf4j
public class InitialPageServiceImpl extends ServiceImpl<InitialPageMapper, Talk> implements IInitialPageService {

    /**
     * 注意：
     * 1.这里绝对不能注入 IInitialPageService initialPageService，否则会报错“循环依赖”。
     * 2.Controller 中调用的方法是 getPage，所以这里方法名必须是 getPage。
     */
    private final StringRedisTemplate stringRedisTemplate;
    private final IContService contService;

    @Override
    public List<InitialPageVO> getPage(Long userId) {
        // 使用 MyBatis-Plus 的 LambdaQuery 查询 Talk 表
        List<Talk> talks = this.lambdaQuery()
                .eq(Talk::getUserId, userId)
                .orderByDesc(Talk::getUpdateTime)
                .list();

        // 将 Entity (Talk) 转换为 VO (InitialPageVO)
        // 确保 InitialPageVO 加了 @AllArgsConstructor 注解
        return talks.stream()
                .map(talk -> new InitialPageVO(talk.getId(), talk.getTitle()))
                .collect(Collectors.toList());
    }

    @Override
    @Transactional
    public void deleteTalk(Long userId, Long talkId) {
        // 1. 验证权限：确保这个对话属于当前用户
        Talk talk = this.getById(talkId);
        if (talk == null || !talk.getUserId().equals(userId)) {
            throw new RuntimeException("无权删除此对话");
        }

        // 2. 删除 Redis 缓存
        try {
            String historyKey = "chat:history:" + userId + ":" + talkId;
            String streamKey = "chat:stream:" + userId + ":" + talkId;
            stringRedisTemplate.delete(historyKey);
            stringRedisTemplate.delete(streamKey);
            log.info("删除对话缓存: talkId={}, keys=[{}, {}]", talkId, historyKey, streamKey);
        } catch (Exception e) {
            log.warn("删除缓存失败: talkId={}, err={}", talkId, e.getMessage());
        }

        // 3. 删除对话内容（Cont 表）
        LambdaQueryWrapper<Cont> contWrapper = new LambdaQueryWrapper<>();
        contWrapper.eq(Cont::getUserId, userId)
                .eq(Cont::getTalkId, talkId);

        // 注入 ContService 或直接使用 baseMapper
        int contDeleted = contService.remove(contWrapper) ? 1 : 0;
        log.info("删除对话内容: talkId={}, 删除条数={}", talkId, contDeleted);

        // 4. 删除对话记录（Talk 表）
        LambdaQueryWrapper<Talk> talkWrapper = new LambdaQueryWrapper<>();
        talkWrapper.eq(Talk::getUserId, userId)
                .eq(Talk::getId, talkId);

        boolean talkDeleted = this.remove(talkWrapper);
        log.info("删除对话记录: talkId={}, 结果={}", talkId, talkDeleted);

        if (!talkDeleted) {
            throw new RuntimeException("删除对话失败");
        }
    }
}

