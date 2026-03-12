# Spring Boot 4.x — 网关搭建指南

> Spring Boot 4.0.x（预览）+ Spring Cloud Gateway 5.x + Java 21
> Virtual Threads + GraalVM Native + OpenTelemetry 全栈可观测

---

> **版本说明**：本文基于 Spring Boot 4.0 Milestone 和 Spring Cloud 2025.0.x 路线图整理。

---

## 一、选型：Spring Cloud Gateway vs Kubernetes Ingress/Gateway API

| 方案 | 适用场景 |
|------|---------|
| **Spring Cloud Gateway** | 业务网关（认证、限流、熔断、路由复杂逻辑）|
| **Kubernetes Ingress (Nginx)** | 流量入口（简单路由、TLS 终止）|
| **Kubernetes Gateway API** | K8s 标准网关（替代 Ingress，功能更强）|
| **组合方案** | K8s Ingress 入流量 → Spring Cloud Gateway 业务处理 |

---

## 二、Maven 依赖

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
    <!-- Spring Cloud Gateway（5.x，Reactor Netty 0.9+）-->
    <dependency>
        <groupId>org.springframework.cloud</groupId>
        <artifactId>spring-cloud-starter-gateway</artifactId>
    </dependency>
    <!-- 服务发现 -->
    <dependency>
        <groupId>com.alibaba.cloud</groupId>
        <artifactId>spring-cloud-starter-alibaba-nacos-discovery</artifactId>
    </dependency>
    <dependency>
        <groupId>org.springframework.cloud</groupId>
        <artifactId>spring-cloud-starter-loadbalancer</artifactId>
    </dependency>
    <!-- 熔断 -->
    <dependency>
        <groupId>org.springframework.cloud</groupId>
        <artifactId>spring-cloud-starter-circuitbreaker-reactor-resilience4j</artifactId>
    </dependency>
    <!-- 限流（Redis Reactive）-->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-data-redis-reactive</artifactId>
    </dependency>
    <!-- OpenTelemetry 全链路可观测 -->
    <dependency>
        <groupId>io.micrometer</groupId>
        <artifactId>micrometer-tracing-bridge-otel</artifactId>
    </dependency>
    <dependency>
        <groupId>io.opentelemetry</groupId>
        <artifactId>opentelemetry-exporter-otlp</artifactId>
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
@SpringBootApplication
@EnableDiscoveryClient
public class GatewayApplication {
    public static void main(String[] args) {
        SpringApplication.run(GatewayApplication.class, args);
    }
}
```

---

## 四、application.yml

```yaml
server:
  port: 9000
  # Netty 优化（Gateway 不使用 Spring MVC/Tomcat）
  netty:
    connection-timeout: 10s

