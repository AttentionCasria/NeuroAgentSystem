package com.it.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.it.po.vo.InitialPageVO;
import com.it.pojo.Talk;

import java.util.List;

public interface IInitialPageService extends IService<Talk> {
    List<InitialPageVO> getPage(Integer currentId);

    void deleteTalk(Integer userId, Integer talkId);
}
