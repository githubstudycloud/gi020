# Spring Boot 4.x 详解 (2025–)

## 概述

Spring Boot 4.x 以 **Spring Framework 7** 为基础，带来三大核心主题：**完全模块化**（autoconfigure 拆分）、**JSpecify 空安全**（编译期空检查）、**BeanRegistrar 接口**（AOT 友好的 Bean 注册）。同时彻底清除了历史积累的废弃项：移除 Undertow、移除经典 Uber JAR 加载器、切换到 Jackson 3 和 Hibernate 7。

> **生命周期**: 2025-11 ~ 至今
> **当前版本**: 4.0.3（2026-03）
> **Java 最低要求**: Java 17（Java 25 获得一等公民支持）

## 各小版本时间线

| 版本 | 发布时间 | Spring Framework | 主要主题 |
|------|---------|-----------------|---------|
| 4.0 | 2025-11-20 | 7.0 | 模块化、JSpecify、BeanRegistrar、Jakarta EE 11 |
| 4.0.3 | 2026-02 | 7.0.5 | 补丁版本（截至 2026-03 最新） |
| 4.1 | ~2026-05 | 7.x | 开发中 |

## 核心组件版本

| 组件 | 版本 |
|------|------|
| Spring Framework | 7.0.x |
| Spring Security | 7.0 |
| Spring Data | 2026.0.0 |
| Spring Batch | 6.0 |
| Spring AMQP | 4.0 |
| Spring Kafka | 4.0 |
| Spring GraphQL | 2.0 |
| Java 最低 | Java 17 |
| Jakarta EE | 11 |
| Servlet API | 6.1 |
| JPA API | 3.2 |
| Bean Validation | 3.1 |
| 嵌入式 Tomcat | 11.0.x |
| 嵌入式 Jetty | 12.0.x |
| 嵌入式 Undertow | **已移除** |
| Hibernate | 7.x (ORM 7.1/7.2) |
| Jackson | **3.x** |
| Kotlin | 2.2+ |
| Micrometer | **2.0** |
| GraalVM | 25+ 要求 |
| Gradle | 8.14+ / 9.x |

## 核心新特性

### 1. 完全模块化 Autoconfigure

4.0 最大的架构变化：`spring-boot-autoconfigure` 这个单一巨型 JAR 被拆分为多个独立小模块。

```
# 3.x：一个 JAR 包含所有自动配置
spring-boot-autoconfigure-3.5.x.jar  (包含数据库、Web、安全等所有自动配置)

# 4.x：按技术领域拆分
spring-boot-autoconfigure-core-4.0.x.jar
spring-boot-autoconfigure-web-4.0.x.jar
spring-boot-autoconfigure-data-jpa-4.0.x.jar
spring-boot-autoconfigure-security-4.0.x.jar
spring-boot-autoconfigure-actuator-4.0.x.jar
...
```

效果：
- **更小的依赖树**：按需引入，不拉取不用的自动配置
- **更快的启动**：扫描更少的类
- **更好的模块封装**：自动配置类不再是 public API

向下兼容：
```xml
<!-- 需要旧布局的项目可使用兼容模块 -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-autoconfigure-classic</artifactId>
</dependency>
```

### 2. JSpecify 空安全（编译期零指针保护）

```java
// 3.x：依赖 Spring 自己的注解（运行期检查为主）
import org.springframework.lang.Nullable;
import org.springframework.lang.NonNull;

// 4.x：切换到 JSpecify（业界标准，编译期检查）
import org.jspecify.annotations.Nullable;
import org.jspecify.annotations.NullMarked;
import org.jspecify.annotations.NonNull;
```

整个 Spring Boot 4 代码库在包级别标注了 `@NullMarked`：

```java
// 包声明文件 package-info.java
@NullMarked  // 该包下所有类型默认非 null
package com.example.myapp;

import org.jspecify.annotations.NullMarked;
```

```java
// 有了 @NullMarked，null 返回值必须显式标注
@NullMarked
public class UserService {
    // 正确：返回值非空（@NullMarked 下的默认）
    public User findById(Long id) {
        return repository.findById(id)
            .orElseThrow(() -> new UserNotFoundException(id));
    }

    // 正确：可能返回 null 时标注 @Nullable
    @Nullable
    public User findByEmail(String email) {
        return repository.findByEmail(email).orElse(null);
    }

    // 参数也可以是 @Nullable
    public void updateProfile(Long id, @Nullable String bio) {
        // ...
    }
}
```

