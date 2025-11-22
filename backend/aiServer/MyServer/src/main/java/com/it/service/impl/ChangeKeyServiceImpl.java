package com.it.service.impl;

import com.it.Utils.ThreadLocalUtil;
import com.it.mapper.ChangeKeyMapper;
import com.it.pojo.User;
import com.it.pojo.UserDTO;
import com.it.service.ChangeKeyService;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

@Service
public class ChangeKeyServiceImpl implements ChangeKeyService {
    @Autowired
    private ChangeKeyMapper changeKeyMapper;

    @Override
    public void changeKeyById(UserDTO userDTO) {
        Integer currentId = ThreadLocalUtil.getCurrentId();
        User user = changeKeyMapper.selectById(currentId);
        if(user.getPassword().equals(userDTO.getPrePassword()))
        {
            User u = new User();
            BeanUtils.copyProperties(userDTO,u);
            u.setId(currentId); // 明确设置用户ID
            u.setPassword(userDTO.getNewPassword());
            u.setUpdateTime(LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")));
            changeKeyMapper.updateById(u);
        }
        else throw new RuntimeException("密码错误");
    }

    @Override
    public String getUserInfo(Integer currentId) {
        User user = changeKeyMapper.selectById(currentId);
        return user.getName();
    }
}
