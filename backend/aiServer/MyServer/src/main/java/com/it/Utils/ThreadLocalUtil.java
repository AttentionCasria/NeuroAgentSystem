package com.it.Utils;

public class ThreadLocalUtil {
    public static ThreadLocal<Integer> threadLocal = new ThreadLocal<>();
    public static void setCurrentId(Integer id){
        threadLocal.set(id);
    }
    public static Integer getCurrentId(){
        return threadLocal.get();
    }

    public static void removeCurrentId(){
        threadLocal.remove();
    }
}
