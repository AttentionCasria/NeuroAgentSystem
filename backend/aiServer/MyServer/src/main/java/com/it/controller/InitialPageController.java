package com.it.controller;

import com.it.Utils.ThreadLocalUtil;
import com.it.pojo.Result;
import com.it.service.InitialPageService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@RestController
@CrossOrigin("*")
@RequestMapping("/api/user")
@Slf4j
public class InitialPageController {
    @Autowired
    private InitialPageService initialPageService;

    @GetMapping("/title")
    public Result getTitle(){
        return Result.success(initialPageService.getTalkIdAndTitle(ThreadLocalUtil.getCurrentId()));
    }

    @DeleteMapping("deleteTalk/{talk_id}")
    public Result deleteTalk(@PathVariable("talk_id") Integer talkId){
        Integer userId = ThreadLocalUtil.getCurrentId();
        initialPageService.deleteTalk(userId,talkId);
        return Result.success();
    }
}
