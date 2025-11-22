package com.it.interceptor;


import com.it.Utils.ThreadLocalUtil;
import com.it.pojo.JWT;
import com.it.pojo.TokenBlacklistService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;

@Slf4j
@Component
public class Tokeninterceptor implements HandlerInterceptor {

    @Autowired
    private TokenBlacklistService tokenBlacklistService;

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) throws Exception {
        String requestURI = request.getRequestURI();
        if(requestURI.contains("/login")||requestURI.contains("/register")||requestURI.contains("/user/upload")){
            log.info("登陆或者注册或者上传图片，准许放行");
            return true;
        }
        String token = request.getHeader("token");

        System.out.println(token);
        if(token==null||token.isEmpty()){
            log.info("token不存在");
            response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
            return false;
        }

        // 检查token是否在黑名单中
        if (tokenBlacklistService.isBlacklisted(token)) {
            log.info("token已被注销");
            response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
            return false;
        }

        try{
            Integer userId = JWT.getUserIdFromToken(token);
            ThreadLocalUtil.setCurrentId(userId);
        }catch(Exception e){
            log.info("token解析失败");
            response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
            return false;
        }
        return true;
    }

    @Override
    public void afterCompletion(HttpServletRequest request, HttpServletResponse response, Object handler, Exception ex) throws Exception {
        // 请求完成后清除ThreadLocal，防止内存泄漏
        ThreadLocalUtil.removeCurrentId();
    }

}


