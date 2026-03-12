# Spring Boot 3.x 详解 (2022–2025)

## 概述

Spring Boot 3.x 是现代云原生时代的全面革新。**最大变化：`javax.*` → `jakarta.*` 命名空间迁移**，Java 17 成为最低要求，GraalVM Native Image 进入正式支持，Micrometer Tracing 统一可观测性。

> **生命周期**: 2022-11 ~ 2025-06（3.5.x OSS 支持）
> **最终版本**: 3.5.x（OSS 支持至 2026-06，商业支持至 2032-06）

## 各小版本时间线

| 版本 | 发布时间 | Spring Framework | 主要主题 |
|------|---------|-----------------|---------|
| 3.0 | 2022-11 | 6.0 | Jakarta EE、Java 17+、GraalVM 正式支持 |
| 3.1 | 2023-05 | 6.0 | Testcontainers、Docker Compose、SSL Bundles |
| 3.2 | 2023-11 | 6.1 | **Virtual Threads**、RestClient、CRaC |
| 3.3 | 2024-05 | 6.1 | CDS、SBOM 端点、SNI |
| 3.4 | 2024-11 | 6.2 | **结构化日志**、SSL 健康、Jakarta EE 11 对齐 |
| 3.5 | 2025-05 | 6.2 | WebClient 配置属性、SSL 服务连接（最终版） |

## 核心组件版本对比

| 组件 | 3.0 | 3.5 |
|------|-----|-----|
| Spring Framework | 6.0 | 6.2 |
| Java 最低 | Java 17 | Java 17 |
| Servlet API | Jakarta EE 10 / Servlet 6.0 | Jakarta EE 10/11 |
| 嵌入式 Tomcat | 10.1.x | 10.1.x |
| 嵌入式 Jetty | 11.x | 12.x |
| 嵌入式 Undertow | 2.3.x | 2.3.x |
| Hibernate | 6.1 | 6.4.x |
| Jackson | 2.14 | 2.17.x |
| JUnit | 5.9 | 5.11.x |
| Micrometer | 1.10 | 1.13.x |
| Kotlin | 1.7 | 1.9.x |
| Spring Security | 6.0 | 6.3.x |
| Spring Data | 2022.0 | 2024.0 |
| Spring AMQP | 3.0 | 3.1.x |
| Spring Kafka | 3.0 | 3.2.x |

## Spring Boot 3.0（2022-11）重大变化

### 最大变化：`javax.*` → `jakarta.*`

```java
// 2.x（旧）
import javax.persistence.Entity;
import javax.persistence.Id;
import javax.servlet.http.HttpServletRequest;
import javax.validation.constraints.NotNull;
import javax.annotation.PostConstruct;
import javax.transaction.Transactional;

// 3.x（新）
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.constraints.NotNull;
import jakarta.annotation.PostConstruct;
import jakarta.transaction.Transactional;
```

> 注意：以下 `javax.*` 包**不需要**迁移（属于 JDK 标准库）：
> - `javax.sql.*`（JDBC 数据源）
> - `javax.crypto.*`
> - `javax.net.*`
> - `javax.security.*`（部分）

自动迁移工具：
```bash
# OpenRewrite 自动迁移（推荐）
./mvnw rewrite:run -Drewrite.activeRecipes=org.openrewrite.java.spring.boot3.UpgradeSpringBoot_3_0

# IntelliJ IDEA 迁移助手
# File → Project Structure → Modules → Dependencies 检查 javax → jakarta
```

### Java 17 新特性充分利用

```java
// Records（不可变数据类）
public record UserDTO(Long id, String name, String email) {}

// Sealed Classes（受限继承）
public sealed interface Shape permits Circle, Rectangle, Triangle {}
public record Circle(double radius) implements Shape {}
public record Rectangle(double width, double height) implements Shape {}

// Pattern Matching for switch
String formatShape(Shape shape) {
    return switch (shape) {
        case Circle c -> "Circle with radius: " + c.radius();
        case Rectangle r -> "Rectangle: " + r.width() + "x" + r.height();
        case Triangle t -> "Triangle";
    };
}

// Text Blocks
String json = """
    {
        "name": "John",
        "email": "john@example.com"
    }
    """;
```

### GraalVM Native Image（正式支持）

```bash
# 安装 GraalVM 和 native-image 工具

# Maven 编译
./mvnw -Pnative package
# 或
./mvnw -Pnative spring-boot:build-image  # 构建 OCI 镜像

# Gradle
./gradlew nativeCompile
./gradlew bootBuildImage  # 构建 OCI 镜像
```