IDE（IntelliJ IDEA）和 Kotlin 编译器均原生支持 JSpecify，提供编译期警告：
```
Warning: Possible null pointer dereference: result of 'findByEmail' can be null
```

Kotlin 互操作性：
```kotlin
// Kotlin 编译器将 JSpecify @Nullable 映射到 Kotlin 可空类型
val user: User? = userService.findByEmail("test@example.com")  // 自动推断为可空
val user2: User = userService.findById(1L)  // 自动推断为非空
```

### 3. BeanRegistrar 接口（AOT 友好 Bean 注册）

```java
// 传统 @Bean 方式（反射重，AOT 代理生成）
@Configuration
public class MyConfig {
    @Bean
    public UserService userService(UserRepository repo) {
        return new UserService(repo);
    }
}

// 新 BeanRegistrar（AOT 友好，无反射）
import org.springframework.beans.factory.BeanRegistrar;
import org.springframework.beans.factory.BeanRegistry;
import org.springframework.core.env.Environment;

public class MyBeanRegistrar implements BeanRegistrar {
    @Override
    public void register(BeanRegistry registry, Environment env) {
        registry.registerBean("userService", UserService.class,
            spec -> spec.supplier(ctx ->
                new UserService(ctx.getBean(UserRepository.class))
            )
        );
    }
}

// 注册（类似 @Import）
@Import(MyBeanRegistrar.class)
@SpringBootApplication
public class Application { ... }
```

Kotlin DSL（更优雅）：
```kotlin
class MyBeanRegistrar : BeanRegistrarDsl({
    bean<UserService> {
        UserService(ref<UserRepository>())
    }
    bean<OrderService> {
        OrderService(ref<UserRepository>(), ref<PaymentService>())
    }
})
```

动态注册多个 Bean 的场景：
```java
public class MultiTenantRegistrar implements BeanRegistrar {
    @Override
    public void register(BeanRegistry registry, Environment env) {
        // 根据配置动态注册多个租户数据源
        String[] tenants = env.getProperty("tenants", String[].class, new String[0]);
        for (String tenant : tenants) {
            registry.registerBean(tenant + "DataSource", DataSource.class,
                spec -> spec.supplier(ctx -> createDataSource(tenant, env))
            );
        }
    }
}
```

### 4. `@ImportHttpServices`（零配置声明式 HTTP 客户端）

```java
// 3.x：需要手动配置 HttpServiceProxyFactory
@Configuration
public class ClientConfig {
    @Bean
    public UserClient userClient(RestClient.Builder builder) {
        RestClient restClient = builder.baseUrl("http://user-service").build();
        RestClientAdapter adapter = RestClientAdapter.create(restClient);
        HttpServiceProxyFactory factory = HttpServiceProxyFactory.builderFor(adapter).build();
        return factory.createClient(UserClient.class);
    }
}

// 4.x：零配置，只需注解
@SpringBootApplication
@ImportHttpServices(UserClient.class)  // 自动注册为 Bean！
public class Application { ... }

// 或放在配置类上
@Configuration
@ImportHttpServices({UserClient.class, OrderClient.class})
public class HttpClientsConfig { }
```

```yaml
# application.yml 配置客户端
spring:
  http:
    clients:
      user-client:
        base-url: http://user-service
        connect-timeout: 5s
        read-timeout: 30s
```

### 5. API 版本控制（内置）

```yaml
spring:
  mvc:
    apiversion:
      enabled: true
      default-version: "1"  # 无版本号时使用的默认版本
```

```java
// URL 路径版本（/v1/users, /v2/users）
@RestController
@RequestMapping("/users")
public class UserController {

    @GetMapping  // 所有版本
    public List<User> listUsersV1() { ... }

    @GetMapping
    @ApiVersion("2")  // 仅 v2
    public Page<UserDTO> listUsersV2(Pageable pageable) { ... }
}

// Header 版本（X-API-Version: 2）
// Media Type 版本（application/vnd.myapp.v2+json）
// 由 ApiVersionResolver Bean 控制
```

