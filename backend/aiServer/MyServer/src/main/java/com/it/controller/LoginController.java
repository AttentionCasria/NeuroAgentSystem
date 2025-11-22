package com.it.controller;

import com.it.Utils.ThreadLocalUtil;
import com.it.mapper.RegiMapper;
import com.it.pojo.*;
import com.it.service.LoginService;
import com.it.service.RegiService;
import jakarta.servlet.http.HttpServletRequest;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.*;

@RestController
@CrossOrigin("*")
@RequestMapping("/api/user")
@Slf4j
public class LoginController {
    @Autowired
    RegiService regiService;
    @Autowired
    LoginService loginService;
    @Autowired
    private TokenBlacklistService tokenBlacklistService;


    @PostMapping("/register")
    public Result register(@RequestBody User user){
        if(user==null){
            throw new RuntimeException("用户不存在");
        }
        regiService.insertUser(user);
        ThreadLocalUtil.setCurrentId(user.getId());
        log.info("注册用户:{}",user);
        LoginRegisterInfo lg =loginService.loginRegisterInto(user);
        if (lg != null) {
            return Result.success(lg);
        }
        return Result.error("密码或者账户错误");
    }

    @PostMapping("/login")
    public Result login(@RequestBody User user) {
        try {
            LoginInfo lg = loginService.loginInto(user);
            return Result.success(lg);
        } catch (RuntimeException e) {
            return Result.error(e.getMessage());  // 把异常信息返回给前端
        }
    }


    @PostMapping("/logOut")
    public Result logOut(HttpServletRequest request){
        String token = request.getHeader("token");
        if (token != null && !token.isEmpty()) {
            tokenBlacklistService.addToBlacklist(token);
            log.info("用户注销，token已加入黑名单");
        }
        ThreadLocalUtil.removeCurrentId();
        return Result.success("退出成功");
    }
}
