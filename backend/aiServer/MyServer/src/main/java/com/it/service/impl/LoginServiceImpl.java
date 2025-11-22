package com.it.service.impl;

import com.it.Utils.ThreadLocalUtil;
import com.it.mapper.LoginMapper;
import com.it.pojo.JWT;
import com.it.pojo.LoginInfo;
import com.it.pojo.LoginRegisterInfo;
import com.it.pojo.User;
import com.it.service.LoginService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.HashMap;
import java.util.Map;

@Service
public class LoginServiceImpl implements LoginService {
    @Autowired
    private LoginMapper loginMapper;
    @Override
    public LoginInfo loginInto(User user) {
        User existUser = loginMapper.findUserByName(user.getName());
        if (existUser == null) {
            throw new RuntimeException("用户不存在");
        }
        if (!existUser.getPassword().equals(user.getPassword())) {
            throw new RuntimeException("密码错误");
        }

        ThreadLocalUtil.setCurrentId(existUser.getId());
        Map<String,Object> map = new HashMap<>();
        map.put("id",existUser.getId());
        map.put("name",existUser.getName());
        return new LoginInfo(existUser.getName(),existUser.getImage(),JWT.generateToken(map));
    }


    @Override
    public LoginRegisterInfo loginRegisterInto(User user) {
        //ThreadLocalUtil.setCurrentId(user.getId());
        Map<String,Object> map = new HashMap<>();
        map.put("id",user.getId());
        map.put("name",user.getName());
        return new LoginRegisterInfo(user.getName(),JWT.generateToken(map));
    }
}
