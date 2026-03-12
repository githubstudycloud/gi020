# Spring Boot 4.x — 注册中心搭建指南

> Spring Boot 4.0.x（预览）+ Spring Framework 7 + Java 21+
> 基于 **Spring Cloud 2025.0.x** + Kubernetes 原生 / Nacos 3.x

---

> **版本说明**：Spring Boot 4.0 于 2025 年底进入里程碑阶段（Milestone），
> 最终 GA 预计 2026 年。本文基于已知路线图和 Milestone 版本整理，
> 部分 API 可能随正式版有所调整。

---

## 一、Spring Boot 4.x 注册中心选型

### 1.1 三种主流方案对比

| 方案 | 适用场景 | 特点 |
|------|---------|------|
| **Nacos 3.x** | 传统微服务 / 混合云 | 功能完善，控制台友好，国内主流 |
| **Kubernetes Service + DNS** | 纯 Kubernetes 部署 | 无需额外组件，K8s 原生 |
| **Consul** | 多数据中心 / Service Mesh | 健康检查强，支持 Connect |

---

## 二、方案一：Nacos 3.x（推荐，传统微服务）

### 2.1 Maven 依赖

```xml
<parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>4.0.0-M3</version>
</parent>

<properties>
    <java.version>21</java.version>
</properties>

<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>org.springframework.cloud</groupId>
            <artifactId>spring-cloud-dependencies</artifactId>
            <version>2025.0.0</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>
        <!-- Spring Cloud Alibaba 4.x（适配 Spring Boot 4）-->
        <dependency>
            <groupId>com.alibaba.cloud</groupId>
            <artifactId>spring-cloud-alibaba-dependencies</artifactId>
            <version>2025.0.0.0</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>
    </dependencies>
</dependencyManagement>

<dependencies>
    <dependency>
        <groupId>com.alibaba.cloud</groupId>
        <artifactId>spring-cloud-starter-alibaba-nacos-discovery</artifactId>
    </dependency>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>
    <dependency>
        <groupId>org.springframework.cloud</groupId>
        <artifactId>spring-cloud-starter-openfeign</artifactId>
    </dependency>
    <dependency>
        <groupId>org.springframework.cloud</groupId>
        <artifactId>spring-cloud-starter-loadbalancer</artifactId>
    </dependency>
</dependencies>
```

### 2.2 application.yml

```yaml
spring:
  application:
    name: order-service
  threads:
    virtual:
      enabled: true    # Java 21 虚拟线程（4.x 默认推荐开启）
  cloud:
    nacos:
      discovery:
        server-addr: 127.0.0.1:8848
        namespace: prod
        username: nacos
        password: nacos
        # 4.x 新增：gRPC 长连接配置
        grpc-port: 9848

server:
  port: 8080
```

### 2.3 启动类（Java 21 特性）

```java
@SpringBootApplication
@EnableDiscoveryClient
@EnableFeignClients
public class OrderServiceApplication {

    public static void main(String[] args) {
        SpringApplication.run(OrderServiceApplication.class, args);
    }
}
```

```java
// Java 21：使用 Record 作为 DTO（不可变）
public record UserDTO(Long id, String name, String email) {}

// Java 21：使用 Pattern Matching
public String processUser(Object obj) {
    return switch (obj) {
        case UserDTO u when u.id() > 0 -> "Valid user: " + u.name();
        case null -> "No user";
        default -> "Unknown object";
    };
}
```

---

## 三、方案二：Kubernetes 原生服务发现

### 3.1 Spring Cloud Kubernetes 方式

```xml
<dependencies>
    <!-- Spring Cloud Kubernetes 服务发现（无需 Nacos/Eureka）-->
    <dependency>
        <groupId>org.springframework.cloud</groupId>
        <artifactId>spring-cloud-starter-kubernetes-fabric8-discovery</artifactId>
    </dependency>
    <dependency>
        <groupId>org.springframework.cloud</groupId>
        <artifactId>spring-cloud-starter-loadbalancer</artifactId>
    </dependency>
    <dependency>
        <groupId>org.springframework.cloud</groupId>
        <artifactId>spring-cloud-starter-openfeign</artifactId>
    </dependency>
</dependencies>
```

```yaml
spring:
  application:
    name: order-service
  cloud:
    kubernetes:
      discovery:
        enabled: true
        # 是否发现所有命名空间的服务
        all-namespaces: false
        namespaces:
          - production
          - staging
        # 只发现有 spring-boot 标签的 Service
        service-labels:
          app-type: spring-boot
      loadbalancer:
        mode: SERVICE    # 使用 K8s Service DNS 负载均衡
```

