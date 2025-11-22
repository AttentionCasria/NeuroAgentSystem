package com.it.service;

import com.it.pojo.InitialPageVO;

import java.util.List;

public interface InitialPageService {
    List<InitialPageVO> getTalkIdAndTitle(Integer currentId);

    void deleteTalk(Integer userId, Integer talkId);
}
