package com.it.controller;

import com.it.Utils.ThreadLocalUtil;
import com.it.pojo.AnswerVO;
import com.it.pojo.QuesParam;
import com.it.pojo.Result;
import com.it.service.QuesService;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;
import lombok.extern.slf4j.Slf4j;

import java.io.IOException;
import java.io.PrintWriter;
import java.util.List;

@Slf4j
@RestController
@CrossOrigin("*")
@RequestMapping("/api/user/ques")
public class QuesController {
    @Autowired
    private QuesService quesService;

    @PostMapping("/getQues")
    public Result getQues(@RequestBody QuesParam quesParam){
        log.info("用户在询问信息"+quesParam.getQuestion());
        AnswerVO answer = quesService.getQues(quesParam.getQuestion(),quesParam.getTalkId(), ThreadLocalUtil.getCurrentId());
        return Result.success(answer);
    }
    @GetMapping("/getQues/{talk_id}")
    public Result getPreContent(@PathVariable("talk_id") Integer talkId){
        Integer userId = ThreadLocalUtil.getCurrentId();
        List<String> preContent = quesService.getPreContent(userId,talkId);
        return Result.success(preContent);
    }


    @PostMapping("/newGetQues")
    public Result newGetQues(@RequestBody QuesParam quesParam){
        log.info("用户在询问信息"+quesParam.getQuestion());
        AnswerVO answer = quesService.getQues(quesParam.getQuestion(),quesParam.getTalkId(),ThreadLocalUtil.getCurrentId());
        return Result.success(answer);
    }

    @PostMapping("/streamingQues")
    public void streamingQues(@RequestBody QuesParam quesParam, HttpServletResponse response) {
        log.info("用户使用流式响应询问信息: {}", quesParam.getQuestion());
        Integer userId = ThreadLocalUtil.getCurrentId();

        response.setContentType("text/event-stream;charset=UTF-8");
        response.setHeader("Cache-Control", "no-cache");
        response.setHeader("Connection", "keep-alive");
        response.setHeader("Access-Control-Allow-Origin", "*");

        try (PrintWriter writer = response.getWriter()) {
            writer.write("data: [开始处理] 正在为您生成回答...\n\n");
            writer.flush();

            AnswerVO answer = quesService.getQues(quesParam.getQuestion(), quesParam.getTalkId(), userId);
            String content = answer.getContent();
            int chunkSize = 20;

            for (int i = 0; i < content.length(); i += chunkSize) {
                int end = Math.min(i + chunkSize, content.length());
                writer.write("data: " + content.substring(i, end) + "\n\n");
                writer.flush();
                Thread.sleep(100);
            }

            writer.write("data: [完成]\n\n");
            writer.flush();
        } catch (Exception e) {
            log.error("流式响应处理失败", e);
            try {
                response.getWriter().write("data: [错误] " + e.getMessage() + "\n\n");
                response.getWriter().flush();
            } catch (IOException ex) {
                log.error("发送错误消息失败", ex);
            }
        }
    }

}
