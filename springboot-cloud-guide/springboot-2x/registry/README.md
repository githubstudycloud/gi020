# Spring Boot 2.x — Nacos 注册中心搭建指南

> Spring Boot 2.7.x + Spring Cloud Alibaba 2021.0.5 + Nacos 1.4.x/2.0.x

---

## 一、Nacos Server 安装与启动

### 1.1 下载安装

```bash
# 方式1：下载二进制包（推荐）
wget https://github.com/alibaba/nacos/releases/download/2.0.4/nacos-server-2.0.4.tar.gz
tar -xzf nacos-server-2.0.4.tar.gz
cd nacos/bin

# 单机模式启动（开发）
sh startup.sh -m standalone   # Linux/Mac
startup.cmd -m standalone     # Windows

# 方式2：Docker 启动
docker run -d \
  --name nacos \
  -e MODE=standalone \
  -e PREFER_HOST_MODE=hostname \
  -p 8848:8848 \
  -p 9848:9848 \
  -p 9849:9849 \
  nacos/nacos-server:v2.0.4
```

### 1.2 数据库持久化（生产必须）

```sql
-- 导入 Nacos 建表 SQL（nacos/conf/nacos-mysql.sql）
CREATE DATABASE nacos_config DEFAULT CHARACTER SET utf8mb4;
USE nacos_config;
-- 执行 SQL 文件...
```

```properties
# nacos/conf/application.properties
spring.datasource.platform=mysql
db.num=1
db.url.0=jdbc:mysql://127.0.0.1:3306/nacos_config?characterEncoding=utf8&serverTimezone=UTC
db.user.0=root
db.password.0=123456
```

### 1.3 集群部署

```bash
# nacos/conf/cluster.conf
192.168.1.100:8848
192.168.1.101:8848
192.168.1.102:8848
```

访问控制台：`http://localhost:8848/nacos`（默认账号密码：nacos/nacos）

---

## 二、Spring Boot 2.x 服务接入 Nacos

### 2.1 Maven 依赖

```xml
<parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>2.7.18</version>
</parent>

<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>org.springframework.cloud</groupId>
            <artifactId>spring-cloud-dependencies</artifactId>
            <version>2021.0.9</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>
        <dependency>
            <groupId>com.alibaba.cloud</groupId>
            <artifactId>spring-cloud-alibaba-dependencies</artifactId>
            <version>2021.0.5.0</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>
    </dependencies>
</dependencyManagement>

<dependencies>
    <!-- Nacos 服务发现 -->
    <dependency>
        <groupId>com.alibaba.cloud</groupId>
        <artifactId>spring-cloud-starter-alibaba-nacos-discovery</artifactId>
    </dependency>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-actuator</artifactId>
    </dependency>
    <!-- OpenFeign 服务调用 -->
    <dependency>
        <groupId>org.springframework.cloud</groupId>
        <artifactId>spring-cloud-starter-openfeign</artifactId>
    </dependency>
    <!-- LoadBalancer（替代 Ribbon，2021.x 默认）-->
    <dependency>
        <groupId>org.springframework.cloud</groupId>
        <artifactId>spring-cloud-starter-loadbalancer</artifactId>
    </dependency>
</dependencies>
```

### 2.2 启动类

```java
@SpringBootApplication
@EnableDiscoveryClient   // 通用注解，Nacos/Eureka/Consul 都支持
@EnableFeignClients
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
    name: order-service
  cloud:
    nacos:
      discovery:
        # Nacos Server 地址
        server-addr: 127.0.0.1:8848
        # 命名空间（隔离不同环境），默认 public
        namespace: dev
        # 分组（业务分组），默认 DEFAULT_GROUP
        group: ORDER_GROUP
        # 集群名（同一集群优先调用）
        cluster-name: SH
        # 服务权重（0-100，影响负载均衡）
        weight: 100
        # 认证（Nacos 开启鉴权时填写）
        username: nacos
        password: nacos
        # 心跳间隔（毫秒，默认5000）
        heart-beat-interval: 5000
        # 心跳超时（毫秒，默认15000）
        heart-beat-timeout: 15000
        # IP 删除超时（毫秒，默认30000）
        ip-delete-timeout: 30000
        # 是否注册为持久化实例（默认false=临时实例）
        ephemeral: true

# 健康检查端点
management:
  endpoints:
    web:
      exposure:
        include: health,info,metrics
```

