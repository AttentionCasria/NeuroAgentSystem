package com.it.pojo;

import java.time.LocalDateTime;

import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class Talk {
    private Integer id;
    private Integer userId;
    private String title;
    private String content;
    private String createTime;
    private String updateTime;
}
