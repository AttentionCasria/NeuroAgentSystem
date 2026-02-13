package com.it.pojo;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Data
@ConfigurationProperties(prefix = "aiserver.alioss")
@Component
public class AliOssProperties {
    public String endpoint ;
    public String bucketName ;
    public String region ;
    public String accessKeyId;
    public String accessKeySecret;
}
