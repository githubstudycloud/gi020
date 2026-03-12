# Spring Boot 2.x 详解 (2018–2023)

## 概述

Spring Boot 2.x 是大规模现代化改造阶段。最大变化：**Java 8 成为最低要求**，引入 Spring Framework 5 响应式编程模型，彻底重写 Actuator，引入 Micrometer 统一指标体系，并将 HikariCP 设为默认连接池。

> **生命周期**: 2018-03 ~ 2022-11（OSS 支持）
> **最终版本**: 2.7.18（OSS 于 2023-11 结束；商业支持延长至 2029-06）

## 各小版本时间线

| 版本 | 发布时间 | Spring Framework | 主要主题 |
|------|---------|-----------------|---------|
| 2.0 | 2018-03 | 5.0 | 响应式、Kotlin、Actuator 重构、Micrometer |
| 2.1 | 2018-10 | 5.1 | Java 11、懒加载、Gradle 5 |
| 2.2 | 2019-10 | 5.2 | `proxyBeanMethods`、JUnit 5 默认 |
| 2.3 | 2020-05 | 5.2 | Docker 镜像构建、分层 JAR、优雅关机、K8s 探针 |
| 2.4 | 2020-11 | 5.3 | 新配置处理、新版本号方案 |
| 2.5 | 2021-05 | 5.3 | Jetty 10（可选） |
| 2.6 | 2021-11 | 5.3 | 禁止循环引用、PathPatternParser 默认 |
| 2.7 | 2022-05 | 5.3 | **GraphQL**、`@AutoConfiguration`、新 imports 文件（最终版） |

## 核心组件版本对比

| 组件 | 2.0 | 2.7 |
|------|-----|-----|
| Spring Framework | 5.0 | 5.3 |
| Java 最低 | Java 8 | Java 8 |
| Java 最高测试 | Java 9 | Java 18 |
| 嵌入式 Tomcat | 8.5 | 9.0.x |
| 嵌入式 Jetty | 9.4 | 9.4.x（10.x 可选） |
| 嵌入式 Undertow | 1.4 | 2.0.x |
| Hibernate | 5.2 | 5.6.x |
| Jackson | 2.9 | 2.13.x |
| JUnit | 4.x（2.0-2.1）/ 5.x（2.2+） | 5.8.x |
| Micrometer | 1.0 | 1.9.x |
| Kotlin | 1.2 | 1.6.x |
| Spring Security | 5.0 | 5.7.x |
| Flyway | 5.0 | 8.5.x |
| Spring Data | Kay | 2021.2 |

## Spring Boot 2.0（2018-03）重大变化

### Java 8 最低要求

```java
// 2.0 起可以原生使用 Java 8 特性
@FunctionalInterface
interface OrderProcessor {
    void process(Order order);
}

// 函数式 Bean 注册（Spring 5 新特性）
SpringApplication.run(Application.class, args);
// 或函数式方式
new SpringApplicationBuilder()
    .sources(Application.class)
    .initializers((GenericApplicationContext ctx) -> {
        ctx.registerBean(MyService.class, MyService::new);
    })
    .run(args);
```

### Spring WebFlux（响应式 Web）

```java
// 注解方式（与 MVC 类似）
@RestController
public class UserController {
    @GetMapping("/users/{id}")
    public Mono<User> getUser(@PathVariable String id) {
        return userService.findById(id); // 返回 Mono/Flux
    }

    @GetMapping("/users")
    public Flux<User> getAllUsers() {
        return userService.findAll();
    }
}

// 函数式方式（RouterFunction）
@Bean
public RouterFunction<ServerResponse> routes(UserHandler handler) {
    return RouterFunctions.route()
        .GET("/users/{id}", handler::getUser)
        .GET("/users", handler::getAllUsers)
        .POST("/users", handler::createUser)
        .build();
}
```

添加 WebFlux starter（区别于 MVC）：
```xml
<!-- 响应式 Web（使用 Netty） -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-webflux</artifactId>
</dependency>
<!-- 不能同时有 spring-boot-starter-web，否则 MVC 优先 -->
```

### Micrometer 指标系统

```java
// 注入 MeterRegistry
@Service
public class OrderService {
    private final Counter orderCounter;
    private final Timer orderTimer;

    public OrderService(MeterRegistry registry) {
        this.orderCounter = Counter.builder("orders.created")
            .tag("status", "success")
            .register(registry);
        this.orderTimer = Timer.builder("orders.processing.time")
            .register(registry);
    }

    public Order createOrder(OrderRequest request) {
        return orderTimer.record(() -> {
            // 处理逻辑
            orderCounter.increment();
            return processOrder(request);
        });
    }
}
```

配置 Prometheus 暴露：
```yaml
management:
  endpoints:
    web:
      exposure:
        include: health, info, metrics, prometheus
  metrics:
    export:
      prometheus:
        enabled: true
```

### HikariCP 默认连接池

