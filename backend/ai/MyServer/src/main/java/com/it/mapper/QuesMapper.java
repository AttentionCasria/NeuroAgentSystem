package com.it.mapper;

import com.it.pojo.Talk;
import org.apache.ibatis.annotations.Mapper;

import java.util.List;

@Mapper
public interface QuesMapper {
    public String findExContent(Integer userId, Integer talkId);

    boolean notNULL(Integer userId, Integer talkId);

    void insertTalk(Talk talk);

    void updateTalk(Talk currentTalk);

    List<String> findAllExContent(Integer userId, Integer talkId);

    void insertContent(Integer userId, Integer talkId, String content, String createTime);
}
