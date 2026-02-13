# 项目部署与运行说明

## 1. 项目简介
MyServer 是一个基于 Spring Boot + MyBatis-Plus + Redis 的后端服务，支持用户注册登录、对话管理、流式 AI 响应等功能。

### 技术栈
- **后端框架**: Spring Boot 3.4.9
- **数据库**: MySQL 8.0
- **持久层**: MyBatis-Plus 3.5.7
- **缓存**: Redis (支持单点登录、对话历史缓存)
- **工具**: Lombok, Hutool, JWT
- **第三方服务**: 阿里云 OSS, 外部 AI 模型接口

### 亮点
- **流式响应**: 通过 `SseEmitter` 或直接写流实现 AI 对话的打字机效果。
- **单点登录 (SSO)**: 利用 Redis 存储 Token 的 JTI，实现同账号互踢。
- **双重拦截器**: `RefreshTokenInterceptor` 处理自动登录和 Token 校验，`TokenInterceptor` 处理权限拦截。
- **MyBatis-Plus**: 简化 CRUD 操作。

---

## 2. 宝塔面板 (Baota) 部署指南

### 第一步：准备 Jar 包
你已经打包好了 `MyServer-0.0.1-SNAPSHOT.jar`。
默认位置在：`D:\ideaProject\AI\ai\MyServer\target\MyServer-0.0.1-SNAPSHOT.jar`

### 第二步：上传到服务器
将 Jar 包上传到服务器目录，例如：`/www/wwwroot/myserver/`

### 第三步：运行命令
由于你使用的是 127.0.0.1 本地 Redis 和 MySQL，请确保服务器上已安装并启动这些服务。

使用以下命令启动（后台运行）：

```bash
nohup /www/server/java/jdk-21.0.2/bin/java -jar -Xmx1024M -Xms256M /www/wwwroot/myserver/MyServer-0.0.1-SNAPSHOT.jar --spring.profiles.active=prod > /www/wwwroot/myserver/app.log 2>&1 &
```

- `Xmx1024M`: 最大堆内存 1GB
- `--spring.profiles.active=prod`: 指定使用生产环境配置 (`application-prod.yml`)
- `> ... 2>&1`: 将日志输出到 `app.log`

### 第四步：常见问��排查

#### 1. Redis 连接超时 (Connection timed out)
**现象**:  `io.netty.channel.ConnectTimeoutException: connection timed out after 10000 ms: /192.168.2.161:6379`
**原因**: 你的配置文件中配置了 Redis 地址，但实际运行时可能被某些环境覆盖，或者是你的本地开发环境残留配置。
**解决**:
- 检查 `application-prod.yml`，确保 `aiserver.redis.host` 为 `127.0.0.1`（如果是本机 Redis）。
- 如果你的 Redis 确实在远程 `192.168.2.161`，请确保服务器能 Ping 通该 IP，且防火墙放行 6379 端口。
- **注意**: 如果 Redis 没有密码，请在配置文件中删除 `password` 字段或保留为空。

#### 2. “一登进去就是在网站内的界面”
**原因**: 前端可能缓存了 Token，或者拦截器逻辑放行了。
- 你的 `WebConfig.java` 配置了拦截器，但如果 Token 无效，`RefreshTokenInterceptor` 可能会直接返回 `true` (看代码逻辑 `if (StrUtil.isBlank(token)) return true;`)，然后 `TokenInterceptor` 检查 `ThreadLocal` 为空返回 401。
- 如果前端收到 401，应该自动跳转登录页。如果直接显示内部界面，说明前端没有正确处理 401 状态码，或者前端本地存储了旧的有效 Token。
- **建议**: 清除浏览器 LocalStorage/SessionStorage 里的 Token 再��。

#### 3. 数据库插入 Out of Range / Data Truncation
**现象**: `Data truncation: Out of range value for column 'id' at row 1`
**原因**: 数据库表 `talk` 或 `user` 的 `id` 字段可能没有设置为 `AUTO_INCREMENT`，或者类型定义太小（如 `TINYINT`）。
**解决**:
请在 MySQL 中执行：
```sql
ALTER TABLE talk MODIFY COLUMN id INT AUTO_INCREMENT;
ALTER TABLE user MODIFY COLUMN id INT AUTO_INCREMENT;
```
并且代码中实体类需要加上 `@TableId(type = IdType.AUTO)` (已修复)。

#### 4. InitialPageVO 构造函数报错
**现象**: `Actual arguments 2 but expected none`
**解决**: 这是一个 Lombok 问题，反序列化时有时需要无参构造器，或者查询结果映射时需要带参构造器。已在 `InitialPageVO` 中添加 `@NoArgsConstructor` 和 `@AllArgsConstructor`。
