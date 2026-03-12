# Spring Boot 1.x — Spring Cloud Config 配置中心搭建指南

> Spring Boot 1.5.x + Spring Cloud Config Server + Git 存储后端

---

## 一、Config Server（配置服务端）

### 1.1 Maven 依赖

```xml
<parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>1.5.22.RELEASE</version>
</parent>

<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>org.springframework.cloud</groupId>
            <artifactId>spring-cloud-dependencies</artifactId>
            <version>Edgware.SR6</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>
    </dependencies>
</dependencyManagement>

<dependencies>
    <dependency>
        <groupId>org.springframework.cloud</groupId>
        <artifactId>spring-cloud-config-server</artifactId>
    </dependency>
    <!-- 注册到 Eureka（可选）-->
    <dependency>
        <groupId>org.springframework.cloud</groupId>
        <artifactId>spring-cloud-starter-eureka</artifactId>
    </dependency>
</dependencies>
```

### 1.2 启动类

```java
@SpringBootApplication
@EnableConfigServer
@EnableEurekaClient  // 可选，注册到 Eureka
public class ConfigServerApplication {
    public static void main(String[] args) {
        SpringApplication.run(ConfigServerApplication.class, args);
    }
}
```

### 1.3 application.yml（Git 后端）

```yaml
server:
  port: 8888

spring:
  application:
    name: config-server
  cloud:
    config:
      server:
        git:
          # Git 仓库地址（支持 GitHub/GitLab/本地）
          uri: https://github.com/your-org/config-repo
          # 搜索路径（仓库内子目录）
          search-paths: '{application}'
          # 分支（默认 master）
          default-label: master
          # 私有仓库认证
          username: your-username
          password: your-token
          # 本地克隆路径（缓存）
          basedir: /tmp/config-repo-cache
          # 强制拉取（避免本地缓存脏数据）
          force-pull: true
          # 克隆超时（毫秒）
          timeout: 10

eureka:
  client:
    service-url:
      defaultZone: http://localhost:8761/eureka/
```

### 1.4 application.yml（本地文件系统后端，开发用）

```yaml
spring:
  profiles:
    active: native  # 激活 native profile
  cloud:
    config:
      server:
        native:
          # 本地配置文件目录
          search-locations: classpath:/config-repo,file:///D:/config-repo
```

### 1.5 Git 仓库配置文件命名规则

```
config-repo/
├── application.yml              # 所有应用共享
├── application-dev.yml          # 所有应用 dev 环境
├── order-service.yml            # order-service 所有环境
├── order-service-dev.yml        # order-service dev 环境
├── order-service-prod.yml       # order-service prod 环境
└── user-service/
    ├── user-service.yml
    └── user-service-dev.yml
```

### 1.6 Config Server API

```bash
# 查询配置
# /{application}/{profile}[/{label}]
GET http://localhost:8888/order-service/dev/master

# 查看原始文件
GET http://localhost:8888/order-service-dev.yml

# 查看所有配置（JSON格式）
GET http://localhost:8888/order-service/dev
```

响应示例：
```json
{
  "name": "order-service",
  "profiles": ["dev"],
  "label": "master",
  "version": "abc123def",
  "propertySources": [
    {
      "name": "https://github.com/.../order-service-dev.yml",
      "source": {
        "server.port": "8080",
        "datasource.url": "jdbc:mysql://dev-db:3306/orders"
      }
    }
  ]
}
```

---

## 二、Config Client（配置客户端）

### 2.1 Maven 依赖

```xml
<dependencies>
    <dependency>
        <groupId>org.springframework.cloud</groupId>
        <artifactId>spring-cloud-starter-config</artifactId>
    </dependency>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-actuator</artifactId>
    </dependency>
</dependencies>
```

### 2.2 bootstrap.yml（必须用 bootstrap，不能用 application）

> **重要**：Config Client 的配置服务器连接信息必须放在 `bootstrap.yml`，
> 因为 bootstrap 上下文比 application 上下文先加载。

