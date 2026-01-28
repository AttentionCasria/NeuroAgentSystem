package com.it.service.impl;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.it.pojo.ChangeKey;
import com.it.pojo.Result;
import com.it.mapper.ChangeKeyMapper;
import com.it.po.uo.User;
import com.it.service.IChangeKeyService;
import lombok.RequiredArgsConstructor;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.concurrent.TimeUnit;

@Service
@RequiredArgsConstructor
public class ChangeKeyServiceImpl extends ServiceImpl<ChangeKeyMapper, User> implements IChangeKeyService {

    private final StringRedisTemplate stringRedisTemplate;

    @Override
    public Result changeKeyById(Integer currentId, ChangeKey changeKey) {
        String password = stringRedisTemplate.opsForValue().get("user:password:" + currentId);
        if(password != null)
        {
            return Result.success("密码已修改,三十天内不能重复修改");
        }
        User user = query().eq("id", currentId).one();
        if(user.getPassword().equals(changeKey.getPrePassword()))
        {
            user.setPassword(changeKey.getNewPassword());
            user.setUpdateTime(LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")));
            updateById(user);
            stringRedisTemplate.opsForValue().set("user:password:" + currentId, changeKey.getNewPassword(), 30, TimeUnit.DAYS);
            return Result.success("密码修改成功");
        }
        else return Result.error("密码错误");
    }

    @Override
    public Result getUserInfo(Integer currentId) {
        User user = query().eq("id", currentId).one();
        return Result.success(user);
    }
}