```yaml
# Kubernetes Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order-service
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: order-service
  template:
    metadata:
      labels:
        app: order-service
        app-type: spring-boot
        version: v1
    spec:
      serviceAccountName: spring-cloud-k8s   # 需要读取 Service 的权限
      containers:
        - name: order-service
          image: registry/order-service:4.0.0
          ports:
            - containerPort: 8080
          env:
            - name: SPRING_PROFILES_ACTIVE
              value: prod
          # 使用 Spring Boot Actuator 健康检查
          readinessProbe:
            httpGet:
              path: /actuator/health/readiness
              port: 8080
            initialDelaySeconds: 10
            periodSeconds: 5
          livenessProbe:
            httpGet:
              path: /actuator/health/liveness
              port: 8080
            initialDelaySeconds: 15
            periodSeconds: 10
          resources:
            requests:
              memory: "128Mi"
              cpu: "100m"
            limits:
              memory: "256Mi"
              cpu: "500m"
```

```yaml
# RBAC：给 Spring Cloud Kubernetes 读取 Service 的权限
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: spring-cloud-k8s-role
  namespace: production
rules:
  - apiGroups: [""]
    resources: ["services", "endpoints", "pods", "configmaps", "secrets"]
    verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: spring-cloud-k8s-binding
  namespace: production
subjects:
  - kind: ServiceAccount
    name: spring-cloud-k8s
roleRef:
  kind: Role
  name: spring-cloud-k8s-role
  apiGroup: rbac.authorization.k8s.io
```

### 3.2 服务调用（K8s 方式，服务名即 K8s Service 名）

```java
// Feign 接口（服务名 = K8s Service 名）
@FeignClient(name = "user-service")   // 对应 K8s Service: user-service
public interface UserClient {
    @GetMapping("/users/{id}")
    UserDTO getById(@PathVariable Long id);
}
```

---

## 四、Virtual Threads 与注册中心（Java 21 特性）

```java
// Spring Boot 4.x + Java 21：虚拟线程下的服务调用
@Service
public class OrderService {

    private final UserClient userClient;

    public OrderService(UserClient userClient) {
        this.userClient = userClient;
    }

    // 虚拟线程下，同步调用不会阻塞平台线程
    public OrderDTO createOrder(CreateOrderRequest request) {
        // 并发调用多个服务（使用 StructuredConcurrency — Java 21 预览特性）
        try (var scope = new StructuredTaskScope.ShutdownOnFailure()) {
            var userTask = scope.fork(() -> userClient.getById(request.getUserId()));
            var inventoryTask = scope.fork(() -> checkInventory(request.getProductId()));

            scope.join().throwIfFailed();

            UserDTO user = userTask.get();
            boolean inStock = inventoryTask.get();

            return buildOrder(user, request, inStock);
        } catch (Exception e) {
            throw new RuntimeException("创建订单失败", e);
        }
    }
}
```

---

## 五、GraalVM Native Image（4.x 成熟特性）

```bash
# Spring Boot 4.x：Native Image 构建更快，启动时间 < 100ms
./mvnw -Pnative spring-boot:build-image

# 预期性能对比（参考）
# JVM 模式：启动 2-5秒，内存 256MB
# Native 模式：启动 0.05-0.1秒，内存 50MB
```

---

## 六、Observability（4.x 全面集成 Micrometer）

```yaml
management:
  tracing:
    sampling:
      probability: 1.0    # 全量采样（开发环境）
  otlp:
    tracing:
      endpoint: http://otel-collector:4318/v1/traces  # OpenTelemetry
  metrics:
    export:
      otlp:
        url: http://otel-collector:4318/v1/metrics
```

```java
// 4.x：使用 @Observed 注解自动生成链路和指标
@Service
@Observed(name = "order.service")
public class OrderService {

    @Observed(name = "order.create", contextualName = "create-order")
    public OrderDTO createOrder(CreateOrderRequest request) {
        // 自动记录：追踪 span、指标（耗时、调用次数）
        return buildOrder(request);
    }
}
```

---

## 七、常见问题

| 问题 | 解决 |
|------|------|
| K8s 模式找不到服务 | 检查 RBAC 权限，ServiceAccount 需要 get/list/watch |
| 虚拟线程下 Feign 超时 | 调大 `feign.client.config.default.readTimeout` |
| Native Image 缺少反射 | 运行 `native:generateTestResourceConfig` 自动生成 |
| Nacos 3.x 兼容性 | 确认使用 Spring Cloud Alibaba 4.x 适配版本 |
