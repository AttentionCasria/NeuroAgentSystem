package com.it.service.impl;

import com.it.mapper.QuesMapper;
import com.it.pojo.AiResponse;
import com.it.pojo.AnswerVO;
import com.it.pojo.Talk;
import com.it.service.QuesService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestTemplate;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
public class QuesServiceImpl implements QuesService {
    @Autowired
    private QuesMapper quesMapper;

    @Autowired
    private RestTemplate restTemplate;

    @Value("${ai.api.url}")  // 注入配置的 URL
    private String aiApiUrl;

    @Override
    @Transactional(rollbackFor = {Exception.class})
    public AnswerVO getQues(String question, Integer talkId, Integer userId) {
        String preAnswer = "";
        // 局部变量存储当前对话，避免线程安全问题和NPE


        String now = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"));
        AiResponse aiResponse=null;


        if (talkId != null && quesMapper.notNULL(userId,talkId)) {
            // 从数据库获取历史对话总结内容
            preAnswer = quesMapper.findExContent(userId,talkId);
            // 获取AI模型完整响应（包含result和summary）
            aiResponse = callFastAPI(question, preAnswer);
            String updateTime = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"));

            Talk currentTalk = Talk.builder()
                        .id(talkId)
                        .userId(userId)
                        .content(aiResponse.getSummary())
                        .createTime(now)
                        .updateTime(updateTime)
                        .build();
            // 调用mapper更新对话（需在QuesMapper中添加updateTalk方法）
            quesMapper.insertContent(userId,talkId,question,now);
            quesMapper.insertContent(userId,talkId,aiResponse.getResult(),now);
            quesMapper.updateTalk(currentTalk);
            // 构建AnswerVO对象
            AnswerVO answerVO = new AnswerVO();
            answerVO.setContent(aiResponse.getResult());
            return answerVO; // 返回AI回答结果
        }
        else {
            aiResponse = callFastAPI(question, preAnswer);
            String updateTime = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"));
            Talk currentTalk = Talk.builder()
                        .userId(userId)
                        .title(aiResponse.getName())
                        .content(aiResponse.getSummary())
                        .createTime(now)
                        .updateTime(updateTime)
                        .build();
            quesMapper.insertTalk(currentTalk); // 插入后自动生成ID（通过useGeneratedKeys）
            quesMapper.insertContent(userId,currentTalk.getId(),question,now);
            quesMapper.insertContent(userId,currentTalk.getId(),aiResponse.getResult(),now);

            // 构建AnswerVO对象
            AnswerVO answerVO = new AnswerVO();
            answerVO.setContent(aiResponse.getResult());
            answerVO.setTalkId(currentTalk.getId());
            answerVO.setTitle(aiResponse.getName());
            return answerVO; // 返回AI回答结果
        }
    }
    // 修改返回类型为AiResponse，而非String
    private AiResponse callFastAPI(String question, String preAnswer) {
        try {
            Map<String, Object> request = new HashMap<>();
            request.put("question", question);
            request.put("round", 2);
            request.put("all_info", preAnswer);

            // 直接返回完整响应对象（包含result和summary）
            return restTemplate.postForObject(aiApiUrl, request, AiResponse.class);

        } catch (Exception e) {
            e.printStackTrace();
            // 异常时返回默认响应对象
            AiResponse errorResponse = new AiResponse();
            errorResponse.setResult("调用AI模型时发生错误: " + e.getMessage());
            errorResponse.setSummary("");
            return errorResponse;
        }
    }



    @Override
    public List<String> getPreContent(Integer userId, Integer talkId) {
        List<String> preContent = quesMapper.findAllExContent(userId,talkId);
        return preContent;
    }
}