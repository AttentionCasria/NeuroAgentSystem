package com.it.po.uo;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

@Data
@TableName("cont")
public class Cont {

    @TableId(type = IdType.AUTO)
    private Integer id;

    private Integer userId;

    private Integer talkId;

    private String content;

    private String createTime;
}