---

## 三、服务发现与调用

### 3.1 OpenFeign 调用

```java
// Feign 接口定义
@FeignClient(
    name = "user-service",
    fallback = UserClientFallback.class,
    configuration = FeignConfig.class
)
public interface UserClient {

    @GetMapping("/users/{id}")
    UserDTO getById(@PathVariable("id") Long id);

    @PostMapping("/users/batch")
    List<UserDTO> batchQuery(@RequestBody List<Long> ids);
}

// 降级处理
@Component
public class UserClientFallback implements UserClient {
    @Override
    public UserDTO getById(Long id) {
        return new UserDTO(id, "降级用户", "N/A");
    }

    @Override
    public List<UserDTO> batchQuery(List<Long> ids) {
        return Collections.emptyList();
    }
}

// Feign 配置
@Configuration
public class FeignConfig {
    // 超时配置
    @Bean
    public Request.Options options() {
        return new Request.Options(5, TimeUnit.SECONDS, 10, TimeUnit.SECONDS, true);
    }

    // 日志级别
    @Bean
    public feign.Logger.Level feignLogLevel() {
        return feign.Logger.Level.FULL;
    }
}
```

### 3.2 RestTemplate 调用（Spring Cloud LoadBalancer）

```java
@Configuration
public class LoadBalancerConfig {
    @Bean
    @LoadBalanced
    public RestTemplate restTemplate() {
        return new RestTemplate();
    }
}

@Service
public class UserService {
    @Autowired
    private RestTemplate restTemplate;

    public UserDTO getUser(Long id) {
        return restTemplate.getForObject(
            "http://user-service/users/" + id, UserDTO.class);
    }
}
```

### 3.3 使用 DiscoveryClient 手动获取实例

```java
@Autowired
private DiscoveryClient discoveryClient;

public void listInstances() {
    List<ServiceInstance> instances = discoveryClient.getInstances("user-service");
    instances.forEach(instance -> {
        System.out.printf("host=%s, port=%d, metadata=%s%n",
            instance.getHost(), instance.getPort(), instance.getMetadata());
    });
}
```

---

## 四、Nacos 命名空间与分组规划

```
Nacos 命名空间（Namespace）→ 环境隔离
├── public（默认，不建议生产使用）
├── dev（开发环境）
├── test（测试环境）
└── prod（生产环境）

分组（Group）→ 业务隔离
├── DEFAULT_GROUP
├── ORDER_GROUP
└── USER_GROUP

服务（Service）→ 微服务实例
├── order-service
│   ├── 集群: SH（上海）
│   │   ├── 192.168.1.1:8080
│   │   └── 192.168.1.2:8080
│   └── 集群: BJ（北京）
│       └── 192.168.2.1:8080
```

---

## 五、负载均衡策略（Spring Cloud LoadBalancer 自定义）

```java
// 自定义随机负载均衡策略
@Bean
ReactorLoadBalancer<ServiceInstance> randomLoadBalancer(
        Environment environment,
        LoadBalancerClientFactory loadBalancerClientFactory) {
    String name = environment.getProperty(LoadBalancerClientFactory.PROPERTY_NAME);
    return new RandomLoadBalancer(
        loadBalancerClientFactory.getLazyProvider(name, ServiceInstanceListSupplier.class),
        name);
}
```

---

## 六、健康检查

```yaml
# Nacos 使用 Spring Boot Actuator 健康端点
management:
  endpoint:
    health:
      show-details: always
  health:
    nacos-discovery:
      enabled: true
```

---

## 七、常见问题

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| 服务注册成功但无法调用 | 命名空间/分组不一致 | 确认 consumer 和 provider 在同一 namespace+group |
| Nacos 2.x 端口变化 | 2.x 新增 gRPC 端口 | 开放 8848、9848、9849 三个端口 |
| Spring Cloud 2021.x 去掉 Ribbon | 已被 LoadBalancer 替代 | 引入 `spring-cloud-starter-loadbalancer` |
| 服务消失后 Feign 缓存未更新 | LoadBalancer 缓存 | 配置 `spring.cloud.loadbalancer.cache.ttl` |
