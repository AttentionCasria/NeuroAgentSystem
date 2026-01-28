package com.it.controller;

import com.it.utils.ThreadLocalUtil;
import com.it.po.vo.AnswerVO;
import com.it.po.uo.QuesParam;
import com.it.pojo.Result;
import com.it.service.IQuesService;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;
import lombok.extern.slf4j.Slf4j;

import java.io.IOException;
import java.io.PrintWriter;
import java.util.List;

@Slf4j
@RestController
@CrossOrigin("*")
@RequestMapping("/api/user/ques")
@RequiredArgsConstructor
public class QuesController {

    private final IQuesService quesService;

    @PostMapping("/getQues")
    public Result getQues(@RequestBody QuesParam quesParam, @RequestHeader(value = "token", required = false) String token)
    {
        log.info("用户在询问信息"+quesParam.getQuestion());
        return Result.success(quesService.getQues(quesParam,ThreadLocalUtil.getCurrentUser().getId(),token));
    }
    @GetMapping("/getQues/{talk_id}")
    public Result getPreContent(@PathVariable("talk_id") Integer talkId){
        Integer userId = ThreadLocalUtil.getCurrentUser().getId();
        return Result.success(quesService.getPreContent(userId,talkId));
    }


    @PostMapping("/newGetQues")
    public Result newGetQues(@RequestBody QuesParam quesParam, @RequestHeader(value = "token", required = false) String token){
        log.info("用户在询问信息"+quesParam.getQuestion());
        return Result.success(quesService.getQues(quesParam,ThreadLocalUtil.getCurrentUser().getId(),token));
    }

    @PostMapping("/streamingQues")
    public void streamingQues(@RequestBody QuesParam quesParam,
                              HttpServletResponse response,
                              @RequestHeader(value = "token", required = false) String token) {
        log.info("用户使用流式响应询问信息: {}", quesParam.getQuestion());
        Integer userId = ThreadLocalUtil.getCurrentUser().getId();

        response.setContentType("text/event-stream;charset=UTF-8");
        response.setHeader("Cache-Control", "no-cache");
        response.setHeader("Connection", "keep-alive");
        response.setHeader("Access-Control-Allow-Origin", "*");

        try (PrintWriter writer = response.getWriter()) {
            writer.write("data: [开始处理] 正在为您生成回答...\n\n");
            writer.flush();

            AnswerVO answer = quesService.getQues(quesParam, userId,token);
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
