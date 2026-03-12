# Spring Boot 1.x — Eureka 注册中心搭建指南

> Spring Boot 1.5.x + Spring Cloud Dalston/Edgware + Netflix Eureka

---

## 一、Eureka Server（注册中心服务端）

### 1.1 Maven 依赖

```xml
<!-- pom.xml -->
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
        <artifactId>spring-cloud-starter-eureka-server</artifactId>
    </dependency>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>
</dependencies>
```

### 1.2 启动类

```java
// EurekaServerApplication.java
@SpringBootApplication
@EnableEurekaServer
public class EurekaServerApplication {
    public static void main(String[] args) {
        SpringApplication.run(EurekaServerApplication.class, args);
    }
}
```

### 1.3 application.yml（单机模式）

```yaml
server:
  port: 8761

spring:
  application:
    name: eureka-server

eureka:
  instance:
    hostname: localhost
  client:
    # 不向自己注册
    register-with-eureka: false
    # 不从自己拉取注册表
    fetch-registry: false
    service-url:
      defaultZone: http://${eureka.instance.hostname}:${server.port}/eureka/
  server:
    # 关闭自我保护（开发环境）
    enable-self-preservation: false
    # 清理间隔（毫秒）
    eviction-interval-timer-in-ms: 5000
```

### 1.4 application.yml（高可用集群 — 3节点）

```yaml
# 节点1: application-peer1.yml
spring:
  application:
    name: eureka-server
  profiles: peer1

server:
  port: 8761

eureka:
  instance:
    hostname: peer1
  client:
    service-url:
      defaultZone: http://peer2:8762/eureka/,http://peer3:8763/eureka/
```

```yaml
# 节点2: application-peer2.yml
spring:
  profiles: peer2
server:
  port: 8762
eureka:
  instance:
    hostname: peer2
  client:
    service-url:
      defaultZone: http://peer1:8761/eureka/,http://peer3:8763/eureka/
```

启动命令：
```bash
java -jar eureka-server.jar --spring.profiles.active=peer1
java -jar eureka-server.jar --spring.profiles.active=peer2
```

---

## 二、Eureka Client（服务提供者）

### 2.1 Maven 依赖

```xml
<dependencies>
    <dependency>
        <groupId>org.springframework.cloud</groupId>
        <artifactId>spring-cloud-starter-eureka</artifactId>
    </dependency>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>
    <!-- 健康检查 -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-actuator</artifactId>
    </dependency>
</dependencies>
```

### 2.2 启动类

```java
@SpringBootApplication
@EnableEurekaClient   // 或 @EnableDiscoveryClient（通用）
public class OrderServiceApplication {
    public static void main(String[] args) {
        SpringApplication.run(OrderServiceApplication.class, args);
    }
}
```

### 2.3 application.yml

```yaml
server:
  port: 8080

spring:
  application:
    name: order-service   # 服务名，会显示在 Eureka 控制台

eureka:
  client:
    service-url:
      defaultZone: http://localhost:8761/eureka/
    # 拉取注册表间隔（秒，默认30）
    registry-fetch-interval-seconds: 10
  instance:
    # 心跳间隔（秒，默认30）
    lease-renewal-interval-in-seconds: 10
    # 服务失效时间（秒，默认90）
    lease-expiration-duration-in-seconds: 30
    # 使用IP注册（容器环境必须）
    prefer-ip-address: true
    instance-id: ${spring.cloud.client.ipAddress}:${server.port}

# 暴露健康检查端点
management:
  security:
    enabled: false   # 1.x 关闭 actuator 安全
```

### 2.4 服务调用（Ribbon + RestTemplate）

```java
// 配置 RestTemplate 开启负载均衡
@Configuration
public class RibbonConfig {
    @Bean
    @LoadBalanced
    public RestTemplate restTemplate() {
        return new RestTemplate();
    }
}

// 调用服务（按服务名调用，Ribbon 自动负载均衡）
@Service
public class OrderService {
    @Autowired
    private RestTemplate restTemplate;

    public String getUserInfo(Long userId) {
        // user-service 是注册到 Eureka 的服务名
        return restTemplate.getForObject(
            "http://user-service/users/" + userId, String.class);
    }
}
```

### 2.5 服务调用（Feign 声明式）

```xml
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-feign</artifactId>
</dependency>
```

```java
// 启动类加 @EnableFeignClients
@SpringBootApplication
@EnableEurekaClient
@EnableFeignClients
public class OrderServiceApplication { ... }

// Feign 接口
@FeignClient(name = "user-service", fallback = UserClientFallback.class)
public interface UserClient {
    @GetMapping("/users/{id}")
    UserDTO getUser(@PathVariable("id") Long id);
}

// 降级处理
@Component
public class UserClientFallback implements UserClient {
    @Override
    public UserDTO getUser(Long id) {
        return UserDTO.builder().id(id).name("未知用户").build();
    }
}
```

---

## 三、控制台访问

启动 Eureka Server 后访问：`http://localhost:8761`

控制台展示：
- 已注册实例列表（Application / AMIs / Availability Zones / Status）
- 实例心跳状态
- 自我保护模式状态（红字警告）

---

## 四、常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| 服务注册后立即下线 | 心跳超时默认90s | 调小 `lease-expiration-duration-in-seconds` |
| 服务摘除后仍能访问 | Ribbon 缓存未更新 | 调小 `ribbon.ServerListRefreshInterval` |
| 自我保护模式触发 | 网络抖动导致心跳丢失 | 开发环境可关闭，生产谨慎 |
| 容器内注册IP错误 | 默认注册hostname | 设置 `prefer-ip-address: true` |