```yaml
# 2.0 起 HikariCP 是默认连接池
spring:
  datasource:
    hikari:
      maximum-pool-size: 10
      minimum-idle: 5
      connection-timeout: 30000
      idle-timeout: 600000
      max-lifetime: 1800000
```

### Actuator 重大改版

```yaml
# 2.x Actuator 配置
management:
  endpoints:
    web:
      base-path: /actuator   # 新的统一前缀
      exposure:
        include: health, info, metrics  # 默认只暴露 health
        exclude: env, beans  # 排除敏感端点
  endpoint:
    health:
      show-details: always  # 展示详细健康信息
```

端点路径对比：

| 1.x | 2.x | 说明 |
|-----|-----|------|
| `/health` | `/actuator/health` | 健康检查 |
| `/info` | `/actuator/info` | 应用信息 |
| `/metrics` | `/actuator/metrics` | 指标（维度化） |
| `/env` | `/actuator/env` | 环境变量 |
| `/beans` | `/actuator/beans` | Bean 列表 |
| `/trace` | `/actuator/httptrace` | HTTP 追踪 |
| `/dump` | `/actuator/threaddump` | 线程转储 |

自定义端点：
```java
@Component
@Endpoint(id = "custom")
public class CustomEndpoint {
    @ReadOperation
    public Map<String, Object> info() {
        return Map.of("version", "1.0", "status", "OK");
    }

    @WriteOperation
    public void update(@Selector String name, String value) {
        // 写操作
    }
}
// 访问：GET /actuator/custom
```

### Kotlin 一等公民

```kotlin
// runApplication 函数
fun main(args: Array<String>) {
    runApplication<Application>(*args)
}

// Kotlin DSL 配置
@Configuration
class AppConfig {
    @Bean
    fun dataSource() = DataSourceBuilder.create()
        .url("jdbc:h2:mem:testdb")
        .build()
}

// 扩展函数支持
val logger = logger<MyService>()

// Kotlin 协程（与 WebFlux 配合）
@GetMapping("/users/{id}")
suspend fun getUser(@PathVariable id: String): User =
    userService.findById(id)
```

## Spring Boot 2.2（2019-10）

### `proxyBeanMethods = false`

```java
// 2.2 引入 proxyBeanMethods 优化
@Configuration(proxyBeanMethods = false)  // 不通过 CGLIB 代理
public class AppConfig {
    @Bean
    public ServiceA serviceA() {
        return new ServiceA();
    }

    @Bean
    public ServiceB serviceB() {
        // proxyBeanMethods=true（默认）：serviceA() 返回同一个实例
        // proxyBeanMethods=false：serviceA() 每次创建新实例
        return new ServiceB(serviceA());
    }
}

// 对于无 Bean 间依赖的配置类，false 可提升启动性能
@SpringBootApplication(proxyBeanMethods = false)
public class Application { ... }
```

### JUnit 5 成为默认

```xml
<!-- 2.2 起，spring-boot-starter-test 默认包含 JUnit 5 -->
<!-- 同时提供 vintage engine 兼容 JUnit 4 -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-test</artifactId>
    <scope>test</scope>
    <!-- 不再需要显式排除 JUnit 4 -->
</dependency>
```

```java
// JUnit 5 写法
@SpringBootTest
class UserServiceTest {
    @Autowired
    private UserService userService;

    @Test
    void shouldCreateUser() {
        // JUnit 5 不再需要 public 方法
        User user = userService.create(new CreateUserRequest("test@example.com"));
        assertThat(user.getId()).isNotNull();
    }
}
```

## Spring Boot 2.3（2020-05）

### Docker 镜像构建

```bash
# Maven
./mvnw spring-boot:build-image

# Gradle
./gradlew bootBuildImage

# 自定义镜像名称
./mvnw spring-boot:build-image -Dspring-boot.build-image.imageName=myapp:latest
```

```xml
<!-- Maven 插件配置 -->
<plugin>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-maven-plugin</artifactId>
    <configuration>
        <image>
            <name>myapp:${project.version}</name>
        </image>
        <layers>
            <enabled>true</enabled>  <!-- 分层 JAR -->
        </layers>
    </configuration>
</plugin>
```

### 优雅关机

```yaml
server:
  shutdown: graceful  # 开启优雅关机

spring:
  lifecycle:
    timeout-per-shutdown-phase: 30s  # 等待时间
```

### Kubernetes 探针

```yaml
management:
  health:
    probes:
      enabled: true  # 开启 K8s 探针（检测到 K8s 环境自动启用）

# 探针端点：
# GET /actuator/health/liveness  → LivenessState
# GET /actuator/health/readiness → ReadinessState
```

## Spring Boot 2.4（2020-11）

### 版本号变化

```
# 1.x 和之前 2.x
2.3.9.RELEASE

# 2.4 起，去掉 .RELEASE 后缀
2.4.0
```

### 新配置文件处理

