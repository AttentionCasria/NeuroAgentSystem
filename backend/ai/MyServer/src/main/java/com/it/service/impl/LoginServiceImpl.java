package com.it.service.impl;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.bean.copier.CopyOptions;
import cn.hutool.core.util.StrUtil;
import cn.hutool.json.JSONUtil;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.it.mapper.LoginMapper;
import com.it.po.dto.UserDTO;
import com.it.po.uo.LoginInfo;
import com.it.po.uo.User;
import com.it.pojo.Result;
import com.it.service.ILoginService;
import com.it.utils.JWT;
import com.it.utils.ThreadLocalUtil;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.util.HashMap;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.TimeUnit;

@Service
@RequiredArgsConstructor
@Slf4j
public class LoginServiceImpl extends ServiceImpl<LoginMapper, User> implements ILoginService {

    private final StringRedisTemplate stringRedisTemplate;

    @Override
    public Result loginInto(User u) {
        // 1 & 2. 缓存 User 逻辑保持不变...
        String username = u.getName();
        String userCacheKey = "cache:user:" + username;
        String userJson = stringRedisTemplate.opsForValue().get(userCacheKey);
        User dbUser = StrUtil.isNotBlank(userJson) ? JSONUtil.toBean(userJson, User.class) : query().eq("name", username).one();

        if (dbUser == null || !dbUser.getPassword().equals(u.getPassword())) {
            return Result.error("用户不存在或密码错误");
        }
        if (dbUser != null && StrUtil.isBlank(userJson)) {
            stringRedisTemplate.opsForValue().set(userCacheKey, JSONUtil.toJsonStr(dbUser), 30, TimeUnit.MINUTES);
        }

        // ⭐ 新增：登录前清理该用户的所有旧 Token（主动清理）
        cleanOldTokensBeforeLogin(dbUser.getId());

        // --- 核心修改：实现单设备登录 ---
        // 4. 生成唯一 JTI 并存入 Redis
        String jti = UUID.randomUUID().toString();
        // 键名格式：login:user:1
        String loginKey = "login:user:" + dbUser.getId();
        // 存入当前最新的 JTI，设置与 Token 相同的有效期（或略长）
        stringRedisTemplate.opsForValue().set(loginKey, jti, 3, TimeUnit.DAYS);
        log.info("用户 {} 登录，生成 JTI: {}", dbUser.getId(), jti);

        // 5. 生成 Token，带上 id 和 jti
        Map<String, Object> claims = new HashMap<>();
        claims.put("id", dbUser.getId());
        claims.put("name", dbUser.getName());
        claims.put("jti", jti); // 必须放入 JWT
        String token = JWT.generateToken(claims);

        // 6. 存入 Token 详情（你原有逻辑，用于存放 UserDTO）
        UserDTO userDTO = BeanUtil.copyProperties(dbUser, UserDTO.class);
        Map<String, Object> userMap = BeanUtil.beanToMap(userDTO, new HashMap<>(),
                new CopyOptions().setIgnoreNullValue(true)
                        .setFieldValueEditor((fieldName, fieldValue) -> fieldValue.toString()));

        String tokenKey = "user:token:" + token;
        stringRedisTemplate.opsForHash().putAll(tokenKey, userMap);
        stringRedisTemplate.expire(tokenKey, 120, TimeUnit.MINUTES);

        ThreadLocalUtil.setCurrentUser(userDTO);
        return Result.success(new LoginInfo(dbUser.getName(), dbUser.getImage(), token));
    }

    @Override
    public Result logOut(String token) {
        if (StrUtil.isBlank(token)) return Result.error("Token为空");
        if (token.startsWith("Bearer ")) token = token.substring(7);

        try {
            // 退出时清除单点登录限制
            Integer userId = JWT.getUserIdFromToken(token);
            stringRedisTemplate.delete("login:user:" + userId);

            // 清除原有 Token 数据
            stringRedisTemplate.delete("user:token:" + token);

            UserDTO currentUser = ThreadLocalUtil.getCurrentUser();
            if (currentUser != null) {
                stringRedisTemplate.delete("cache:user:" + currentUser.getName());
            }
            ThreadLocalUtil.removeCurrentUser();
            log.info("用户 {} 退出登录成功", userId);
        } catch (Exception e) {
            log.error("注销异常", e);
        }
        return Result.success("退出成功");
    }

    /**
     * ⭐ 登录前删除用户的所有旧 Token（更加主动和清爽）
     *
     * 作用：当���户在新设备登录时，自动删除旧设备上的 Token 数据
     * 这样旧设备再使用旧 Token 访问时，会因为 Redis 中找不到而被拒绝
     *
     * @param userId 用户 ID
     */
    private void cleanOldTokensBeforeLogin(Integer userId) {
        try {
            // 扫描所有 user:token:* 的 key
            Set<String> tokenKeys = stringRedisTemplate.keys("user:token:*");

            if (tokenKeys != null && !tokenKeys.isEmpty()) {
                int deleteCount = 0;
                for (String tokenKey : tokenKeys) {
                    // 获取 token 对应的用户信息
                    Map<Object, Object> userMap = stringRedisTemplate.opsForHash().entries(tokenKey);
                    if (!userMap.isEmpty()) {
                        Object userIdObj = userMap.get("id");
                        // 如果是当前用户的 Token，则删除
                        if (userIdObj != null && userId.equals(Integer.valueOf(userIdObj.toString()))) {
                            log.info("登录前清理用户 {} 的旧 Token: {}", userId, tokenKey);
                            stringRedisTemplate.delete(tokenKey);
                            deleteCount++;
                        }
                    }
                }
                if (deleteCount > 0) {
                    log.info("用户 {} 登录时清理了 {} 个旧 Token", userId, deleteCount);
                }
            }
        } catch (Exception e) {
            log.error("清理旧 Token 异常: {}", e.getMessage());
        }
    }
}