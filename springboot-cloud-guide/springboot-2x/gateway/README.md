# Spring Boot 2.x — Spring Cloud Gateway 搭建指南

> Spring Boot 2.7.x + Spring Cloud Gateway 3.1.x（基于 Reactor/Netty，异步非阻塞）

---

## 一、Maven 依赖

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
    <!-- Spring Cloud Gateway（基于 WebFlux，不能引入 spring-boot-starter-web）-->
    <dependency>
        <groupId>org.springframework.cloud</groupId>
        <artifactId>spring-cloud-starter-gateway</artifactId>
    </dependency>
    <!-- Nacos 服务发现（支持 lb:// 协议路由）-->
    <dependency>
        <groupId>com.alibaba.cloud</groupId>
        <artifactId>spring-cloud-starter-alibaba-nacos-discovery</artifactId>
    </dependency>
    <!-- LoadBalancer -->
    <dependency>
        <groupId>org.springframework.cloud</groupId>
        <artifactId>spring-cloud-starter-loadbalancer</artifactId>
    </dependency>
    <!-- 限流（Redis 令牌桶）-->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-data-redis-reactive</artifactId>
    </dependency>
    <!-- 熔断（Resilience4j）-->
    <dependency>
        <groupId>org.springframework.cloud</groupId>
        <artifactId>spring-cloud-starter-circuitbreaker-reactor-resilience4j</artifactId>
    </dependency>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-actuator</artifactId>
    </dependency>
</dependencies>
```

> **重要**：Gateway 基于 WebFlux，不能与 `spring-boot-starter-web` 共存！

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

## 三、路由配置

### 3.1 YAML 配置（推荐）

```yaml
server:
  port: 9000

