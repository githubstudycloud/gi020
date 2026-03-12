# Spring Boot 3.x — Nacos 2.3.x 注册中心搭建指南

> Spring Boot 3.3.x + Spring Cloud 2023.0.x + Spring Cloud Alibaba 2023.0.3 + Nacos 2.3.x
> 要求 **Java 17+**，全面迁移 Jakarta EE 命名空间

---

## 一、Nacos Server 2.3.x 安装

```bash
# 下载 Nacos 2.3.x（支持 Spring Boot 3.x 客户端）
wget https://github.com/alibaba/nacos/releases/download/2.3.2/nacos-server-2.3.2.tar.gz
tar -xzf nacos-server-2.3.2.tar.gz
cd nacos/bin

# 单机启动
sh startup.sh -m standalone

# Docker 启动
docker run -d \
  --name nacos \
  -e MODE=standalone \
  -e NACOS_AUTH_ENABLE=true \
  -e NACOS_AUTH_TOKEN=SecretKey012345678901234567890123456789012345678901234567890123456789 \
  -e NACOS_AUTH_IDENTITY_KEY=serverIdentity \
  -e NACOS_AUTH_IDENTITY_VALUE=security \
  -p 8848:8848 \
  -p 9848:9848 \
  nacos/nacos-server:v2.3.2
```

> **安全提示**：Nacos 2.2.0+ 默认开启鉴权，必须配置 `NACOS_AUTH_TOKEN`（Base64编码，长度>=32字节）

---

## 二、Maven 依赖（Java 17 + Jakarta EE）

```xml
<parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>3.3.5</version>
</parent>

<properties>
    <java.version>17</java.version>
</properties>

<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>org.springframework.cloud</groupId>
            <artifactId>spring-cloud-dependencies</artifactId>
            <version>2023.0.3</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>
        <dependency>
            <groupId>com.alibaba.cloud</groupId>
            <artifactId>spring-cloud-alibaba-dependencies</artifactId>
            <version>2023.0.3.2</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>
    </dependencies>
</dependencyManagement>

<dependencies>
    <!-- Nacos 服务发现（已适配 Jakarta EE）-->
    <dependency>
        <groupId>com.alibaba.cloud</groupId>
        <artifactId>spring-cloud-starter-alibaba-nacos-discovery</artifactId>
    </dependency>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>
    <!-- OpenFeign（3.x，Jakarta 命名空间）-->
    <dependency>
        <groupId>org.springframework.cloud</groupId>
        <artifactId>spring-cloud-starter-openfeign</artifactId>
    </dependency>
    <dependency>
        <groupId>org.springframework.cloud</groupId>
        <artifactId>spring-cloud-starter-loadbalancer</artifactId>
    </dependency>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-actuator</artifactId>
    </dependency>
</dependencies>
```

---

## 三、启动类

```java
// Spring Boot 3.x：javax.* → jakarta.*（所有注解包名变化）
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;
import org.springframework.cloud.openfeign.EnableFeignClients;

@SpringBootApplication
@EnableDiscoveryClient
@EnableFeignClients
public class OrderServiceApplication {
    public static void main(String[] args) {
        SpringApplication.run(OrderServiceApplication.class, args);
    }
}
```

---

## 四、application.yml

```yaml
server:
  port: 8080

spring:
  application:
    name: order-service
  cloud:
    nacos:
      discovery:
        server-addr: 127.0.0.1:8848
        namespace: dev
        group: ORDER_GROUP
        # Nacos 2.2+ 鉴权配置
        username: nacos
        password: nacos
        # gRPC 端口（Nacos 2.x 特性，比 HTTP 更高效）
        # 自动计算：server-addr port + 1000 = 9848
        cluster-name: SH

# 暴露所有 Actuator 端点（3.x 默认更安全）
management:
  endpoints:
    web:
      exposure:
        include: health,info,metrics,nacos-discovery
  endpoint:
    health:
      show-details: always
```

---

## 五、OpenFeign 3.x 变化与用法

### 5.1 Feign 接口定义

