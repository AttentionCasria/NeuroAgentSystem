package com.it.service.impl;

import com.it.mapper.InitialPageMapper;
import com.it.pojo.InitialPageVO;
import com.it.service.InitialPageService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class InitialPageServiceImpl implements InitialPageService {
    @Autowired
    private InitialPageMapper initialPageMapper;
    @Override
    public List<InitialPageVO> getTalkIdAndTitle(Integer currentId) {
        return initialPageMapper.getTalkIdAndTitle(currentId);
    }

    @Override
    public void deleteTalk(Integer userId, Integer talkId) {
        initialPageMapper.deleteTalk(userId,talkId);
    }
}
