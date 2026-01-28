package com.it.interceptor;

import com.it.utils.ThreadLocalUtil;
import com.it.utils.JWT;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.extern.slf4j.Slf4j;

import org.springframework.web.servlet.HandlerInterceptor;

@Slf4j
public class Tokeninterceptor implements HandlerInterceptor {

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) {
        // 打印当前拦截到的路径，看看是不是登录路径没被排除掉
        log.info("当前拦截到的路径：{}", request.getRequestURI());
        // 直接看 ThreadLocalUtil 里有没有用户对象
        if (ThreadLocalUtil.getCurrentUser() == null) {
            log.info("用户未登录，拒绝访问");
            response.setStatus(401);
            return false;
        }
        return true; // 有用户，放行
    }

}
