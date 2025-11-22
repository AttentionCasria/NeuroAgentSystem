package com.it.mapper;

import com.it.pojo.User;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface RegiMapper {
    void insertUser(User user);
}
