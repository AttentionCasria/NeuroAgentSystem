package com.it.service.impl;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.it.mapper.RegiMapper;
import com.it.pojo.LoginRegisterInfo;
import com.it.pojo.Result;
import com.it.po.uo.User;
import com.it.po.dto.UserDTO;
import com.it.service.IRegiService;
import com.it.utils.JWT;
import com.it.utils.ThreadLocalUtil;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.HashMap;
import java.util.Map;

@Slf4j
@Service
@Transactional
@RequiredArgsConstructor
public class RegiServiceImpl extends ServiceImpl<RegiMapper, User> implements IRegiService {

    @Override
    public Result insertUser(User user) {
        if(user==null){
            return Result.error("用户不存在");
        }
        boolean isSuccess = save(user);
        if (!isSuccess) {
            return Result.error("注册失败");
        }

        ThreadLocalUtil.setCurrentUser(new UserDTO(user.getId(), user.getName(), user.getImage()));
        log.info("注册用户:{}",user);
        // 注册逻辑保持不变
        Map<String, Object> map = new HashMap<>();
        map.put("id", user.getId());
        map.put("name", user.getName());
        return Result.success(new LoginRegisterInfo(user.getName(), JWT.generateToken(map)));
    }
}