```xml
<!-- Maven pom.xml -->
<profiles>
    <profile>
        <id>native</id>
        <build>
            <plugins>
                <plugin>
                    <groupId>org.graalvm.buildtools</groupId>
                    <artifactId>native-maven-plugin</artifactId>
                </plugin>
            </plugins>
        </build>
    </profile>
</profiles>
```

AOT（提前编译）提示：
```java
// 告知 AOT 哪些类需要反射访问
@ImportRuntimeHints(MyRuntimeHints.class)
@SpringBootApplication
public class Application { ... }

class MyRuntimeHints implements RuntimeHintsRegistrar {
    @Override
    public void registerHints(RuntimeHints hints, ClassLoader classLoader) {
        hints.reflection()
            .registerType(MyDynamicClass.class,
                MemberCategory.INVOKE_DECLARED_CONSTRUCTORS,
                MemberCategory.INVOKE_DECLARED_METHODS);
        hints.resources().registerPattern("static/**");
    }
}
```

### Micrometer Tracing（可观测性统一）

```xml
<!-- 添加 Tracing 支持（选择一个 bridge） -->
<dependency>
    <groupId>io.micrometer</groupId>
    <artifactId>micrometer-tracing-bridge-otel</artifactId>
    <!-- 或 micrometer-tracing-bridge-brave（Sleuth） -->
</dependency>

<!-- Zipkin 导出 -->
<dependency>
    <groupId>io.zipkin.reporter2</groupId>
    <artifactId>zipkin-reporter-brave</artifactId>
</dependency>
```

```yaml
management:
  tracing:
    sampling:
      probability: 1.0  # 100% 采样率（生产环境建议 0.1）
  zipkin:
    tracing:
      endpoint: http://localhost:9411/api/v2/spans
```

```java
// @Observed 注解（声明式观测）
@Service
@Observed(name = "user.service")
public class UserService {
    @Observed(name = "user.service.findById")
    public User findById(String id) {
        return repository.findById(id).orElseThrow();
    }
}
// 需要 spring-boot-starter-aop 和 @EnableObservability（或 @SpringBootApplication 自动启用）
```

### Spring Security 6.0（重大变化）

```java
// 3.x：WebSecurityConfigurerAdapter 已移除！
// 必须改用 SecurityFilterChain Bean

@Configuration
@EnableWebSecurity
public class SecurityConfig {

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .authorizeHttpRequests(auth -> auth  // 不再是 authorizeRequests()
                .requestMatchers("/api/public/**").permitAll()  // 不再是 antMatchers()
                .requestMatchers("/api/admin/**").hasRole("ADMIN")
                .anyRequest().authenticated()
            )
            .oauth2Login(Customizer.withDefaults())
            .oauth2ResourceServer(oauth2 -> oauth2
                .jwt(Customizer.withDefaults())
            );
        return http.build();
    }

    @Bean
    public UserDetailsService userDetailsService() {
        UserDetails user = User.withDefaultPasswordEncoder()
            .username("user")
            .password("password")
            .roles("USER")
            .build();
        return new InMemoryUserDetailsManager(user);
    }
}
```

### HTTP 接口客户端

```java
// 声明接口（无需实现，Spring 自动代理）
@HttpExchange("/api/users")
public interface UserClient {

    @GetExchange("/{id}")
    User getUser(@PathVariable String id);

    @GetExchange
    List<User> getAllUsers();

    @PostExchange
    User createUser(@RequestBody CreateUserRequest request);

    @DeleteExchange("/{id}")
    void deleteUser(@PathVariable String id);
}

// 注册为 Bean
@Configuration
public class ClientConfig {
    @Bean
    public UserClient userClient(RestClient.Builder builder) {
        RestClient restClient = builder
            .baseUrl("http://user-service")
            .build();
        RestClientAdapter adapter = RestClientAdapter.create(restClient);
        HttpServiceProxyFactory factory = HttpServiceProxyFactory.builderFor(adapter).build();
        return factory.createClient(UserClient.class);
    }
}
```

### RFC 7807 Problem Details

```java
// 开启 Problem Details（RFC 7807）
// application.yml
spring:
  mvc:
    problemdetails:
      enabled: true

// 自动生成标准错误响应：
// {
//   "type": "about:blank",
//   "title": "Bad Request",
//   "status": 400,
//   "detail": "Validation failed for ...",
//   "instance": "/api/users"
// }
```

### 尾部斜杠不再匹配

```java
// 3.0 前：/api/users/ 等同于 /api/users
// 3.0 起：/api/users/ 返回 404

// 若需要保持兼容：
@Configuration
public class WebConfig implements WebMvcConfigurer {
    @Override
    public void configurePathMatch(PathMatchConfigurer configurer) {
        configurer.setUseTrailingSlashMatch(true);  // 废弃，谨慎使用
    }
}
```

