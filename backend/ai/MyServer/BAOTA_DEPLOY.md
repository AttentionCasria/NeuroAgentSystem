# 宝塔面板部署指南

## 1. 环境准备
确保你的宝塔面板服务器已经安装了以下软件：
*   **JDK 21** (必须是21及以上版本)
*   **MySQL 8.0**
*   **Redis** (版本建议 6.0+)

## 2. 数据库与Jar包准备
1.  **上传Jar包**：
    将本地打包好的 `MyServer-0.0.1-SNAPSHOT.jar` 上传到服务器目录，例如：`/www/wwwroot/myserver/`。
    
2.  **创建数据库**：
    在宝塔数据库面板创建一个名为 `medai` 的数据库（字符集选 `utf8mb4`）。

## 3. 部署方式 (解决报错的关键)

**为什么会出现“Redis连接问题”和“未找到配置文件”的警告？**
这是因为项目使用了环境变量配置 (`${...}`)，宝塔在静态检查时无法获取这些运行时的值。**请忽略这些警告**，直接按照下面的方式启动即可。

### 方法一：使用宝塔“Java项目”管理器 (推荐)

1.  **添加项目**：
    *   **项目类型**：Spring Boot
    *   **Jar包路径**：选择你上传的 `/www/wwwroot/myserver/MyServer-0.0.1-SNAPSHOT.jar`
    *   **端口**：`8080`
    *   **JDK版本**：选择安装好的 JDK 21

2.  **设置环境变量 (非常重要)**
    在项目设置 -> **环境变量** (或者启动命令的自定义参数) 中，你需要填入 `application-prod.yml` 中定义的变量，否则会启动失败。
    
    如果你的 MySQL 和 Redis 都在**本机**且**无密码** (或者是默认密码)，你可以直接启动，因为代码里默认连 `127.0.0.1`。
    
    **如果有密码，请添加以下参数** (在“项目执行命令”或“参数”栏)：
    ```bash
    --spring.datasource.password=你的数据库密码
    --spring.redis.password=你的Redis密码
    --aiserver.alioss.access-key-id=你的阿里云AK
    --aiserver.alioss.access-key-secret=你的阿里云SK
    ```

### 方法二：命令行启动 (最稳妥)

直接在终端或宝塔的“终端”中运行以下命令。这解决了之前提到的“JVM参数顺序错误”问题。

```bash
# 进入目录
cd /www/wwwroot/myserver/

# 启动命令 (后台运行，并将日志输出到 server.log)
nohup /www/server/java/jdk-21.0.2/bin/java \
  -Xmx1024M -Xms256M \
  -jar MyServer-0.0.1-SNAPSHOT.jar \
  --spring.profiles.active=prod \
  --spring.datasource.password=你的数据库密码 \
    --aiserver.alioss.access-key-id=LTAI5tCsXMzZtiBxnUgqKPNA \
    --aiserver.alioss.access-key-secret=Bkp8ixYCRDicOWLeclRqdPvlNoxMiK \
  > server.log 2>&1 &
```

*(注意：请将命令中的 `/www/server/java/jdk-21.0.2/bin/java` 替换为你实际的 JDK 21 路径)*

## 4. 常见问题排查

1.  **Redis 连接超时 (Connection timeout)**
    *   **原因**：代码默认连接 `127.0.0.1:6379`。如果报错连接 `192.168.x.x`，说明加载了开发环境配置。
    *   **解决**：确保启动命令里加了 `--spring.profiles.active=prod`，或者确认服务器本地装了 Redis 并且启动了。

2.  **Data truncation: Out of range value for column 'id'**
    *   **原因**：数据库里的 `id` 字段类型太小（比如 `INT`），但生成的 ID 是 `Long` 类型的大整数（雪花算法）。
    *   **解决**：修改数据库表结构，将 `id` 字段改为 `BIGINT(20)`。

3.  **UnsatisfiedDependencyException / Circular reference**
    *   **原因**：Bean 循环依赖（A依赖B，B依赖A）。
    *   **解决**：这是代码逻辑问题。如果遇到启动失败，需要在代码中用 `@Lazy` 注解打破循环，或者在 `application.yml` 添加 `spring.main.allow-circular-references: true` (不推荐，但能应急)。
