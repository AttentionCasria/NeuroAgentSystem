package com.it.service;

import com.it.po.uo.QuesParam;
import com.it.po.vo.AnswerVO;
import com.it.pojo.Result;

import java.util.List;

public interface IQuesService {
     AnswerVO getQues(QuesParam quesParam, Integer userId, String token);

     /**
      * 获取历史内容（如果你还要这个接口）
      */
     List<String> getPreContent(Integer userId, Integer talkId);
}