```java
@FeignClient(
    name = "user-service",
    fallbackFactory = UserClientFallbackFactory.class
)
public interface UserClient {

    @GetMapping("/users/{id}")
    UserDTO getById(@PathVariable Long id);

    // 3.x 支持接口默认方法
    default List<UserDTO> getByIds(List<Long> ids) {
        return ids.stream()
            .map(this::getById)
            .filter(Objects::nonNull)
            .collect(Collectors.toList());
    }
}

// FallbackFactory 可获取异常原因
@Component
public class UserClientFallbackFactory implements FallbackFactory<UserClient> {

    private static final Logger log = LoggerFactory.getLogger(UserClientFallbackFactory.class);

    @Override
    public UserClient create(Throwable cause) {
        log.error("UserClient fallback, cause: {}", cause.getMessage());
        return id -> new UserDTO(id, "降级用户", null);
    }
}
```

### 5.2 Feign 配置（3.x 新增 Bean Override 检测）

```java
@Configuration(proxyBeanMethods = false)   // 3.x 推荐
public class FeignConfig {

    // 超时配置
    @Bean
    public Request.Options options() {
        return new Request.Options(
            5, TimeUnit.SECONDS,    // connectTimeout
            10, TimeUnit.SECONDS,   // readTimeout
            true                    // followRedirects
        );
    }

    // 重试策略
    @Bean
    public Retryer retryer() {
        return new Retryer.Default(100, 1000, 3);
    }

    // 日志级别
    @Bean
    public feign.Logger.Level feignLogLevel() {
        return feign.Logger.Level.BASIC;
    }
}
```

---

## 六、GraalVM Native Image 支持（3.x 特性）

```xml
<!-- 原生镜像编译插件 -->
<plugin>
    <groupId>org.graalvm.buildtools</groupId>
    <artifactId>native-maven-plugin</artifactId>
    <configuration>
        <imageName>${project.artifactId}</imageName>
        <buildArgs>
            <buildArg>--no-fallback</buildArg>
        </buildArgs>
    </configuration>
</plugin>
```

```bash
# 编译原生镜像（需要 GraalVM 22.3+）
./mvnw -Pnative native:compile

# 运行
./target/order-service
```

> **Nacos 原生支持**：Spring Cloud Alibaba 2023.0.1+ 已提供 GraalVM 适配，
> 需在 `src/main/resources/META-INF/native-image/` 添加反射配置。

---

## 七、Virtual Threads 集成（Java 21 + Spring Boot 3.2+）

```yaml
# application.yml（Spring Boot 3.2+ 一键开启虚拟线程）
spring:
  threads:
    virtual:
      enabled: true
```

```java
// Feign 使用虚拟线程（自动，无需额外配置）
// Tomcat 处理请求使用虚拟线程（自动）
// 旧的 @Async 也自动使用虚拟线程
```

---

## 八、Jakarta 命名空间迁移对照

| javax.* (Spring Boot 2.x) | jakarta.* (Spring Boot 3.x) |
|---------------------------|------------------------------|
| javax.servlet.http.HttpServletRequest | jakarta.servlet.http.HttpServletRequest |
| javax.annotation.Resource | jakarta.annotation.Resource |
| javax.validation.constraints.* | jakarta.validation.constraints.* |
| javax.persistence.* | jakarta.persistence.* |

---

## 九、服务实例元数据与灰度路由

```yaml
spring:
  cloud:
    nacos:
      discovery:
        metadata:
          version: v2
          env: prod
          region: cn-east
```

```java
// 自定义灰度路由（根据 Header 选择版本）
@Configuration
public class GrayLoadBalancerConfig {

    @Bean
    @Primary
    public ReactorServiceInstanceLoadBalancer grayLoadBalancer(
            Environment environment,
            LoadBalancerClientFactory factory) {
        String serviceId = environment.getProperty(
            LoadBalancerClientFactory.PROPERTY_NAME);
        return new GrayRoundRobinLoadBalancer(
            factory.getLazyProvider(serviceId, ServiceInstanceListSupplier.class),
            serviceId
        );
    }
}

public class GrayRoundRobinLoadBalancer implements ReactorServiceInstanceLoadBalancer {
    // 根据请求 Header X-Version 选择对应版本实例
    // ...
}
```

---

## 十、常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| 启动报 ClassNotFoundException: javax.servlet | 使用了 javax 包 | 依赖改为 jakarta 版本 |
| Nacos 注册失败 403 | 开启鉴权但未配置 | 配置 username/password |
| Native Image 启动失败 | 反射配置缺失 | 添加 Nacos 相关的 reflect-config.json |
| Feign 调用报 405 | GET 请求带 body | 改用 @RequestParam 或 POST |