```yaml
# bootstrap.yml
spring:
  application:
    name: order-service        # 对应 Git 仓库中的文件名前缀
  profiles:
    active: dev                # 环境标识
  cloud:
    config:
      uri: http://localhost:8888           # Config Server 地址
      label: master                        # Git 分支
      fail-fast: true                      # 连不上则快速失败
      retry:
        initial-interval: 1000
        max-attempts: 6
        max-interval: 2000
      # 通过 Eureka 发现 Config Server（可选）
      discovery:
        enabled: true
        service-id: config-server
```

### 2.3 使用配置

```java
// 方式1：@Value 注入
@RestController
@RefreshScope  // 支持配置热更新
public class OrderController {

    @Value("${order.timeout:5000}")
    private int timeout;

    @Value("${datasource.url}")
    private String datasourceUrl;

    @GetMapping("/config")
    public Map<String, Object> getConfig() {
        Map<String, Object> map = new HashMap<>();
        map.put("timeout", timeout);
        map.put("datasourceUrl", datasourceUrl);
        return map;
    }
}

// 方式2：@ConfigurationProperties 类型安全绑定
@Component
@ConfigurationProperties(prefix = "order")
@RefreshScope
public class OrderProperties {
    private int timeout = 5000;
    private String currency = "CNY";
    // getter/setter...
}
```

### 2.4 配置热更新（手动触发）

```bash
# 触发单个服务刷新（POST 请求）
curl -X POST http://localhost:8080/refresh

# Spring Boot 1.x 默认 actuator 不加前缀
# 响应：["order.timeout","datasource.url"]
```

> 注意：`@RefreshScope` 只能刷新 Bean 级别的配置，DataSource 等需要额外处理。

### 2.5 Spring Cloud Bus 实现自动广播刷新（可选）

```xml
<!-- 引入 Spring Cloud Bus（基于 RabbitMQ 或 Kafka）-->
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-bus-amqp</artifactId>
</dependency>
```

```yaml
# 所有服务加上 RabbitMQ 配置
spring:
  rabbitmq:
    host: localhost
    port: 5672
    username: guest
    password: guest
```

```bash
# 触发一次，所有订阅 bus 的服务都会刷新
curl -X POST http://localhost:8888/bus/refresh

# 只刷新指定服务
curl -X POST http://localhost:8888/bus/refresh?destination=order-service:**
```

---

## 三、配置加密

### 3.1 对称加密

```yaml
# Config Server bootstrap.yml
encrypt:
  key: my-secret-key-32chars-minimum!!   # 对称密钥
```

```bash
# 加密
curl http://localhost:8888/encrypt -d "my-db-password"
# 输出: a3f4b2c1...（密文）

# 解密
curl http://localhost:8888/decrypt -d "a3f4b2c1..."
```

```yaml
# Git 仓库配置文件中使用加密值
spring:
  datasource:
    password: '{cipher}a3f4b2c1...'  # {cipher} 前缀标识加密值
```

### 3.2 非对称加密（RSA）

```bash
# 生成 keystore
keytool -genkeypair -alias config-server -keyalg RSA \
  -dname "CN=Config Server,OU=IT,O=Org,L=BJ,S=BJ,C=CN" \
  -keystore config-server.jks -keypass 123456 -storepass 123456
```

```yaml
encrypt:
  key-store:
    location: classpath:config-server.jks
    password: 123456
    alias: config-server
    secret: 123456
```

---

## 四、完整项目结构

```
config-server/
├── src/main/java/
│   └── ConfigServerApplication.java
├── src/main/resources/
│   ├── application.yml
│   └── bootstrap.yml（如注册到Eureka）
└── pom.xml

order-service/
├── src/main/java/
│   └── OrderServiceApplication.java
├── src/main/resources/
│   └── bootstrap.yml      ← 核心：连接Config Server
└── pom.xml

# Git 配置仓库（独立仓库）
config-repo/
├── application.yml
├── order-service.yml
├── order-service-dev.yml
└── order-service-prod.yml
```