## Spring Boot 3.1（2023-05）

### Testcontainers 集成

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-testcontainers</artifactId>
    <scope>test</scope>
</dependency>
<dependency>
    <groupId>org.testcontainers</groupId>
    <artifactId>postgresql</artifactId>
    <scope>test</scope>
</dependency>
```

```java
@SpringBootTest
@Testcontainers
class UserRepositoryTest {

    @Container
    @ServiceConnection  // 自动配置连接属性（无需手动 @DynamicPropertySource）
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:15");

    @Autowired
    private UserRepository userRepository;

    @Test
    void shouldFindUser() {
        userRepository.save(new User("John", "john@example.com"));
        assertThat(userRepository.findByEmail("john@example.com")).isPresent();
    }
}
```

开发时启动容器（替代本地安装）：
```java
// 开发时自动启动 Docker 容器
@SpringBootApplication
public class Application {
    public static void main(String[] args) {
        SpringApplication.from(Application::main)
            .with(MyContainersConfig.class)  // 开发时容器配置
            .run(args);
    }
}

@TestConfiguration(proxyBeanMethods = false)
class MyContainersConfig {
    @Bean
    @ServiceConnection
    PostgreSQLContainer<?> postgresContainer() {
        return new PostgreSQLContainer<>("postgres:15");
    }

    @Bean
    @ServiceConnection
    RedisContainer redisContainer() {
        return new RedisContainer(DockerImageName.parse("redis:7"));
    }
}
```

### Docker Compose 集成

```yaml
# compose.yml（根目录）
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: mydb
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
  redis:
    image: redis:7
    ports:
      - "6379:6379"
```

```yaml
# application.yml
spring:
  docker:
    compose:
      enabled: true  # 启动时自动 docker compose up
      stop:
        command: stop  # 关闭时 docker compose stop（而非 down）
```

### SSL Bundles

```yaml
# 统一 SSL 配置（跨服务器、客户端、数据源）
spring:
  ssl:
    bundle:
      jks:
        mybundle:
          key:
            alias: mykey
          keystore:
            location: classpath:keystore.p12
            password: secret
            type: PKCS12

server:
  ssl:
    bundle: mybundle  # 引用 SSL Bundle

# 数据源 SSL
spring:
  datasource:
    url: jdbc:postgresql://localhost:5432/mydb?sslmode=verify-full
    ssl:
      bundle: mybundle
```

## Spring Boot 3.2（2023-11）

### Virtual Threads（虚拟线程/Project Loom）

```yaml
# Java 21+ 开启虚拟线程
spring:
  threads:
    virtual:
      enabled: true
```

效果：
- Tomcat 和 Jetty 使用虚拟线程处理请求（每请求一个虚拟线程）
- `@Async` 方法使用虚拟线程执行器
- `@Scheduled` 方法使用虚拟线程

性能对比（阻塞 IO 场景）：
```
传统平台线程：受限于线程池大小（如 200 个线程）
虚拟线程：可创建数百万个，阻塞 IO 时挂起而非占用系统线程
```

```java
// 手动使用虚拟线程
Thread.ofVirtual().start(() -> {
    // 执行阻塞操作
    var result = blockingDbCall();
    System.out.println(result);
});

// ExecutorService 使用虚拟线程
try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
    executor.submit(() -> processTask());
}
```

### RestClient（新 HTTP 客户端）

```java
// RestTemplate（旧，仍支持但不再积极发展）
RestTemplate restTemplate = new RestTemplate();
User user = restTemplate.getForObject("http://api/users/{id}", User.class, id);

// RestClient（新，3.2+，流式风格，类似 WebClient 但阻塞）
RestClient restClient = RestClient.builder()
    .baseUrl("http://api")
    .defaultHeader("Accept", "application/json")
    .build();

User user = restClient.get()
    .uri("/users/{id}", id)
    .retrieve()
    .body(User.class);

// 错误处理
restClient.post()
    .uri("/users")
    .body(createRequest)
    .retrieve()
    .onStatus(HttpStatusCode::is4xxClientError, (req, res) -> {
        throw new UserNotFoundException("User not found");
    })
    .toBodilessEntity();

// 注入（Auto-configured RestClient.Builder）
@Service
public class UserService {
    private final RestClient restClient;

    public UserService(RestClient.Builder builder) {
        this.restClient = builder
            .baseUrl("http://user-service")
            .build();
    }
}
```

### JdbcClient（新 JDBC 客户端）

```java
// JdbcTemplate（旧）
List<User> users = jdbcTemplate.query(
    "SELECT * FROM users WHERE active = ?",
    (rs, row) -> new User(rs.getLong("id"), rs.getString("name")),
    true
);