### 6. Spring Framework 7 内置弹性（Retry/Timeout/Fallback）

```java
// 无需额外依赖（不需要 @EnableRetry 或引入 Spring Retry）
@Service
public class UserService {

    @Retryable(retryFor = {IOException.class}, maxAttempts = 3, backoff = @Backoff(delay = 1000))
    public User fetchFromRemote(String userId) {
        return remoteClient.fetch(userId);  // 网络错误时自动重试
    }

    @Timeout(value = 5, unit = ChronoUnit.SECONDS)
    public User fetchWithTimeout(String userId) {
        return remoteClient.fetchSlow(userId);  // 超时抛出异常
    }

    @Fallback(fallbackMethod = "fallbackUser")
    public User fetchWithFallback(String userId) {
        return remoteClient.fetch(userId);
    }

    private User fallbackUser(String userId, Throwable ex) {
        return User.defaultUser(userId);
    }
}
```

### 7. Micrometer 2.0 + OpenTelemetry 一等公民

```xml
<!-- 新的 OpenTelemetry starter -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-opentelemetry</artifactId>
</dependency>
```

```yaml
management:
  opentelemetry:
    resource:
      attributes:
        service.name: my-service
        service.version: 1.0.0
    tracing:
      endpoint: http://otel-collector:4318/v1/traces
    metrics:
      endpoint: http://otel-collector:4318/v1/metrics
```

### 8. AOT Repositories（Spring Data 编译期处理）

```java
// 4.x：Spring Data 在构建时将 Repository 查询方法编译为实际代码
// 无需运行时字节码生成

@Repository
public interface UserRepository extends JpaRepository<User, Long> {
    // 这个方法在编译时生成查询实现代码
    List<User> findByEmailAndActive(String email, boolean active);

    @Query("SELECT u FROM User u WHERE u.createdAt > :since")
    List<User> findRecentUsers(LocalDateTime since);
}

// 构建时生成（native image 中无需运行时反射）：
// target/generated-sources/...UserRepositoryImpl.java
```

### 9. Kotlin Serialization 支持

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-kotlin-serialization</artifactId>
</dependency>
```

```kotlin
@Serializable
data class User(
    val id: Long,
    val name: String,
    val email: String
)

// 配置
// application.yml
spring:
  kotlinx:
    serialization:
      json:
        pretty-print: true
        ignore-unknown-keys: true
```

### 10. 测试改进：`RestTestClient`

```java
// 4.x：在 MockMvc 测试中可以注入 RestTestClient
@SpringBootTest
@AutoConfigureMockMvc
class UserControllerTest {

    @Autowired
    private RestTestClient restTestClient;  // 新的！基于 MockMvc 的 RestClient 风格

    @Test
    void shouldGetUser() {
        restTestClient.get()
            .uri("/users/{id}", 1L)
            .exchange()
            .expectStatus().isOk()
            .expectBody(User.class)
            .value(user -> assertThat(user.getName()).isEqualTo("John"));
    }

    @Test
    void shouldCreateUser() {
        restTestClient.post()
            .uri("/users")
            .body(new CreateUserRequest("John", "john@example.com"))
            .exchange()
            .expectStatus().isCreated()
            .expectHeader().exists("Location");
    }
}
```

## Jackson 3.x 重大变化

Jackson 3 是破坏性升级，行为变化显著：

```java
// 包名变化：com.fasterxml.jackson → tools.jackson
// 注解变化
// Jackson 2.x
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.databind.ObjectMapper;

// Jackson 3.x（Boot 4 管理的版本）
// 包名保持不变（Jackson 3 仍用 com.fasterxml.jackson），
// 但模块结构和默认行为变化

// 主要行为变化：
// 1. 更严格的类型处理
// 2. 默认不序列化 null 字段（需要显式配置）
// 3. MapperFeature 和 DeserializationFeature 的默认值变化

// 配置示例
spring:
  jackson:
    default-property-inclusion: non-null  # 不序列化 null
    deserialization:
      fail-on-unknown-properties: false
    serialization:
      write-dates-as-timestamps: false
