# Spring Boot 1.x — Zuul 网关搭建指南

> Spring Boot 1.5.x + Spring Cloud Netflix Zuul 1.x（基于 Servlet，同步阻塞）

---

## 一、Zuul 基础搭建

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
    <!-- Zuul 网关 -->
    <dependency>
        <groupId>org.springframework.cloud</groupId>
        <artifactId>spring-cloud-starter-zuul</artifactId>
    </dependency>
    <!-- 注册中心（通过 Eureka 发现服务）-->
    <dependency>
        <groupId>org.springframework.cloud</groupId>
        <artifactId>spring-cloud-starter-eureka</artifactId>
    </dependency>
    <!-- Hystrix 熔断（Zuul 内置，但需显式引入配置）-->
    <dependency>
        <groupId>org.springframework.cloud</groupId>
        <artifactId>spring-cloud-starter-hystrix</artifactId>
    </dependency>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-actuator</artifactId>
    </dependency>
</dependencies>
```

### 1.2 启动类

```java
@SpringBootApplication
@EnableZuulProxy     // 开启 Zuul 代理（含 Ribbon、Hystrix）
@EnableEurekaClient
public class GatewayApplication {
    public static void main(String[] args) {
        SpringApplication.run(GatewayApplication.class, args);
    }
}
```

---

## 二、路由配置

### 2.1 application.yml（基于 Eureka 服务名路由）

```yaml
server:
  port: 9000

spring:
  application:
    name: api-gateway

eureka:
  client:
    service-url:
      defaultZone: http://localhost:8761/eureka/

