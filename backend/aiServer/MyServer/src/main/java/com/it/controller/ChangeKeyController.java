package com.it.controller;

import com.it.Utils.ThreadLocalUtil;
import com.it.pojo.Result;
import com.it.pojo.User;
import com.it.pojo.UserDTO;
import com.it.service.ChangeKeyService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@RestController
@CrossOrigin("*")
@RequestMapping("/api/user/showInfo")
public class ChangeKeyController {
    @Autowired
    private ChangeKeyService changeKeyService;


    @PutMapping("/changeKey")
    public Result changeKey(@RequestBody UserDTO userDTO) {
        userDTO.setId(ThreadLocalUtil.getCurrentId());
        changeKeyService.changeKeyById(userDTO);
        return Result.success();
    }

    @GetMapping
    public Result getUserInfo() {
        String name = changeKeyService.getUserInfo(ThreadLocalUtil.getCurrentId());
        return Result.success(name);
    }
}
