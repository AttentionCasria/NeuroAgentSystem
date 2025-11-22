package com.it.service;

import com.it.pojo.UserDTO;

public interface ChangeKeyService {

    void changeKeyById(UserDTO userDTO);

    String getUserInfo(Integer currentId);
}
