package com.it.interceptor;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.util.StrUtil;
import com.it.po.dto.UserDTO;
import com.it.utils.JWT;
import com.it.utils.ThreadLocalUtil;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.web.servlet.HandlerInterceptor;

import java.util.Map;
import java.util.concurrent.TimeUnit;

@Slf4j
public class RefreshTokenInterceptor implements HandlerInterceptor {

    private final StringRedisTemplate stringRedisTemplate;
    public RefreshTokenInterceptor(StringRedisTemplate stringRedisTemplate) {
        this.stringRedisTemplate = stringRedisTemplate;
    }

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) {
        // 1. 获取 token
        String token = request.getHeader("token");
        if (StrUtil.isBlank(token)) {
            return true; // 放行给下一个拦截器
        }
        try{
            System.out.println("==========================================================================");
            System.out.println("token: " + token);
            Integer userId = JWT.getUserIdFromToken(token);
        }catch(Exception e){
            log.info("token解析失败");
            response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
            return false;
        }
        // 2. 查询 Redis (注意：entries 不会返回 null)
        Map<Object, Object> userMap = stringRedisTemplate.opsForHash().entries("user:token:" + token);
        if (userMap.isEmpty()) {
            return true; // 没查到也放行
        }

        // 3. 查到了，存入 ThreadLocal
        UserDTO userDTO = BeanUtil.fillBeanWithMap(userMap, new UserDTO(), false);
        ThreadLocalUtil.setCurrentUser(userDTO);

        // 4. 刷新有效期
        stringRedisTemplate.expire("user:token:" + token, 30, TimeUnit.MINUTES);
        return true;
    }

    @Override
    public void afterCompletion(HttpServletRequest request, HttpServletResponse response, Object handler, Exception ex) {
        ThreadLocalUtil.removeCurrentUser();
    }
}