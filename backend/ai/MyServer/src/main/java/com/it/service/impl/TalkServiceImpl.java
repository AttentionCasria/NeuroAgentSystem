package com.it.service.impl;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.it.mapper.TalkMapper;
import com.it.pojo.Talk;
import com.it.service.ITalkService;
import org.springframework.stereotype.Service;

@Service
public class TalkServiceImpl extends ServiceImpl<TalkMapper, Talk> implements ITalkService {
}
