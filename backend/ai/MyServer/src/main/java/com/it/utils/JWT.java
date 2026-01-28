package com.it.utils;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.SignatureAlgorithm;

import java.nio.charset.StandardCharsets; // ❌ 必须导入这个
import java.util.Date;
import java.util.Map;

public class JWT {
    private static final String SECRET_KEY = "/jdhn:836**1";

    public static String generateToken(Map<String,Object> claims) {
        return Jwts.builder()
                // ✅ 重点修改：使用 .getBytes(StandardCharsets.UTF_8)
                // 强制 Java 使用和 Python 完全一样的字节序列
                .signWith(SignatureAlgorithm.HS256, SECRET_KEY.getBytes(StandardCharsets.UTF_8))
                .setExpiration(new Date(System.currentTimeMillis() + 1000 * 60 * 60 * 24 * 3))
                .addClaims(claims)
                .compact();
    }

    public static Claims parseToken(String token) {
        return Jwts.parser()
                // ✅ 重点修改：解析时也要用同样的字节数组
                .setSigningKey(SECRET_KEY.getBytes(StandardCharsets.UTF_8))
                .parseClaimsJws(token)
                .getBody();
    }

    public static Integer getUserIdFromToken(String token) {
        Claims claims = parseToken(token);
        return Integer.valueOf(claims.get("id").toString());
    }

}

//package com.it.utils;
//
//import io.jsonwebtoken.Claims;
//import io.jsonwebtoken.Jwts;
//import io.jsonwebtoken.SignatureAlgorithm;
//
//import java.util.Date;
//import java.util.Map;
//
//public class JWT {
//    private static final String SECRET_KEY = "/jdhn:836**1";
//
//    public static String generateToken(Map<String,Object> claims) {
//        return Jwts.builder()
//                .signWith(SignatureAlgorithm.HS256,SECRET_KEY)
//                // 设置过期时间为10小时
//                .setExpiration(new Date(System.currentTimeMillis() + 1000 * 60 * 60 * 24 * 3))
//                .addClaims(claims)
//                .compact();
//    }
//
//    public static Claims parseToken(String token) {
//        return Jwts.parser()
//                .setSigningKey(SECRET_KEY)
//                .parseClaimsJws(token)
//                .getBody();
//    }
//
//    public static Integer getUserIdFromToken(String token) {
//        Claims claims = parseToken(token);
//        return Integer.valueOf(claims.get("id").toString());
//    }
//
//}
