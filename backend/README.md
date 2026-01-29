这是一个为您生成的详细 `README.md` 文档。结合了您提供的 `RefreshTokenInterceptor` 代码、之前的报错日志以及整体项目结构进行编写。

它重点突出了 **Redis 分布式会话**、**ThreadLocal 上下文隔离** 以及 **流式响应** 等核心亮点。

```markdown
# MyServer - AI 智能对话与用户管理系统

## 📖 项目简介

MyServer 是一个基于 **Spring Boot 3** 开发的高性能后端服务系统。项目核心定位于提供安全可靠的用户鉴权体系以及流畅的 AI 对话体验。

系统采用了现代化的 **前后端分离** 架构，后端通过 RESTful API 提供服务。核心功能包括基于 Redis 的双重拦截器鉴权机制、Token 自动续期、用户信息上下文隔离、以及支持流式输出 (SSE) 的 AI 对话功能。实现数据的持久化存储（MySQL）与高速缓存（Redis）的双轨运行。

## 🛠️ 技术栈

### 核心框架
- **开发语言**: Java 17+
- **Web 框架**: Spring Boot 3.x (使用了 Jakarta EE 规范)
- **ORM 框架**: MyBatis-Plus (极大简化 SQL 编写，提供 CRUD 接口)

### 数据存储与缓存
- **关系型数据库**: MySQL 8.0
- **高速缓存/会话**: **Redis**
    - 使用 `StringRedisTemplate` 操作
    - 采用 Hash 结构存储用户信息 (`user:token:{token}`)
    - 负责 Token 的存储、校验与过期时间管理

### 工具与中间件
- **工具库**: Hutool (BeanUtil 对象拷贝, StrUtil 字符串处理)
- **简化代码**: Lombok (@Slf4j, @Data, @RequiredArgsConstructor)
- **鉴权工具**: JWT (JSON Web Token) 用于生成令牌
- **连接池**: HikariCP

## 🚀 核心架构与业务流程

### 1. 极速鉴权与自动续期流程 (核心亮点)
本项目采用 **拦截器 (Interceptor) + Redis + ThreadLocal** 的组合模式，实现无感续期与高效鉴权。

*   **登录阶段**:
    1. 用户提交账号密码，验证通过。
    2. 生成唯一 Token。
    3. 将用户信息 (`UserDTO`) 转换为 Hash 结构存入 Redis，Key 为 `user:token:{token}`，设置有效期（如 30 分钟）。
    4. 返回 Token 给前端。

*   **请求拦截阶段 (`RefreshTokenInterceptor`)**:
    1. **拦截所有请求**: 检查 Header 中的 `token`。
    2. **双重校验**: 先解析 JWT 格式是否合法，再查询 Redis 中是否存在该 Key。
    3. **Token 续期**: 若 Redis 中存在该用户 Token，说明用户活跃，立即重置 Redis Key 的过期时间（30分钟），实现**活跃用户永不掉线**。
    4. **上下文隔离**: 将 Redis 中的 Hash 数据转为 `UserDTO` 对象，存入 `ThreadLocalUtil`。
    5. **后续使用**: Controller 和 Service 层无需传递用户 ID 参数，直接通过 `ThreadLocalUtil.getCurrentUser()` 获取当前登录用户信息。
    6. **资源释放**: 请求结束 (`afterCompletion`) 自动清理 ThreadLocal，防止内存泄漏。

### 2. AI 对话业务
*   **流式响应**: 通过 `QuesController` 处理 AI 对话请求，支持流式回传（类似 ChatGPT 的打字机效果），提升用户等待体验。
*   **持久化**:
    *   用户的提问与 AI 回复由 `TalkMapper` 实时写入 MySQL 的 `talk` 表。
    *   利用 MyBatis-Plus 自动填充机制处理 `create_time` 和 `update_time`。

### 3. 首页初始化
*   **聚合接口**: `InitialPageController` 负责在用户进入应用时，一次性聚合用户信息、历史会话摘要等关键数据，减少前端 HTTP 请求数量。

## ✨ 项目亮点

1. **健壮的 Redis 会话管理**
   - 相比于无状态的纯 JWT，本项目结合 Redis 实现了**可控的会话管理**。管理员可以随时在 Redis 中删除 Key 来强制用户下线，同时利用 Redis 的 TTL 机制实现了自动的 Session 滚动续期。

2. **优雅的代码设计**
   - **ThreadLocal 全局获取用户**: 彻底解决了 Controller 到 Service 层层传递 `userId` 的痛点，代码更加清爽。
   - **构造器注入**: 全面采用 Spring 推荐的构造器注入（Lombok `@RequiredArgsConstructor`），保证了 Bean 的不可变性和初始化安全性。
   - **统一异常处理与日志**: 集成 Slf4j，对关键路径（如 Token 解析失败、数据库截断异常）进行了详细的日志记录。

3. **MyBatis-Plus 深度应用**
   - 使用 MP 的通用 Mapper 和 Service 接口，大幅减少 JDBC 样板代码。
   - 针对 MySQL 大数据量可能导致的 `Out of range` 问题，优化了主键策略。

## 📂 数据库设计概览

### MySQL 表结构
*   **`user`**: 用户基础信息表。
*   **`talk`**: 对话记录表。
    *   `id`: BIGINT (主键)
    *   `user_id`: BIGINT (关联用户)
    *   `title`: VARCHAR (对话标题)
    *   `content`: TEXT/LONGTEXT (对话内容)

### Redis Key 设计
| Key Pattern | 类型 | 说明 | TTL |
| :--- | :--- | :--- | :--- |
| `user:token:{token_string}` | Hash | 存储 UserDTO (id, username, nickName...) | 30 分钟 (滚动刷新) |

## 🔧 快速开始 (Getting Started)

### 环境要求
*   JDK 17 或更高版本
*   Maven 3.6+
*   MySQL 8.0+
*   Redis 6.0+

### 1. 数据库配置
修改 `src/main/resources/application.yml`:

```yaml
spring:
  datasource:
    url: jdbc:mysql://localhost:3306/your_database?serverTimezone=Asia/Shanghai&characterEncoding=utf-8
    username: root
    password: your_password
  data:
    redis:
      host: localhost
      port: 6379
      database: 0
```

### 2. 启动项目
```bash
# 编译打包
mvn clean package

# 运行
java -jar target/MyServer-0.0.1-SNAPSHOT.jar
```

### 3. 常见问题排查
*   **Startup Error (Bean Creation)**: 如果遇到 `Circular reference` 循环依赖错误，请检查是否在 Service 层通过构造器相互注入，建议使用 `@Lazy` 或重构代码解耦。
*   **Data Truncation**: 如果插入 `talk` 表报错 `Out of range`，请确认数据库 `id` 字段类型为 `BIGINT`，且 Java 实体类中使用 `Long` 类型。

---
*Created by DarksideCasria*
```