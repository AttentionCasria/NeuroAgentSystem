package com.it.service;

import com.it.pojo.LoginInfo;
import com.it.pojo.LoginRegisterInfo;
import com.it.pojo.User;

public interface LoginService {
    LoginInfo loginInto(User user);

    LoginRegisterInfo loginRegisterInto(User user);
}
