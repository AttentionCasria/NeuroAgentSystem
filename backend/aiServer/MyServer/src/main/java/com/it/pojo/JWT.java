package com.it.pojo;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.SignatureAlgorithm;

import java.util.Date;
import java.util.Map;

public class JWT {
    private static final String SECRET_KEY = "/jdhn:836**1";
    private static final long EXPIRATION_TIME = 12*60*60*1000;


    public static String generateToken(Map<String,Object> claims) {
        return Jwts.builder()
                .signWith(SignatureAlgorithm.HS256,SECRET_KEY)
                .addClaims(claims)
                .setExpiration(new Date(System.currentTimeMillis() + EXPIRATION_TIME))
                .compact();
    }

    public static Claims parseToken(String token) {
        return Jwts.parser()
                .setSigningKey(SECRET_KEY)
                .parseClaimsJws(token)
                .getBody();
    }

    public static Integer getUserIdFromToken(String token) {
        Claims claims = parseToken(token);
        return Integer.valueOf(claims.get("id").toString());
    }

}