zuul:
  # 路由规则
  routes:
    # 用户服务：/api/user/** -> user-service/**
    user-service:
      path: /api/user/**
      serviceId: user-service         # Eureka 服务名
      strip-prefix: true              # 去掉 /api/user 前缀（默认true）

    # 订单服务：/api/order/** -> order-service/**
    order-service:
      path: /api/order/**
      serviceId: order-service

    # 直接 URL 路由（不经过 Eureka）
    static-service:
      path: /static/**
      url: http://192.168.1.100:8090

  # 全局前缀
  prefix: /v1
  # 是否去掉全局前缀
  strip-prefix: true

  # 敏感请求头（不转发到后端）
  sensitive-headers: Cookie,Set-Cookie,Authorization

  # 超时配置
  host:
    connect-timeout-millis: 5000
    socket-timeout-millis: 10000

# Ribbon 超时（通过 Eureka 路由时使用）
ribbon:
  ConnectTimeout: 5000
  ReadTimeout: 10000
  MaxAutoRetries: 1
  MaxAutoRetriesNextServer: 2

# Hystrix 超时（必须 > Ribbon 超时）
hystrix:
  command:
    default:
      execution:
        isolation:
          thread:
            timeoutInMilliseconds: 20000
```

### 2.2 简化路由（自动映射 Eureka 服务）

```yaml
zuul:
  # 忽略指定服务（不自动代理）
  ignored-services: config-server, eureka-server
  # 忽略所有自动路由，只用手动配置
  # ignored-services: '*'
```

自动映射规则：`http://gateway:9000/order-service/api/orders` → `order-service`

---

## 三、过滤器（Filter）

Zuul 过滤器分 4 种类型：`pre`、`route`、`post`、`error`

### 3.1 认证过滤器（pre filter）

```java
@Component
public class AuthFilter extends ZuulFilter {

    @Override
    public String filterType() {
        return FilterConstants.PRE_TYPE;  // "pre"
    }

    @Override
    public int filterOrder() {
        return 1;  // 执行顺序，数字越小越先执行
    }

    @Override
    public boolean shouldFilter() {
        RequestContext ctx = RequestContext.getCurrentContext();
        String uri = ctx.getRequest().getRequestURI();
        // 登录接口不校验
        return !uri.startsWith("/api/user/login");
    }

    @Override
    public Object run() {
        RequestContext ctx = RequestContext.getCurrentContext();
        HttpServletRequest request = ctx.getRequest();

        String token = request.getHeader("Authorization");
        if (token == null || !token.startsWith("Bearer ")) {
            // 拦截请求，返回 401
            ctx.setSendZuulResponse(false);
            ctx.setResponseStatusCode(HttpStatus.UNAUTHORIZED.value());
            ctx.setResponseBody("{\"code\":401,\"message\":\"Unauthorized\"}");
            ctx.getResponse().setContentType("application/json;charset=UTF-8");
            return null;
        }

        // 解析 JWT，将用户信息放入请求头传递给下游
        String userId = parseToken(token);
        ctx.addZuulRequestHeader("X-User-Id", userId);
        return null;
    }

    private String parseToken(String token) {
        // JWT 解析逻辑...
        return "user-123";
    }
}
```

### 3.2 日志过滤器（pre + post）

```java
@Component
public class LogFilter extends ZuulFilter {

    private static final Logger log = LoggerFactory.getLogger(LogFilter.class);

    @Override
    public String filterType() { return FilterConstants.PRE_TYPE; }

    @Override
    public int filterOrder() { return 0; }

    @Override
    public boolean shouldFilter() { return true; }

    @Override
    public Object run() {
        RequestContext ctx = RequestContext.getCurrentContext();
        HttpServletRequest request = ctx.getRequest();

        String traceId = UUID.randomUUID().toString().replace("-", "");
        ctx.addZuulRequestHeader("X-Trace-Id", traceId);

        log.info("[GATEWAY] {} {} traceId={}", request.getMethod(),
                 request.getRequestURI(), traceId);
        ctx.set("startTime", System.currentTimeMillis());
        return null;
    }
}

@Component
public class ResponseLogFilter extends ZuulFilter {

    private static final Logger log = LoggerFactory.getLogger(ResponseLogFilter.class);

    @Override
    public String filterType() { return FilterConstants.POST_TYPE; }

    @Override
    public int filterOrder() { return FilterConstants.SEND_RESPONSE_FILTER_ORDER - 1; }

    @Override
    public boolean shouldFilter() { return true; }

    @Override
    public Object run() {
        RequestContext ctx = RequestContext.getCurrentContext();
        Long startTime = (Long) ctx.get("startTime");
        if (startTime != null) {
            long elapsed = System.currentTimeMillis() - startTime;
            log.info("[GATEWAY] Response status={} elapsed={}ms",
                     ctx.getResponseStatusCode(), elapsed);
        }
        return null;
    }
}
```

### 3.3 限流过滤器（pre filter）

```xml
<!-- 引入 Guava 限流 -->
<dependency>
    <groupId>com.google.guava</groupId>
    <artifactId>guava</artifactId>
    <version>27.1-jre</version>
</dependency>
```

```java
@Component
public class RateLimitFilter extends ZuulFilter {

    // 每秒允许100个请求
    private final RateLimiter rateLimiter = RateLimiter.create(100.0);

    @Override
    public String filterType() { return FilterConstants.PRE_TYPE; }

    @Override
    public int filterOrder() { return -1; }  // 最先执行

    @Override
    public boolean shouldFilter() { return true; }

    @Override
    public Object run() {
        RequestContext ctx = RequestContext.getCurrentContext();
        if (!rateLimiter.tryAcquire()) {
            ctx.setSendZuulResponse(false);
            ctx.setResponseStatusCode(429);
            ctx.setResponseBody("{\"code\":429,\"message\":\"Too Many Requests\"}");
            ctx.getResponse().setContentType("application/json;charset=UTF-8");
        }
        return null;
    }
}
```

---

## 四、熔断降级

### 4.1 Zuul Fallback

```java
@Component
public class OrderServiceFallback implements ZuulFallbackProvider {

    @Override
    public String getRoute() {
        return "order-service";  // 对应的服务名，* 表示全部
    }

    @Override
    public ClientHttpResponse fallbackResponse(String route, Throwable cause) {
        return new ClientHttpResponse() {
            @Override
            public HttpStatus getStatusCode() { return HttpStatus.OK; }

            @Override
            public int getRawStatusCode() { return 200; }

            @Override
            public String getStatusText() { return "OK"; }

            @Override
            public void close() {}

            @Override
            public InputStream getBody() {
                String body = "{\"code\":503,\"message\":\"服务暂不可用，请稍后重试\"}";
                return new ByteArrayInputStream(body.getBytes(StandardCharsets.UTF_8));
            }

            @Override
            public HttpHeaders getHeaders() {
                HttpHeaders headers = new HttpHeaders();
                headers.setContentType(MediaType.APPLICATION_JSON_UTF8);
                return headers;
            }
        };
    }
}
```

---

## 五、CORS 跨域配置

```java
@Configuration
public class CorsConfig {

    @Bean
    public CorsFilter corsFilter() {
        CorsConfiguration config = new CorsConfiguration();
        config.addAllowedOrigin("*");
        config.addAllowedMethod("*");
        config.addAllowedHeader("*");
        config.setAllowCredentials(true);
        config.setMaxAge(3600L);

        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", config);
        return new CorsFilter(source);
    }
}
```

---

## 六、过滤器执行顺序

```
请求进入
  └─► pre filters（认证、限流、日志）
        └─► route filters（路由转发到后端服务）
              └─► post filters（响应日志、Header修改）
  error filter（任意阶段异常）
```

## 七、常见问题

| 问题 | 解决方案 |
|------|---------|
| Zuul 超时 502 | 调大 `ribbon.ReadTimeout` 和 `hystrix.timeoutInMilliseconds` |
| 大文件上传超时 | 增大 `zuul.max.host.max-per-route-connections` 和 HTTP 超时 |
| 请求头丢失 | 检查 `zuul.sensitive-headers`，移除不需要过滤的头 |
| 服务无法发现 | 确认服务名大小写与 Eureka 注册名一致 |
