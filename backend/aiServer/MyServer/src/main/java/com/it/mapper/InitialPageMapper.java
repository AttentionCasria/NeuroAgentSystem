package com.it.mapper;

import com.it.pojo.InitialPageVO;
import org.apache.ibatis.annotations.Delete;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface InitialPageMapper {
    @Select("select id as talkId, title from talk where user_id=#{currentId} order by create_time desc")
    List<InitialPageVO> getTalkIdAndTitle(Integer currentId);


    void deleteTalk(Integer userId, Integer talkId);
}
