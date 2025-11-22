package com.it.service;

import com.it.pojo.AnswerVO;

import java.util.List;

public interface QuesService {
    AnswerVO getQues(String question, Integer talkId, Integer userId);

    List<String> getPreContent(Integer userId, Integer talkId);
}
