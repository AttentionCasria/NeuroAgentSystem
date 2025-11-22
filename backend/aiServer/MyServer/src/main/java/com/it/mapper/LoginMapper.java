package com.it.mapper;


import com.it.pojo.User;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface LoginMapper {
    User findUser(User user);

    User findUserByName(String name);
}