```

## Hibernate 7.x 主要变化

```java
// 包路径变化（Hibernate 原生 API）
// 6.x
import org.hibernate.Session;
import org.hibernate.cfg.Configuration;

// 7.x（JPA 模式下变化不大，主要是原生 Hibernate API）
// orm.jpa.hibernate 包重组

// ID 生成器变化（JPA 3.2 对应）
@Entity
public class User {
    @Id
    @GeneratedValue(strategy = GenerationType.SEQUENCE,
                    generator = "user_seq")
    @SequenceGenerator(name = "user_seq", sequenceName = "USER_SEQ")
    private Long id;  // Hibernate 7 对序列生成器有更强制的规范
}

// HQL 语法增强（JPA 3.2 扩展）
// 支持 UNION、INTERSECT、EXCEPT
@Query("SELECT u FROM User u WHERE u.role = 'ADMIN' " +
       "UNION " +
       "SELECT u FROM User u WHERE u.role = 'SUPERUSER'")
List<User> findPrivilegedUsers();
```

## Undertow 移除

```xml
<!-- 3.x：可以使用 Undertow -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-web</artifactId>
    <exclusions>
        <exclusion>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-tomcat</artifactId>
        </exclusion>
    </exclusions>
</dependency>
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-undertow</artifactId>
</dependency>

<!-- 4.x：Undertow 不再支持（Jakarta Servlet 6.1 不兼容） -->
<!-- 迁移到 Tomcat 11 或 Jetty 12 -->
```

## 从 3.x 迁移到 4.x 核心清单

```
□ 确认 GraalVM 版本为 25+（如使用 Native Image）
□ 升级 Gradle 至 8.14+ 或 9.x
□ 迁移 Undertow 到 Tomcat 11 或 Jetty 12
□ 升级 Jackson 到 3.x，检查行为变化
□ 升级 Hibernate 到 7.x，检查原生 API 变化
□ 更新 JPA 2.x → 3.2 语法（JPA 3.2 新特性）
□ 将空安全注解迁移到 JSpecify（渐进式）
□ 检查 spring.factories 中的其他配置（不仅是 AutoConfiguration）
□ 移除对 spring-security-oauth2-autoconfigure 的依赖
□ 更新 Spring Security 到 7.0 API
□ 更新 Spring Batch 到 6.0 API（如使用）
□ 检查第三方库的 Spring Boot 4 兼容性
```

## Spring Security 7.0

```java
// 继续使用 SecurityFilterChain（无变化）
@Configuration
@EnableWebSecurity
public class SecurityConfig {

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/api/public/**").permitAll()
                .anyRequest().authenticated()
            )
            .oauth2ResourceServer(oauth2 -> oauth2
                .jwt(jwt -> jwt
                    .decoder(JwtDecoders.fromIssuerLocation(issuerUri))
                )
            );
        return http.build();
    }
}
```

Spring Authorization Server（已整合进 Spring Security）：
```xml
<!-- 4.x：不再需要单独的 starter -->
<!-- 直接使用 spring-security-authorization-server 依赖 -->
```

## 与 3.x 核心差异总结

| 方面 | Spring Boot 3.x | Spring Boot 4.x |
|------|----------------|----------------|
| Spring Framework | 6.x | 7.x |
| Jakarta EE | 10 (Servlet 6.0) | 11 (Servlet 6.1) |
| Tomcat | 10.1.x | **11.0.x** |
| Undertow | 支持 | **已移除** |
| Hibernate | 6.x | **7.x** |
| Jackson | 2.x | **3.x** |
| Micrometer | 1.x | **2.0** |
| 空安全 | Spring 注解/JSR 305 | **JSpecify** |
| 自动配置 JAR | 单一 JAR | **完全模块化** |
| Bean 注册 | `@Bean` 方法 | `@Bean` + **`BeanRegistrar`** |
| HTTP 客户端 | 需要手动配置代理 | **`@ImportHttpServices`** 零配置 |
| 弹性能力 | 需要 Spring Retry | **框架内置 Retry/Timeout/Fallback** |
| GraalVM | 任意版本 | **GraalVM 25+** |
| 经典 Uber JAR 加载器 | 支持 | **已移除** |
