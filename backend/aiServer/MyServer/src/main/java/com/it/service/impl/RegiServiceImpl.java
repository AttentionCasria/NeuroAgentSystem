package com.it.service.impl;

import com.it.mapper.RegiMapper;
import com.it.pojo.User;
import com.it.service.RegiService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

@Slf4j
@Service
@Transactional
public class RegiServiceImpl implements RegiService {
    @Autowired
    RegiMapper regiMapper;
    @Transactional(rollbackFor = {Exception.class})
    @Override
    public void insertUser(User user) {
        String currentTime = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"));
        user.setCreateTime(currentTime);
        user.setUpdateTime(currentTime);
        regiMapper.insertUser(user);
    }
}
