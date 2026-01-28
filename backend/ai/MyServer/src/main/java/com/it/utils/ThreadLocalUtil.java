package com.it.utils;

import com.it.po.dto.UserDTO;

public class ThreadLocalUtil {
    public static ThreadLocal<UserDTO> threadLocal = new ThreadLocal<>();
    public static void setCurrentUser(UserDTO user){
        threadLocal.set(user);
    }
    public static UserDTO getCurrentUser(){
        return threadLocal.get();
    }

    public static void removeCurrentUser(){
        threadLocal.remove();
    }
}