// JdbcClient（新，3.2+，流式风格）
@Autowired
private JdbcClient jdbcClient;

List<User> users = jdbcClient
    .sql("SELECT * FROM users WHERE active = :active")
    .param("active", true)
    .query(User.class)  // 自动映射（需要 record 或标准 Java Bean）
    .list();

// 单个结果
Optional<User> user = jdbcClient
    .sql("SELECT * FROM users WHERE id = :id")
    .param("id", userId)
    .query(User.class)
    .optional();

// 更新
int rows = jdbcClient
    .sql("UPDATE users SET name = :name WHERE id = :id")
    .param("name", "NewName")
    .param("id", userId)
    .update();
```

### CRaC（Coordinated Restore at Checkpoint）

```bash
# 需要 CRaC 版本的 JDK（如 Azul Zulu CRaC）

# 1. 启动应用
java -XX:CRaCCheckpointTo=/tmp/checkpoint -jar myapp.jar

# 2. 创建检查点（应用运行时）
jcmd $(pgrep -f myapp.jar) JDK.checkpoint

# 3. 从检查点恢复（毫秒级启动）
java -XX:CRaCRestoreFrom=/tmp/checkpoint
```

## Spring Boot 3.3（2024-05）

### CDS（Class Data Sharing）

```bash
# 1. 训练运行（收集类使用数据）
java -XX:ArchiveClassesAtExit=application.jsa \
     -Dspring.context.exit=onRefresh \
     -jar myapp.jar

# 2. 使用 CDS 启动（更快）
java -XX:SharedArchiveFile=application.jsa -jar myapp.jar
```

### SBOM 端点

```yaml
# 暴露 SBOM 端点
management:
  endpoints:
    web:
      exposure:
        include: sbom

# 访问：GET /actuator/sbom
# 返回：CycloneDX/SPDX 格式的软件物料清单
```

## Spring Boot 3.4（2024-11）

### 结构化日志

```yaml
logging:
  structured:
    format:
      console: ecs       # Elastic Common Schema（JSON 格式）
      # 或 gelf          # Graylog Extended Log Format
      # 或 logstash      # Logstash JSON
```

ECS 格式输出示例：
```json
{
  "@timestamp": "2024-11-15T10:30:00.000Z",
  "log.level": "INFO",
  "message": "User created successfully",
  "service.name": "myapp",
  "service.version": "1.0.0",
  "process.pid": 12345,
  "log.logger": "com.example.UserService",
  "trace.id": "abc123",
  "span.id": "def456"
}
```

## Spring Boot 3.x 共同变化

### 自动配置注册方式

```
# 3.0 起 spring.factories 中的 AutoConfiguration 完全移除
# 只使用：
META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports

# 内容（每行一个）：
com.example.autoconfigure.FooAutoConfiguration
com.example.autoconfigure.BarAutoConfiguration
```

### Actuator 变化

```yaml
management:
  endpoints:
    web:
      exposure:
        # 3.x 默认只暴露 health
        # info 需要显式加入（2.5 起不再默认暴露）
        include: health, info, metrics, prometheus, startup
  endpoint:
    health:
      show-details: when-authorized
      group:
        liveness:
          include: livenessState
        readiness:
          include: readinessState, db, redis
```

### Spring Data 3.x 变化

```java
// Spring Data 3.0：repository 方法不再返回 null，改用 Optional
// 原来：User findByEmail(String email); // 可能返回 null
// 现在：Optional<User> findByEmail(String email);

// Scroll API（大数据分页，避免深度分页性能问题）
Window<User> window = userRepository.findTop10By(
    ScrollPosition.offset()
);
while (window.hasNext()) {
    window = userRepository.findTop10By(window.positionAt(window.size() - 1));
}
```

## 从 2.x 迁移到 3.x 核心清单

```
□ Java 版本升级至 17+
□ 全局替换 javax.* → jakarta.*（使用迁移工具）
□ 升级第三方库到支持 Jakarta EE 的版本
□ WebSecurityConfigurerAdapter → SecurityFilterChain Bean
□ antMatchers() → requestMatchers()
□ authorizeRequests() → authorizeHttpRequests()
□ spring.factories → .imports 文件（自定义自动配置）
□ 检查 Hibernate 5→6 的 ID 生成器变化
□ 检查 Tomcat 9→10 的兼容性
□ 处理尾部斜杠 URL 匹配问题
□ 检查 spring-security-oauth2-autoconfigure 替换
```
