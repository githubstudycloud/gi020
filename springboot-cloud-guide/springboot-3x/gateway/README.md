# Spring Boot 3.x — Spring Cloud Gateway 搭建指南

> Spring Boot 3.3.x + Spring Cloud Gateway 4.1.x + Reactor Netty
> Java 17+，支持 GraalVM Native Image、Virtual Threads

---

## 一、Maven 依赖

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
    <dependency>
        <groupId>org.springframework.cloud</groupId>
        <artifactId>spring-cloud-starter-gateway</artifactId>
    </dependency>
    <dependency>
        <groupId>com.alibaba.cloud</groupId>
        <artifactId>spring-cloud-starter-alibaba-nacos-discovery</artifactId>
    </dependency>
    <dependency>
        <groupId>org.springframework.cloud</groupId>
        <artifactId>spring-cloud-starter-loadbalancer</artifactId>
    </dependency>
    <!-- Resilience4j 熔断（Reactor 版）-->
    <dependency>
        <groupId>org.springframework.cloud</groupId>
        <artifactId>spring-cloud-starter-circuitbreaker-reactor-resilience4j</artifactId>
    </dependency>
    <!-- Redis 限流 -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-data-redis-reactive</artifactId>
    </dependency>
    <!-- 观测性（Micrometer Tracing，替代 Sleuth）-->
    <dependency>
        <groupId>io.micrometer</groupId>
        <artifactId>micrometer-tracing-bridge-brave</artifactId>
    </dependency>
    <dependency>
        <groupId>io.zipkin.reporter2</groupId>
        <artifactId>zipkin-reporter-brave</artifactId>
    </dependency>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-actuator</artifactId>
    </dependency>
</dependencies>
```

---

## 二、启动类

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

## 三、application.yml

```yaml
server:
  port: 9000
  # Spring Boot 3.2+ 开启虚拟线程
  # （Gateway 基于 Reactor 不依赖线程池，此配置影响阻塞操作）

