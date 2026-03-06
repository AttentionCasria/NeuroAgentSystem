package com.it.po.uo;

import com.baomidou.mybatisplus.annotation.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@Builder
@AllArgsConstructor
@NoArgsConstructor
@TableName("cont")
public class Cont {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long userId;
    private Long talkId;

    private String content;
    private LocalDateTime createTime;
}