spring:
  application:
    name: api-gateway
  threads:
    virtual:
      enabled: true   # Java 21 虚拟线程（影响阻塞操作的执行器）
  cloud:
    nacos:
      discovery:
        server-addr: ${NACOS_ADDR:nacos:8848}
        namespace: ${NACOS_NAMESPACE:prod-xxxx}
        username: ${NACOS_USERNAME:nacos}
        password: ${NACOS_PASSWORD:nacos}

    gateway:
      # 全局跨域
      globalcors:
        add-to-simple-url-handler-mapping: true
        cors-configurations:
          '[/**]':
            allowedOriginPatterns:
              - "https://*.yourdomain.com"
            allowedMethods: [GET, POST, PUT, DELETE, OPTIONS, PATCH]
            allowedHeaders: "*"
            allowCredentials: true
            maxAge: 86400

      routes:
        # ===== 用户服务 =====
        - id: user-service
          uri: lb://user-service
          predicates:
            - Path=/api/v{version:[12]}/user/**   # 版本路由：v1, v2
          filters:
            - StripPrefix=3   # 去掉 /api/v1/user
            - name: CircuitBreaker
              args:
                name: user-cb
                fallbackUri: forward:/fallback/user
            - name: RequestRateLimiter
              args:
                redis-rate-limiter.replenishRate: 100
                redis-rate-limiter.burstCapacity: 200
                key-resolver: "#{@compositeKeyResolver}"

        # ===== 订单服务（金丝雀 10% 流量）=====
        - id: order-service-canary
          uri: lb://order-service-v2
          predicates:
            - Path=/api/v{version}/order/**
            - Weight=order-group, 10
            - Header=X-Beta-User, true    # 只对 Beta 用户灰度
          filters:
            - StripPrefix=3
            - AddRequestHeader=X-Canary, true
            - AddRequestHeader=X-Gateway-Version, v2

        - id: order-service-stable
          uri: lb://order-service
          predicates:
            - Path=/api/v{version}/order/**
            - Weight=order-group, 90
          filters:
            - StripPrefix=3

      # 默认过滤器（全局）
      default-filters:
        - DedupeResponseHeader=Access-Control-Allow-Credentials Access-Control-Allow-Origin
        - name: Retry
          args:
            retries: 3
            statuses: BAD_GATEWAY,SERVICE_UNAVAILABLE,GATEWAY_TIMEOUT
            methods: GET,HEAD
            backoff:
              firstBackoff: 50ms
              maxBackoff: 500ms
              factor: 2

      # HTTP 客户端配置
      httpclient:
        connect-timeout: 5000
        response-timeout: 15s
        # HTTP/2 支持
        http2:
          enabled: true
        pool:
          type: elastic
          max-idle-time: 20s
          max-life-time: 60s

  data:
    redis:
      host: ${REDIS_HOST:redis}
      port: 6379
      password: ${REDIS_PASSWORD:}

# Resilience4j 熔断
resilience4j:
  circuitbreaker:
    configs:
      default:
        slidingWindowType: COUNT_BASED
        slidingWindowSize: 20
        failureRateThreshold: 50
        slowCallRateThreshold: 80
        slowCallDurationThreshold: 3s
        waitDurationInOpenState: 15s
        permittedNumberOfCallsInHalfOpenState: 5
        automaticTransitionFromOpenToHalfOpenEnabled: true
    instances:
      user-cb: { baseConfig: default }
      order-cb: { baseConfig: default }

# OpenTelemetry 可观测
management:
  tracing:
    sampling:
      probability: ${TRACING_SAMPLE_RATE:0.1}
  otlp:
    tracing:
      endpoint: ${OTEL_EXPORTER_OTLP_TRACES_ENDPOINT:http://otel-collector:4318/v1/traces}
    metrics:
      export:
        url: ${OTEL_EXPORTER_OTLP_METRICS_ENDPOINT:http://otel-collector:4318/v1/metrics}
  endpoints:
    web:
      exposure:
        include: health,info,metrics,prometheus,gateway,circuitbreakers
  metrics:
    export:
      prometheus:
        enabled: true
```

---

## 五、全局过滤器（Java 21 + Reactor 风格）

### 5.1 JWT 认证过滤器

```java
@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
public class JwtAuthGlobalFilter implements GlobalFilter {

    // Java 21 密封接口：认证结果类型安全
    sealed interface AuthResult permits AuthResult.Success, AuthResult.Failure {
        record Success(String userId, String role) implements AuthResult {}
        record Failure(HttpStatus status, String message) implements AuthResult {}
    }

    private static final Set<String> WHITE_LIST = Set.of(
        "/api/v1/user/login", "/api/v1/user/register",
        "/actuator/health", "/actuator/info"
    );

    private final JwtUtil jwtUtil;

    public JwtAuthGlobalFilter(JwtUtil jwtUtil) {
        this.jwtUtil = jwtUtil;
    }

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        String path = exchange.getRequest().getPath().value();

        // 版本无关白名单匹配（正则）
        boolean isWhitelisted = WHITE_LIST.stream()
            .anyMatch(p -> path.matches(p.replace("/v1/", "/v[0-9]+/")));

        if (isWhitelisted) return chain.filter(exchange);

        return authenticate(exchange)
            .flatMap(result -> switch (result) {
                case AuthResult.Success s -> {
                    var req = exchange.getRequest().mutate()
                        .header("X-User-Id", s.userId())
                        .header("X-User-Role", s.role())
                        .build();
                    yield chain.filter(exchange.mutate().request(req).build());
                }
                case AuthResult.Failure f -> writeError(exchange, f.status(), f.message());
            });
    }

    private Mono<AuthResult> authenticate(ServerWebExchange exchange) {
        return Mono.justOrEmpty(
                exchange.getRequest().getHeaders().getFirst(HttpHeaders.AUTHORIZATION)
            )
            .filter(h -> h.startsWith("Bearer "))
            .map(h -> h.substring(7))
            .flatMap(jwtUtil::validate)
            .map(claims -> (AuthResult) new AuthResult.Success(
                claims.getSubject(), claims.get("role", String.class)))
            .defaultIfEmpty(new AuthResult.Failure(HttpStatus.UNAUTHORIZED, "Missing or invalid token"))
            .onErrorReturn(new AuthResult.Failure(HttpStatus.UNAUTHORIZED, "Token validation failed"));
    }

    private Mono<Void> writeError(ServerWebExchange exchange, HttpStatus status, String message) {
        var response = exchange.getResponse();
        response.setStatusCode(status);
        response.getHeaders().setContentType(MediaType.APPLICATION_JSON);
        var body = """
            {"code":%d,"message":"%s","timestamp":%d}
            """.formatted(status.value(), message, System.currentTimeMillis());
        return response.writeWith(Mono.just(
            response.bufferFactory().wrap(body.getBytes(StandardCharsets.UTF_8))));
    }
}
```

### 5.2 可观测性过滤器（OpenTelemetry）

```java
@Component
@Order(1)
public class ObservabilityGlobalFilter implements GlobalFilter {

    private final ObservationRegistry observationRegistry;

    public ObservabilityGlobalFilter(ObservationRegistry observationRegistry) {
        this.observationRegistry = observationRegistry;
    }

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        ServerHttpRequest request = exchange.getRequest();
        String method = request.getMethod().name();
        String path = request.getPath().value();

        return Observation.createNotStarted("gateway.request", observationRegistry)
            .lowCardinalityKeyValue("http.method", method)
            .lowCardinalityKeyValue("http.route", normalizeRoute(path))
            .observe(() -> chain.filter(exchange).then(Mono.fromRunnable(() -> {
                int status = exchange.getResponse().getStatusCode() != null
                    ? exchange.getResponse().getStatusCode().value() : 0;
                // 状态码自动记录到指标
            })));
    }

    private String normalizeRoute(String path) {
        // /api/v1/user/123 → /api/v*/user/{id}
        return path.replaceAll("/v\\d+/", "/v*/")
                   .replaceAll("/\\d+", "/{id}");
    }
}
```

---

## 六、GraalVM Native Image

```java
// Gateway Native Image 配置
@ImportRuntimeHints(GatewayNativeHints.Hints.class)
@Configuration(proxyBeanMethods = false)
public class GatewayNativeHints {