spring:
  application:
    name: api-gateway
  threads:
    virtual:
      enabled: true    # Java 21+ 虚拟线程（Spring Boot 3.2+）
  cloud:
    nacos:
      discovery:
        server-addr: 127.0.0.1:8848
        namespace: dev
        username: nacos
        password: nacos

    gateway:
      # 全局跨域（3.x 推荐方式）
      globalcors:
        add-to-simple-url-handler-mapping: true  # 解决 OPTIONS 预检请求问题
        cors-configurations:
          '[/**]':
            allowedOriginPatterns:
              - "https://*.yourdomain.com"
              - "http://localhost:[*]"
            allowedMethods:
              - GET
              - POST
              - PUT
              - DELETE
              - OPTIONS
              - PATCH
            allowedHeaders: "*"
            allowCredentials: true
            maxAge: 3600

      routes:
        # ===== 用户服务 =====
        - id: user-service
          uri: lb://user-service
          predicates:
            - Path=/api/user/**
          filters:
            - StripPrefix=2
            - name: CircuitBreaker
              args:
                name: user-service-cb
                fallbackUri: forward:/fallback/user
            - name: RequestRateLimiter
              args:
                redis-rate-limiter.replenishRate: 50
                redis-rate-limiter.burstCapacity: 100
                key-resolver: "#{@userKeyResolver}"
            # 请求/响应日志（3.x 内置）
            - name: LogRequest
              args:
                enabled: true

        # ===== 订单服务（带权重路由 — 金丝雀发布）=====
        - id: order-service-stable
          uri: lb://order-service
          predicates:
            - Path=/api/order/**
            - Weight=order-group, 90
          filters:
            - StripPrefix=2

        - id: order-service-canary
          uri: lb://order-service-v2
          predicates:
            - Path=/api/order/**
            - Weight=order-group, 10
          filters:
            - StripPrefix=2
            - AddRequestHeader=X-Canary, true

      # 默认过滤器
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
              basedOnPreviousValue: false

      # 3.x 新增：HTTP/2 支持
      httpclient:
        connect-timeout: 5000
        response-timeout: 10s
        pool:
          type: elastic
          max-idle-time: 15s

  data:
    redis:
      host: localhost
      port: 6379

# Resilience4j
resilience4j:
  circuitbreaker:
    configs:
      default:
        slidingWindowType: COUNT_BASED
        slidingWindowSize: 10
        failureRateThreshold: 50
        slowCallRateThreshold: 80
        slowCallDurationThreshold: 2s
        waitDurationInOpenState: 10s
        permittedNumberOfCallsInHalfOpenState: 5
        automaticTransitionFromOpenToHalfOpenEnabled: true
    instances:
      user-service-cb:
        baseConfig: default
      order-service-cb:
        baseConfig: default

# Micrometer Tracing（替代 Spring Cloud Sleuth）
management:
  tracing:
    sampling:
      probability: 0.1    # 10% 采样率
  zipkin:
    tracing:
      endpoint: http://zipkin:9411/api/v2/spans
  endpoints:
    web:
      exposure:
        include: health,info,metrics,gateway,prometheus
  metrics:
    export:
      prometheus:
        enabled: true
```

---

## 四、全局过滤器（Jakarta EE 版本）

### 4.1 JWT 认证过滤器

```java
@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
public class JwtAuthGlobalFilter implements GlobalFilter {

    private static final Set<String> WHITE_LIST = Set.of(
        "/api/user/login",
        "/api/user/register",
        "/actuator/health"
    );

    private final JwtUtil jwtUtil;

    public JwtAuthGlobalFilter(JwtUtil jwtUtil) {
        this.jwtUtil = jwtUtil;
    }

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        String path = exchange.getRequest().getPath().value();

        if (WHITE_LIST.stream().anyMatch(path::startsWith)) {
            return chain.filter(exchange);
        }

        return Mono.justOrEmpty(
                exchange.getRequest().getHeaders().getFirst(HttpHeaders.AUTHORIZATION)
            )
            .filter(token -> token.startsWith("Bearer "))
            .map(token -> token.substring(7))
            .flatMap(jwtUtil::validateAndGetClaims)
            .flatMap(claims -> {
                ServerHttpRequest mutatedReq = exchange.getRequest().mutate()
                    .header("X-User-Id", claims.getSubject())
                    .header("X-User-Role", claims.get("role", String.class))
                    .build();
                return chain.filter(exchange.mutate().request(mutatedReq).build());
            })
            .switchIfEmpty(writeUnauthorized(exchange));
    }

    private Mono<Void> writeUnauthorized(ServerWebExchange exchange) {
        ServerHttpResponse response = exchange.getResponse();
        response.setStatusCode(HttpStatus.UNAUTHORIZED);
        response.getHeaders().setContentType(MediaType.APPLICATION_JSON);
        byte[] bytes = "{\"code\":401,\"message\":\"Unauthorized\"}".getBytes(StandardCharsets.UTF_8);
        return response.writeWith(Mono.just(response.bufferFactory().wrap(bytes)));
    }
}
```

### 4.2 分布式链路追踪过滤器（Micrometer Tracing）

```java
@Component
@Order(1)
public class TracingGlobalFilter implements GlobalFilter {

    private final Tracer tracer;

    public TracingGlobalFilter(Tracer tracer) {
        this.tracer = tracer;
    }

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        Span span = tracer.currentSpan();
        String traceId = span != null ? span.context().traceId() : "no-trace";

        return chain.filter(
            exchange.mutate()
                .request(r -> r.header("X-Trace-Id", traceId))
                .response(r -> {
                    r.getHeaders().add("X-Trace-Id", traceId);
                })
                .build()
        );
    }
}
```

---

## 五、自定义 GatewayFilter（路由级别）

```java
// 请求签名验证 Filter
@Component
public class SignatureGatewayFilterFactory
        extends AbstractGatewayFilterFactory<SignatureGatewayFilterFactory.Config> {

    public SignatureGatewayFilterFactory() {
        super(Config.class);
    }

    @Override
    public GatewayFilter apply(Config config) {
        return (exchange, chain) -> {
            ServerHttpRequest request = exchange.getRequest();
            String appId = request.getHeaders().getFirst("X-App-Id");
            String signature = request.getHeaders().getFirst("X-Signature");
            String timestamp = request.getHeaders().getFirst("X-Timestamp");

            if (!verifySignature(appId, signature, timestamp, config.getSecretKey())) {
                ServerHttpResponse response = exchange.getResponse();
                response.setStatusCode(HttpStatus.FORBIDDEN);
                return response.setComplete();
            }
            return chain.filter(exchange);
        };
    }

    private boolean verifySignature(String appId, String sign, String ts, String secret) {
        // HMAC-SHA256 验签逻辑...
        return true;
    }

    public static class Config {
        private String secretKey;
        // getter/setter
    }
}
```

使用：
```yaml
filters:
  - name: Signature
    args:
      secretKey: my-app-secret
```

---

## 六、降级端点

```java
@RestController
@RequestMapping("/fallback")
public class FallbackController {

    @GetMapping("/user")
    public Mono<Map<String, Object>> userFallback(ServerWebExchange exchange) {
        // 获取熔断原因
        Throwable cause = exchange.getAttribute(
            ServerWebExchangeUtils.CIRCUITBREAKER_EXECUTION_EXCEPTION_ATTR);
        String message = cause != null ? cause.getMessage() : "服务暂不可用";

        return Mono.just(Map.of(
            "code", 503,
            "message", message,
            "timestamp", Instant.now().toEpochMilli(),
            "path", exchange.getRequest().getPath().value()
        ));
    }
}
```

---

## 七、GraalVM Native Image 支持

```java
// src/main/java/com/example/gateway/GatewayNativeHints.java
@ImportRuntimeHints(GatewayNativeHints.GatewayHints.class)
@Configuration(proxyBeanMethods = false)
public class GatewayNativeHints {

    static class GatewayHints implements RuntimeHintsRegistrar {
        @Override
        public void registerHints(RuntimeHints hints, ClassLoader classLoader) {
            // 注册 Gateway 相关反射信息
            hints.reflection()
                .registerType(RouteDefinition.class, MemberCategory.values())
                .registerType(FilterDefinition.class, MemberCategory.values());
        }
    }
}
```

```bash
# 构建 Native Image（需要 GraalVM 或 Buildpacks）
./mvnw -Pnative spring-boot:build-image -DskipTests
docker run -p 9000:9000 api-gateway:latest
```

---

## 八、Spring Boot 3.x vs 2.x Gateway 主要变化

| 特性 | 2.x | 3.x |
|------|-----|-----|
| Java 最低版本 | 8 | **17** |
| Jakarta EE | javax.* | **jakarta.*** |
| 链路追踪 | Spring Cloud Sleuth | **Micrometer Tracing** |
| 指标暴露 | Spring Boot Actuator | **Micrometer + Prometheus** |
| Native Image | 不支持 | **GraalVM Native** |
| 虚拟线程 | 无 | **Java 21 Virtual Threads** |
| HTTP 客户端 | Netty | **Netty（HTTP/2 增强）** |
