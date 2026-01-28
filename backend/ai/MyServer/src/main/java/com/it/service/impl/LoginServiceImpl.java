package com.it.service.impl;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.bean.copier.CopyOptions;
import cn.hutool.core.util.StrUtil;
import cn.hutool.json.JSONUtil; // 引入 JSON 工具
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.it.mapper.LoginMapper;
import com.it.po.dto.UserDTO;
import com.it.po.uo.LoginInfo;
import com.it.po.uo.User;
import com.it.pojo.*;
import com.it.service.ILoginService;
import com.it.utils.JWT;
import com.it.utils.ThreadLocalUtil;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.TimeUnit;

@Service
@RequiredArgsConstructor
@Slf4j
public class LoginServiceImpl extends ServiceImpl<LoginMapper, User> implements ILoginService {


    private final StringRedisTemplate stringRedisTemplate;

    @Override
    public Result loginInto(User u) {
        String username = u.getName();
        // 1. 定义缓存 User 信息的 Key (注意：这是缓存用户资料，不是 Token)
        String userCacheKey = "cache:user:" + username;

        User dbUser = null;

        // 2.【优化点】先从 Redis 查询用户信息
        String userJson = stringRedisTemplate.opsForValue().get(userCacheKey);

        if (StrUtil.isNotBlank(userJson)) {
            // Redis 命中：直接转为 User 对象，省去了一次数据库查询
            dbUser = JSONUtil.toBean(userJson, User.class);
        } else {
            // Redis 未命中：查询数据库
            dbUser = query().eq("name", username).one();

            // 查到数据后，写入 Redis 缓存（设置过期时间，例如 30 分钟）
            // 这样 30 分钟内再次登录就不需要查数据库了
            if (dbUser != null) {
                stringRedisTemplate.opsForValue().set(userCacheKey, JSONUtil.toJsonStr(dbUser), 30, TimeUnit.MINUTES);
            }
        }

        // 3.【安全校验】无论数据来自 Redis 还是 DB，都必须校验是否存在以及密码是否正确
        if (dbUser == null || !dbUser.getPassword().equals(u.getPassword())) {
            Result.error("用户不存在或密码错误");
        }

        // 4. 生成 Token
        Map<String, Object> claims = new HashMap<>();
        claims.put("id", dbUser.getId());
        claims.put("name", dbUser.getName());
        String token = JWT.generateToken(claims);

        // 5. 准备存入 Redis 的 Token 数据 (转为 UserDTO，去除密码等敏感信息)
        UserDTO userDTO = BeanUtil.copyProperties(dbUser, UserDTO.class);
        Map<String, Object> userMap = BeanUtil.beanToMap(userDTO, new HashMap<>(),
                new CopyOptions()
                        .setIgnoreNullValue(true)
                        .setFieldValueEditor((fieldName, fieldValue) -> fieldValue.toString()));

        // 保存 ThreadLocal
        ThreadLocalUtil.setCurrentUser(userDTO);

        // 6. 存入 Token 到 Redis
        // key 必须包含 token，确保唯一性
        String tokenKey = "user:token:" + token;
        stringRedisTemplate.opsForHash().putAll(tokenKey, userMap);
        stringRedisTemplate.expire(tokenKey, 120, TimeUnit.MINUTES); // Token 有效期通常长一点

        // 7. 返回结果
        return Result.success(new LoginInfo(dbUser.getName(), dbUser.getImage(), token));
    }

    @Override
    public Result logOut(String token) {
        // 1. 判空
        if (StrUtil.isBlank(token)) {
            return Result.error("退出错误，Token为空");
        }

        // 2. 去除可能存在的 "Bearer " 前缀（防止 Key 拼错）
        // 如果你的前端传过来的是 "Bearer eyJ...", 生成的 key 就会错，导致删不掉
        if (token.startsWith("Bearer ")) {
            token = token.substring(7);
        }

        // 3. 【核心修改】先删除 Token！不要依赖 ThreadLocal
        // 无论 ThreadLocal 里有没有人，Token 必须先死
        String tokenKey = "user:token:" + token;
        Boolean deleteResult = stringRedisTemplate.delete(tokenKey);
        if (!deleteResult) {
            log.info("未删除token，token是"+token);
            return Result.error("退出错误，Token不存在");
        }
        log.info("删除token成功，token是"+token);

        // 4. 再尝试清理用户缓存信息 (加判空，防止报错中断)
        UserDTO currentUser = ThreadLocalUtil.getCurrentUser();
        if (currentUser != null) {
            String name = currentUser.getName();
            String userCacheKey = "cache:user:" + name;
            stringRedisTemplate.delete(userCacheKey);
        }

        // 5. 清理本地线程变量
        ThreadLocalUtil.removeCurrentUser();

        return Result.success("退出成功");
    }

}