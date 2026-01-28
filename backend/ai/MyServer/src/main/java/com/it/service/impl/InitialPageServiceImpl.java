package com.it.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.it.mapper.InitialPageMapper;
import com.it.po.vo.InitialPageVO;
import com.it.pojo.Talk; // 确保引入正确的实体类（对应数据库表）
import com.it.service.IInitialPageService;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.stream.Collectors;

@Service
// extends ServiceImpl<Mapper, Entity> 提供了基础 CRUD 能力
public class InitialPageServiceImpl extends ServiceImpl<InitialPageMapper, Talk> implements IInitialPageService {

    /**
     * 注意：
     * 1.这里绝对不能注入 IInitialPageService initialPageService，否则会报错“循环依赖”。
     * 2.Controller 中调用的方法是 getPage，所以这里方法名必须是 getPage。
     */

    @Override
    public List<InitialPageVO> getPage(Integer userId) {
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
    public void deleteTalk(Integer userId, Integer talkId) {
        // 构造删除条件：userId 和 talkId ���须都匹配
        LambdaQueryWrapper<Talk> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Talk::getUserId, userId)
                .eq(Talk::getId, talkId); // 假设 Talk 的主键字段是 id (对应数据库 talk_id)

        this.remove(wrapper);
    }
}


//package com.it.service.impl;
//
//import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
//import com.it.mapper.InitialPageMapper;
//import com.it.po.vo.InitialPageVO;
//import com.it.pojo.Talk;
//import com.it.service.IInitialPageService;
//import com.it.service.ITalkService;
//import lombok.RequiredArgsConstructor;
//import org.springframework.stereotype.Service;
//
//import java.util.List;
//import java.util.stream.Collectors;
//
//@Service
//@RequiredArgsConstructor
//public class InitialPageServiceImpl extends ServiceImpl<InitialPageMapper, Talk> implements IInitialPageService {
//    private final IInitialPageService initialPageService;
//
//    @Override
//    public List<InitialPageVO> getPage(Integer currentId) {
//        List<Talk> list = initialPageService.query().eq("user_id", currentId)
//                .orderByDesc("update_time")
//                .list();
//        return list.stream().map(talk -> new InitialPageVO(talk.getId(), talk.getTitle())).collect(Collectors.toList());
//    }
//
//    @Override
//    public void deleteTalk(Integer userId, Integer talkId) {
//        initialPageService.removeById(talkId);
//    }
//}
