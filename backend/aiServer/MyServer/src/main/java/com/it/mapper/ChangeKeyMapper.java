package com.it.mapper;

import com.it.pojo.User;
import com.it.pojo.UserDTO;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface ChangeKeyMapper {


    void updateById(User user);

    User selectById(Integer id);
}