    static class Hints implements RuntimeHintsRegistrar {
        @Override
        public void registerHints(RuntimeHints hints, ClassLoader classLoader) {
            // 路由 DSL 反射
            hints.reflection()
                .registerType(RouteDefinition.class, MemberCategory.values())
                .registerType(FilterDefinition.class, MemberCategory.values())
                .registerType(PredicateDefinition.class, MemberCategory.values());

            // JWT 库反射
            hints.reflection()
                .registerType(io.jsonwebtoken.impl.DefaultClaims.class,
                    MemberCategory.INVOKE_DECLARED_CONSTRUCTORS,
                    MemberCategory.INVOKE_DECLARED_METHODS);
        }
    }
}
```

```bash
# 构建 Native Image（Spring Boot 4.x，构建速度提升约 30%）
./mvnw -Pnative spring-boot:build-image

# 预期启动性能（Gateway 原生镜像）
# 启动时间：< 100ms
# 内存占用：< 80MB（vs JVM 模式 300MB+）
```

---

## 七、Kubernetes Ingress + Gateway 组合部署

```yaml
# k8s/gateway-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-gateway
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api-gateway
  template:
    spec:
      containers:
        - name: api-gateway
          image: registry/api-gateway:4.0.0
          ports:
            - containerPort: 9000
          env:
            - name: NACOS_ADDR
              value: nacos-headless:8848
            - name: REDIS_HOST
              value: redis-master
            - name: SPRING_PROFILES_ACTIVE
              value: prod
          readinessProbe:
            httpGet:
              path: /actuator/health/readiness
              port: 9000
            initialDelaySeconds: 5
            periodSeconds: 3
          livenessProbe:
            httpGet:
              path: /actuator/health/liveness
              port: 9000
          resources:
            requests:
              memory: "128Mi"    # Native Image 大幅降低内存需求
              cpu: "200m"
            limits:
              memory: "256Mi"
              cpu: "1000m"
---
apiVersion: v1
kind: Service
metadata:
  name: api-gateway
  namespace: production
spec:
  selector:
    app: api-gateway
  ports:
    - port: 9000
      targetPort: 9000
---
# K8s Ingress（nginx）作为外部流量入口
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: api-gateway-ingress
  namespace: production
  annotations:
    nginx.ingress.kubernetes.io/proxy-body-size: "50m"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "30"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - api.yourdomain.com
      secretName: api-tls-secret
  rules:
    - host: api.yourdomain.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: api-gateway
                port:
                  number: 9000
```

---

## 八、限流 KeyResolver（Java 21 复合策略）

```java
@Configuration(proxyBeanMethods = false)
public class RateLimiterConfig {

    // 复合限流 Key（用户ID + API路径）
    @Bean
    @Primary
    public KeyResolver compositeKeyResolver() {
        return exchange -> {
            String userId = exchange.getRequest().getHeaders()
                .getFirst("X-User-Id");
            String path = exchange.getRequest().getPath()
                .pathWithinApplication().value()
                .replaceAll("/\\d+", "/{id}");  // 归一化路径
            String key = userId != null
                ? "user:" + userId + ":" + path
                : "ip:" + Objects.requireNonNull(
                    exchange.getRequest().getRemoteAddress())
                    .getAddress().getHostAddress();
            return Mono.just(key);
        };
    }
}
```

---

## 九、Spring Boot 4.x Gateway 亮点总结

| 特性 | 说明 |
|------|------|
| Java 21 必须 | 虚拟线程、密封类、模式匹配全面可用 |
| Native Image 成熟 | 启动 <100ms，内存 <80MB |
| OpenTelemetry 原生 | 替代 Zipkin，统一 Trace/Metric/Log |
| HTTP/2 默认 | 更高效的后端服务通信 |
| `@Observed` 注解 | 方法级别自动生成追踪和指标 |
| K8s 部署标准化 | Liveness/Readiness/Startup 探针开箱即用 |