```yaml
# 2.4 新特性：spring.config.import
spring:
  config:
    import:
      - optional:file:./config/app.properties  # 导入本地文件
      - optional:configserver:http://config-server  # 导入配置中心
      - optional:kubernetes:  # Kubernetes ConfigMap

# 多文档支持（YAML）
spring:
  application:
    name: myapp
---
spring:
  config:
    activate:
      on-profile: production
  datasource:
    url: jdbc:mysql://prod-db:3306/mydb
```

## Spring Boot 2.6（2021-11）

### 禁止循环引用（默认）

```yaml
# 2.6 起，循环依赖默认禁止（启动失败）
# 若必须保留（不推荐）：
spring:
  main:
    allow-circular-references: true
```

### PathPatternParser 成为默认

```java
// 2.6 前：AntPathMatcher（字符串匹配）
// 2.6 起：PathPatternParser（预编译路径模式，性能更好）

// 若依赖 AntPathMatcher 的特殊行为，需显式配置
@Configuration
public class WebConfig implements WebMvcConfigurer {
    @Override
    public void configurePathMatch(PathMatchConfigurer configurer) {
        configurer.setPatternParser(null);  // 回退到 AntPathMatcher
    }
}
```

## Spring Boot 2.7（2022-05）—— 最终 2.x 版本

### `@AutoConfiguration` 注解

```java
// 2.7 前：普通 @Configuration 类放入 spring.factories
@Configuration
@ConditionalOnClass(DataSource.class)
public class DataSourceAutoConfiguration { ... }

// 2.7 起：使用专用 @AutoConfiguration 注解
@AutoConfiguration
@ConditionalOnClass(DataSource.class)
public class DataSourceAutoConfiguration { ... }
```

### 新 AutoConfiguration 注册文件

```
# 2.7 新方式（优先，3.0 将成为唯一方式）
META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports

# 内容示例（每行一个类名）
com.example.FooAutoConfiguration
com.example.BarAutoConfiguration

# 2.7 仍兼容旧方式（3.0 移除）
META-INF/spring.factories
# 内容：
org.springframework.boot.autoconfigure.EnableAutoConfiguration=\
  com.example.FooAutoConfiguration,\
  com.example.BarAutoConfiguration
```

### Spring for GraphQL 1.0

```java
@Controller
public class UserController {
    @QueryMapping
    public User userById(@Argument String id) {
        return userRepository.findById(id).orElseThrow();
    }

    @MutationMapping
    public User createUser(@Argument CreateUserInput input) {
        return userRepository.save(new User(input));
    }
}
```

```graphql
# src/main/resources/graphql/schema.graphqls
type Query {
    userById(id: ID!): User
}

type Mutation {
    createUser(input: CreateUserInput!): User
}

type User {
    id: ID!
    name: String!
    email: String!
}
```

## Spring Security 2.x 演进

```java
// 2.x：WebSecurityConfigurerAdapter（仍然是主要方式）
@Configuration
@EnableWebSecurity
public class SecurityConfig extends WebSecurityConfigurerAdapter {
    @Override
    protected void configure(HttpSecurity http) throws Exception {
        http
            .authorizeRequests()
                .antMatchers("/api/public/**").permitAll()
                .antMatchers("/api/admin/**").hasRole("ADMIN")
                .anyRequest().authenticated()
            .and()
            .oauth2Login()  // 2.0 起内置 OAuth2 客户端
            .and()
            .oauth2ResourceServer()
                .jwt();  // JWT 资源服务器
    }
}

// 2.x OAuth2 配置
// application.yml
spring:
  security:
    oauth2:
      client:
        registration:
          github:
            client-id: your-client-id
            client-secret: your-client-secret
```

## 2.x 关键废弃与移除

| 特性 | 废弃/移除版本 | 替代方案 |
|------|-------------|---------|
| CRaSH 远程 Shell | 2.0 移除 | 无直接替代（JMX/SSH） |
| Tomcat JDBC Pool（默认） | 2.0 换为 HikariCP | HikariCP |
| `spring.factories` AutoConfig | 2.7 废弃 | `.imports` 文件 |
| `WebSecurityConfigurerAdapter` | 2.7 废弃（3.0 移除） | `SecurityFilterChain` Bean |
| `antMatchers()` | 2.7 废弃（3.0 移除） | `requestMatchers()` |
| JUnit 4 默认 | 2.2 起 JUnit 5 默认 | JUnit 5 |
| Elasticsearch RestHighLevelClient | 2.7 废弃 | Elasticsearch Java Client |
| `/httptrace` 端点 | 后续版本移除 | 手动添加 `HttpTraceRepository` |

## 属性迁移辅助工具

```xml
<!-- 检测已重命名/删除的配置属性 -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-properties-migrator</artifactId>
    <scope>runtime</scope>
</dependency>
```

启动时会在日志中提示废弃属性：
```
WARN  PropertyMigrationListener - The use of configuration keys that have been renamed was found in the environment:
  Property source 'application.properties':
    Key: spring.redis.host
      Replacement: spring.data.redis.host
```