spring:
  application:
    name: api-gateway
  cloud:
    nacos:
      discovery:
        server-addr: 127.0.0.1:8848
        namespace: dev

    gateway:
      # 全局跨域
      globalcors:
        cors-configurations:
          '[/**]':
            allowedOriginPatterns: "*"
            allowedMethods: ["GET","POST","PUT","DELETE","OPTIONS"]
            allowedHeaders: "*"
            allowCredentials: true
            maxAge: 3600

      # 路由配置
      routes:
        # ===== 用户服务 =====
        - id: user-service-route
          uri: lb://user-service          # lb:// 表示负载均衡，user-service 为 Nacos 服务名
          predicates:
            - Path=/api/user/**           # 路径断言
            - Method=GET,POST             # 方法断言
            # - Header=X-Request-Id, \d+ # Header 断言
            # - After=2024-01-01T00:00:00+08:00[Asia/Shanghai] # 时间断言
          filters:
            - StripPrefix=2               # 去掉 /api/user 两级前缀
            - AddRequestHeader=X-Gateway-Source, api-gateway
            - AddResponseHeader=X-Response-Time, now
            - name: CircuitBreaker
              args:
                name: user-service-cb
                fallbackUri: forward:/fallback/user-service

        # ===== 订单服务 =====
        - id: order-service-route
          uri: lb://order-service
          predicates:
            - Path=/api/order/**
          filters:
            - StripPrefix=2
            - name: RequestRateLimiter   # Redis 令牌桶限流
              args:
                redis-rate-limiter.replenishRate: 100    # 每秒补充令牌数
                redis-rate-limiter.burstCapacity: 200    # 令牌桶容量
                redis-rate-limiter.requestedTokens: 1    # 每次请求消耗令牌数
                key-resolver: "#{@ipKeyResolver}"        # 限流 key（按IP）

        # ===== 静态 URL 路由 =====
        - id: static-route
          uri: http://192.168.1.100:8090
          predicates:
            - Path=/static/**

      # 默认过滤器（作用于所有路由）
      default-filters:
        - DedupeResponseHeader=Access-Control-Allow-Credentials Access-Control-Allow-Origin
        - name: Retry
          args:
            retries: 3
            statuses: BAD_GATEWAY, GATEWAY_TIMEOUT
            methods: GET
            backoff:
              firstBackoff: 100ms
              maxBackoff: 500ms
              factor: 2

# Resilience4j 熔断配置
resilience4j:
  circuitbreaker:
    configs:
      default:
        slidingWindowType: COUNT_BASED
        slidingWindowSize: 10
        failureRateThreshold: 50
        waitDurationInOpenState: 10s
        permittedNumberOfCallsInHalfOpenState: 5
    instances:
      user-service-cb:
        baseConfig: default
      order-service-cb:
        baseConfig: default

# Redis 配置（限流使用）
  data:
    redis:
      host: localhost
      port: 6379
```

### 3.2 Java 代码配置（动态路由）

```java
@Configuration
public class GatewayRouteConfig {

    @Bean
    public RouteLocator customRoutes(RouteLocatorBuilder builder) {
        return builder.routes()
            // 路由1：带权重的金丝雀发布
            .route("user-service-v1", r -> r
                .path("/api/user/**")
                .and().weight("user-group", 90)    // 90% 流量
                .filters(f -> f.stripPrefix(2))
                .uri("lb://user-service-v1"))

            .route("user-service-v2", r -> r
                .path("/api/user/**")
                .and().weight("user-group", 10)    // 10% 流量（金丝雀）
                .filters(f -> f.stripPrefix(2))
                .uri("lb://user-service-v2"))

            // 路由2：自定义条件
            .route("admin-route", r -> r
                .path("/admin/**")
                .and().header("X-Admin-Token")     // 必须有此 Header
                .filters(f -> f
                    .stripPrefix(1)
                    .addRequestHeader("X-From-Gateway", "true"))
                .uri("lb://admin-service"))
            .build();
    }
}
```

---

## 四、全局过滤器（GlobalFilter）

### 4.1 认证过滤器

```java
@Component
@Order(-1)   // 最高优先级
public class AuthGlobalFilter implements GlobalFilter {

    private static final List<String> WHITE_LIST = Arrays.asList(
        "/api/user/login", "/api/user/register", "/api/public"
    );

    @Autowired
    private JwtUtil jwtUtil;

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        ServerHttpRequest request = exchange.getRequest();
        String path = request.getPath().pathWithinApplication().value();

        // 白名单放行
        if (WHITE_LIST.stream().anyMatch(path::startsWith)) {
            return chain.filter(exchange);
        }

        // 获取 Token
        String token = request.getHeaders().getFirst("Authorization");
        if (token == null || !token.startsWith("Bearer ")) {
            return unauthorized(exchange);
        }

        try {
            String userId = jwtUtil.parseToken(token.substring(7));
            // 将用户信息通过 Header 传递给下游
            ServerHttpRequest mutatedRequest = request.mutate()
                .header("X-User-Id", userId)
                .header("X-User-Type", jwtUtil.getUserType(token))
                .build();
            return chain.filter(exchange.mutate().request(mutatedRequest).build());
        } catch (Exception e) {
            return unauthorized(exchange);
        }
    }

    private Mono<Void> unauthorized(ServerWebExchange exchange) {
        ServerHttpResponse response = exchange.getResponse();
        response.setStatusCode(HttpStatus.UNAUTHORIZED);
        response.getHeaders().setContentType(MediaType.APPLICATION_JSON);
        String body = "{\"code\":401,\"message\":\"Unauthorized\"}";
        DataBuffer buffer = response.bufferFactory()
            .wrap(body.getBytes(StandardCharsets.UTF_8));
        return response.writeWith(Mono.just(buffer));
    }
}
```

### 4.2 链路追踪过滤器

```java
@Component
@Order(0)
public class TraceGlobalFilter implements GlobalFilter {

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        String traceId = exchange.getRequest().getHeaders()
            .getFirst("X-Trace-Id");

        if (traceId == null) {
            traceId = UUID.randomUUID().toString().replace("-", "");
        }

        final String finalTraceId = traceId;
        ServerHttpRequest request = exchange.getRequest().mutate()
            .header("X-Trace-Id", finalTraceId)
            .build();

        return chain.filter(exchange.mutate().request(request).build())
            .then(Mono.fromRunnable(() -> {
                exchange.getResponse().getHeaders().add("X-Trace-Id", finalTraceId);
            }));
    }
}
```

### 4.3 访问日志过滤器

```java
@Component
@Order(1)
public class AccessLogGlobalFilter implements GlobalFilter {

    private static final Logger log = LoggerFactory.getLogger("ACCESS_LOG");

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        ServerHttpRequest request = exchange.getRequest();
        long start = System.currentTimeMillis();

        return chain.filter(exchange).then(Mono.fromRunnable(() -> {
            ServerHttpResponse response = exchange.getResponse();
            long elapsed = System.currentTimeMillis() - start;
            log.info("{} {} {} {}ms ip={}",
                request.getMethod(),
                request.getPath(),
                response.getStatusCode(),
                elapsed,
                request.getRemoteAddress()
            );
        }));
    }
}
```

---

## 五、限流配置（Redis 令牌桶）

```java
@Configuration
public class RateLimiterConfig {

    // 按 IP 限流
    @Bean
    public KeyResolver ipKeyResolver() {
        return exchange -> Mono.just(
            Objects.requireNonNull(exchange.getRequest().getRemoteAddress())
                .getAddress().getHostAddress()
        );
    }

    // 按用户 ID 限流
    @Bean
    public KeyResolver userKeyResolver() {
        return exchange -> Mono.justOrEmpty(
            exchange.getRequest().getHeaders().getFirst("X-User-Id")
        ).defaultIfEmpty("anonymous");
    }

    // 按 API 接口限流
    @Bean
    public KeyResolver apiKeyResolver() {
        return exchange -> Mono.just(
            exchange.getRequest().getPath().pathWithinApplication().value()
        );
    }
}
```

---

## 六、降级端点

```java
@RestController
public class FallbackController {

    @GetMapping("/fallback/user-service")
    public Mono<Map<String, Object>> userServiceFallback(ServerWebExchange exchange) {
        return Mono.just(Map.of(
            "code", 503,
            "message", "用户服务暂不可用，请稍后重试",
            "timestamp", System.currentTimeMillis()
        ));
    }

    @GetMapping("/fallback/order-service")
    public Mono<Map<String, Object>> orderServiceFallback() {
        return Mono.just(Map.of("code", 503, "message", "订单服务暂不可用"));
    }
}
```

---

## 七、动态路由（从数据库/Nacos 加载）

```java
@Service
public class DynamicRouteService implements ApplicationEventPublisherAware {

    @Autowired
    private RouteDefinitionWriter routeDefinitionWriter;

    private ApplicationEventPublisher publisher;

    @Override
    public void setApplicationEventPublisher(ApplicationEventPublisher publisher) {
        this.publisher = publisher;
    }

    // 添加路由
    public void add(RouteDefinition definition) {
        routeDefinitionWriter.save(Mono.just(definition)).subscribe();
        publisher.publishEvent(new RefreshRoutesEvent(this));
    }

    // 删除路由
    public void delete(String routeId) {
        routeDefinitionWriter.delete(Mono.just(routeId)).subscribe();
        publisher.publishEvent(new RefreshRoutesEvent(this));
    }
}
```

---

## 八、常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| 引入 web 依赖冲突 | Gateway 基于 WebFlux 不兼容 Servlet | 去掉 `spring-boot-starter-web` |
| CORS 配置无效 | 与自定义 Filter 冲突 | 统一在 Gateway 配置 CORS，后端服务不配 |
| 大文件上传超时 | Netty 缓冲限制 | 配置 `spring.codec.max-in-memory-size` |
| Redis 限流报错 | 未配置 Redis | 检查 Redis 连接，或换用其他 KeyResolver |
