package com.it.utils;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.SignatureAlgorithm;
import java.nio.charset.StandardCharsets;
import java.util.Date;
import java.util.Map;

public class JWT {
    private static final String SECRET_KEY = "/jdhn:836**1";

    public static String generateToken(Map<String,Object> claims) {
        return Jwts.builder()
                .signWith(SignatureAlgorithm.HS256, SECRET_KEY.getBytes(StandardCharsets.UTF_8))
                .setExpiration(new Date(System.currentTimeMillis() + 1000 * 60 * 60 * 24 * 3))
                .addClaims(claims)  // ❌ 这里的 claims 必须包含 "jti"
                .compact();
    }

    public static Claims parseToken(String token) {
        return Jwts.parser()
                .setSigningKey(SECRET_KEY.getBytes(StandardCharsets.UTF_8))
                .parseClaimsJws(token)
                .getBody();
    }

    public static Integer getUserIdFromToken(String token) {
        return Integer.valueOf(parseToken(token).get("id").toString());
    }

    // --- 新增：从 Token 中获取 JTI ---
    public static String getJtiFromToken(String token) {
        return parseToken(token).get("jti").toString();
    }
}