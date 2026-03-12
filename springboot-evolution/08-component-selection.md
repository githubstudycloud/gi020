# Spring Boot 各版本主流组件选型方案

> 面向实际项目的选型建议，覆盖从 1.x 遗留维护到 4.x 全新构建的场景。
> 标注 ★ 为该版本时期的**业界主流首选**；标注 ⚠️ 表示**应规避或已过时**。

---

## Spring Boot 1.x 时代（2014–2019）

> 适用场景：**遗留系统维护**。新项目不应再选择此版本线。

### 运行环境

| 类别 | 选型 | 版本 | 说明 |
|------|------|------|------|
| **Spring Boot** | spring-boot | ★ 1.5.22.RELEASE | 1.x 最终稳定版，最大兼容性 |
| **Java** | JDK | ★ Java 8 | 1.x 时代主流，避免用 Java 6/7 |
| **构建工具** | Maven | ★ 3.5+ | 主流选择 |
| **构建工具** | Gradle | 3.x~4.x | 可用，但 Maven 更主流 |

### Web 层

| 类别 | 选型 | 版本 | 说明 |
|------|------|------|------|
| **Web 框架** | Spring MVC | ★ 4.3.x（Boot 管理） | 标准选择，注解驱动 |
| **嵌入式服务器** | Tomcat | ★ 8.5.x | 默认，稳定 |
| **嵌入式服务器** | Undertow | 1.x | 高并发场景可选，性能略好于 Tomcat |
| **JSON 序列化** | Jackson | ★ 2.8.x | 默认，无需额外引入 |
| **API 文档** | Springfox Swagger2 | ★ 2.9.x | `@EnableSwagger2` |
| **参数校验** | Hibernate Validator | 5.x（javax.validation） | Boot 自动配置 |

```xml
<!-- API 文档（1.x 时代标配） -->
<dependency>
    <groupId>io.springfox</groupId>
    <artifactId>springfox-swagger2</artifactId>
    <version>2.9.2</version>
</dependency>
<dependency>
    <groupId>io.springfox</groupId>
    <artifactId>springfox-swagger-ui</artifactId>
    <version>2.9.2</version>
</dependency>
```

### 数据层

| 类别 | 选型 | 版本 | 说明 |
|------|------|------|------|
| **ORM** | Spring Data JPA + Hibernate | ★ 5.0.x | 标准首选 |
| **ORM** | MyBatis | ★ 1.3.x | SQL 控制需求强时首选 |
| **连接池** | HikariCP | 2.x | ⚠️ 需手动替换，1.x 默认是 Tomcat JDBC |
| **连接池** | Tomcat JDBC Pool | ⚠️ 默认 | 建议显式换为 HikariCP |
| **数据库迁移** | Flyway | ★ 3.x~4.x | 主流，SQL 文件管理迁移 |
| **数据库迁移** | Liquibase | 3.x | XML/YAML 格式，可选 |
| **缓存** | Redis（Lettuce/Jedis） | ★ Jedis 2.x | 1.x 默认 Jedis，Lettuce 需显式配置 |
| **缓存** | Ehcache 2.x | 2.x | 本地缓存，无需外部依赖 |

```xml
<!-- 1.x 推荐：手动替换 HikariCP -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-data-jpa</artifactId>
    <exclusions>
        <exclusion>
            <groupId>org.apache.tomcat</groupId>
            <artifactId>tomcat-jdbc</artifactId>
        </exclusion>
    </exclusions>
</dependency>
<dependency>
    <groupId>com.zaxxer</groupId>
    <artifactId>HikariCP</artifactId>
</dependency>
```

### 安全

| 类别 | 选型 | 版本 | 说明 |
|------|------|------|------|
| **认证授权** | Spring Security | ★ 4.x | 标准，`WebSecurityConfigurerAdapter` 模式 |
| **OAuth2** | spring-security-oauth2 | ★ 2.3.x | 外部库，需额外引入 |
| **JWT** | jjwt | 0.9.x | 最流行的 JWT 库 |

### 消息队列

| 类别 | 选型 | 版本 | 说明 |
|------|------|------|------|
| **消息队列** | RabbitMQ（Spring AMQP） | ★ 1.7.x | `spring-boot-starter-amqp` |
| **消息队列** | Kafka（Spring Kafka） | ★ 1.2.x | `spring-boot-starter` + spring-kafka |
| **消息队列** | ActiveMQ | 5.14.x | `spring-boot-starter-activemq` |

### 可观测

| 类别 | 选型 | 版本 | 说明 |
|------|------|------|------|
| **监控端点** | Spring Boot Actuator | ★ 内置 | 路径 `/health`, `/metrics` 等 |
| **指标** | 内置简单计数器 | — | ⚠️ 无 Micrometer，功能有限 |
| **日志** | Logback | ★ 1.1.x | 默认，`logback-spring.xml` |

### 测试

| 类别 | 选型 | 版本 | 说明 |
|------|------|------|------|
| **单元测试** | JUnit 4 | ★ 4.12 | 默认，`@RunWith(SpringRunner.class)` |
| **Mock** | Mockito | ★ 1.x~2.x | `@MockBean` 支持 |
| **断言** | AssertJ | 2.x | Boot 自动引入 |
| **内存数据库** | H2 | 1.x | 测试标配 |

### 工具库

| 类别 | 选型 | 版本 | 说明 |
|------|------|------|------|
| **代码简化** | Lombok | ★ 1.16.x | `@Data`, `@Slf4j` |
| **对象映射** | MapStruct | 1.2.x | DTO ↔ Entity 映射 |
| **HTTP 客户端** | RestTemplate | ★ 内置 | 同步 HTTP 调用标配 |
| **HTTP 客户端** | OkHttp | 3.x | 可选，与 RestTemplate 整合 |

---

## Spring Boot 2.x 时代（2018–2023）

> **推荐选择 2.7.x**（OSS 已结束，有商业支持延长至 2029）。
> 适用场景：仍在运行的生产系统、无法立即升级 Java 17 的项目。

### 运行环境

| 类别 | 选型 | 版本 | 说明 |
|------|------|------|------|
| **Spring Boot** | spring-boot | ★ 2.7.18 | 2.x 最终版，最稳定 |
| **Java** | JDK | ★ Java 11 LTS | 主流选择，Go-to for 2.x |
| **Java** | JDK | Java 17 LTS | 升级预备，兼容 2.7.x |
| **Java** | JDK | ⚠️ Java 8 | 可运行，但错过大量新特性 |
| **构建工具** | Maven | ★ 3.6+ | 推荐 |
| **构建工具** | Gradle | ★ 6.8+ | 2.7.x 主流 Gradle 版本 |

### Web 层

| 类别 | 选型 | 版本 | 说明 |
|------|------|------|------|
| **Web 框架（同步）** | Spring MVC | ★ 5.3.x | 标准选择，大多数业务场景 |
| **Web 框架（响应式）** | Spring WebFlux | 5.3.x | I/O 密集型高并发场景 |
| **嵌入式服务器** | Tomcat | ★ 9.0.x | 默认，2.x 时代主流 |
| **嵌入式服务器** | Undertow | 2.0.x | MVC 高吞吐量备选 |
| **嵌入式服务器（响应式）** | Reactor Netty | 1.0.x | WebFlux 默认 |
| **JSON 序列化** | Jackson | ★ 2.13.x | 默认 |
| **API 文档** | springdoc-openapi | ★ 1.6.x | ⭐ 推荐，替代 Springfox |
| **API 文档** | ⚠️ Springfox 3.0 | 3.0.0 | 与 2.6+ 有兼容问题，不推荐 |
| **参数校验** | Hibernate Validator | ★ 6.x（javax.validation） | Boot 自动配置 |

```xml
<!-- API 文档（2.x 时代推荐 springdoc，替代 Springfox） -->
<dependency>
    <groupId>org.springdoc</groupId>
    <artifactId>springdoc-openapi-ui</artifactId>
    <version>1.6.15</version>
</dependency>
<!-- 访问：http://localhost:8080/swagger-ui.html -->
```

### 数据层

| 类别 | 选型 | 版本 | 说明 |
|------|------|------|------|
| **ORM** | Spring Data JPA + Hibernate | ★ 5.6.x | 首选 |
| **ORM** | MyBatis-Plus | ★ 3.5.x | MyBatis 增强，国内项目主流 |
| **ORM（响应式）** | R2DBC | 0.9.x | WebFlux 响应式数据库 |
| **连接池** | HikariCP | ★ 4.0.x | 默认，无需额外配置 |
| **数据库迁移** | Flyway | ★ 8.5.x | 推荐，SQL 版本管理 |
| **数据库迁移** | Liquibase | 4.4.x | 复杂变更场景 |
| **缓存（远程）** | Redis（Lettuce） | ★ 6.1.x | 2.x 默认 Lettuce 客户端 |
| **缓存（本地）** | Caffeine | ★ 2.9.x | 替代 Guava Cache，性能更好 |
| **缓存（本地）** | ⚠️ Guava Cache | — | 2.x 起 Caffeine 为首选 |
| **NoSQL** | MongoDB | 4.6.x | `spring-boot-starter-data-mongodb` |
| **搜索** | Elasticsearch | 7.17.x | `spring-boot-starter-data-elasticsearch` |

```yaml
# 2.x 推荐缓存配置（Caffeine 本地 + Redis 远程）
spring:
  cache:
    type: caffeine          # 本地缓存
    # type: redis           # 分布式缓存
    caffeine:
      spec: maximumSize=500,expireAfterWrite=300s
  redis:
    host: localhost
    port: 6379
    lettuce:
      pool:
        max-active: 8
        max-idle: 8
```

### 安全

| 类别 | 选型 | 版本 | 说明 |
|------|------|------|------|
| **认证授权** | Spring Security | ★ 5.7.x | `WebSecurityConfigurerAdapter`（2.7 废弃但可用） |
| **OAuth2 客户端** | Spring Security OAuth2 Client | ★ 内置 | 2.x 起内置，无需外部库 |
| **OAuth2 资源服务器** | Spring Security OAuth2 RS | ★ 内置 | JWT/Opaque Token |
| **OAuth2 授权服务器** | Spring Authorization Server | 0.3.x | 独立项目，替代 spring-security-oauth2 |
| **JWT** | jjwt | ★ 0.11.x | 主流 JWT 实现 |
| **JWT** | nimbus-jose-jwt | 9.x | Spring Security 内部使用 |

### 消息队列

| 类别 | 选型 | 版本 | 说明 |
|------|------|------|------|
| **消息队列** | Kafka | ★ 3.0.x | 大数据/高吞吐 首选 |
| **消息队列** | RabbitMQ | ★ 5.14.x | 企业集成、灵活路由 首选 |
| **消息队列** | RocketMQ | ★ 2.2.x | 国内项目，rocketmq-spring-boot-starter |
| **消息队列** | ActiveMQ Artemis | 2.x | 传统企业 JMS |

### 可观测

| 类别 | 选型 | 版本 | 说明 |
|------|------|------|------|
| **指标** | Micrometer | ★ 1.9.x | 默认内置 |
| **指标后端** | Prometheus + Grafana | ★ — | 主流监控方案 |
| **链路追踪** | Spring Cloud Sleuth + Zipkin | ★ 3.1.x | 2.x 时代追踪标配 |
| **链路追踪** | Spring Cloud Sleuth + Jaeger | — | OpenTracing 场景 |
| **日志** | Logback | ★ 1.2.x | 默认，`logback-spring.xml` |
| **日志收集** | ELK（Logstash） | — | 配合 logstash-logback-encoder |

```xml
<!-- 2.x 监控全家桶 -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-actuator</artifactId>
</dependency>
<dependency>
    <groupId>io.micrometer</groupId>
    <artifactId>micrometer-registry-prometheus</artifactId>
</dependency>
<!-- 链路追踪（2.x 时代） -->
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-sleuth</artifactId>
</dependency>
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-sleuth-zipkin</artifactId>
</dependency>
```

### 微服务（云原生）

| 类别 | 选型 | 版本 | 说明 |
|------|------|------|------|
| **微服务框架** | Spring Cloud | ★ 2021.0.x | 对应 Boot 2.6/2.7 |
| **服务发现** | Nacos / Eureka | ★ Nacos 2.x | 国内首选 Nacos |
| **配置中心** | Nacos Config / Spring Cloud Config | ★ Nacos 2.x | |
| **网关** | Spring Cloud Gateway | ★ 3.1.x | 基于 WebFlux |
| **负载均衡** | Spring Cloud LoadBalancer | ★ 内置 | 替代 Ribbon |
| **熔断降级** | Resilience4j | ★ 1.7.x | 替代 Hystrix |
| **RPC** | OpenFeign | ★ 3.1.x | 声明式 HTTP 客户端 |
| **HTTP 客户端** | RestTemplate | ★ 内置 | 同步，仍是主流 |
| **HTTP 客户端** | WebClient | 内置 | 响应式/非阻塞场景 |

### 测试

| 类别 | 选型 | 版本 | 说明 |
|------|------|------|------|
| **单元测试** | JUnit 5 | ★ 5.8.x | 2.2 起默认，`@ExtendWith(SpringExtension.class)` |
| **Mock** | Mockito | ★ 4.x | `@MockBean`, `@SpyBean` |
| **断言** | AssertJ | ★ 3.x | 流式断言，Boot 默认引入 |
| **集成测试** | Testcontainers | ★ 1.16.x | 真实容器测试 |
| **HTTP 测试** | MockMvc | ★ 内置 | MVC 层测试 |
| **HTTP 测试** | WebTestClient | 内置 | WebFlux 层测试 |

### 工具库

| 类别 | 选型 | 版本 | 说明 |
|------|------|------|------|
| **代码简化** | Lombok | ★ 1.18.x | 标配 |
| **对象映射** | MapStruct | ★ 1.5.x | 编译期生成，性能优 |
| **工具集** | Apache Commons Lang3 | ★ 3.12.x | 字符串/数组工具 |
| **工具集** | Guava | 31.x | Google 工具库 |
| **JSON 工具** | Jackson ObjectMapper | ★ 内置 | 避免再引 FastJSON（安全问题） |

---

## Spring Boot 3.x 时代（2022–2025）

> **推荐选择 3.3.x / 3.4.x / 3.5.x**（3.5.x 为最终版，OSS 至 2026-06）。
> 适用场景：**新项目主流选择**，云原生、容器化、可观测性完善。

### 运行环境

| 类别 | 选型 | 版本 | 说明 |
|------|------|------|------|
| **Spring Boot** | spring-boot | ★ 3.5.x | 最终版，长期支持 |
| **Spring Boot** | spring-boot | 3.3.x / 3.4.x | 活跃版本，均可选 |
| **Java** | JDK | ★ Java 21 LTS | ⭐ 强烈推荐，Virtual Threads 支持 |
| **Java** | JDK | Java 17 LTS | 最低要求，稳妥选择 |
| **构建工具** | Maven | ★ 3.6.3+ | 推荐 |
| **构建工具** | Gradle | ★ 8.x | 构建性能更好 |

### Web 层

| 类别 | 选型 | 版本 | 说明 |
|------|------|------|------|
| **Web 框架（同步）** | Spring MVC | ★ 6.1.x | 绝大多数业务场景 |
| **Web 框架（响应式）** | Spring WebFlux | 6.1.x | 高并发非阻塞场景 |
| **嵌入式服务器** | Tomcat | ★ 10.1.x | 默认，Jakarta EE 10 对齐 |
| **嵌入式服务器** | Jetty | 12.x | 内存敏感场景备选 |
| **嵌入式服务器（响应式）** | Reactor Netty | 1.1.x | WebFlux 默认 |
| **JSON 序列化** | Jackson | ★ 2.17.x | 默认 |
| **API 文档** | springdoc-openapi | ★ 2.x | `springdoc-openapi-starter-webmvc-ui` |
| **参数校验** | Hibernate Validator | ★ 8.x（jakarta.validation） | Boot 自动配置 |

```xml
<!-- API 文档（3.x 必须用 springdoc 2.x） -->
<dependency>
    <groupId>org.springdoc</groupId>
    <artifactId>springdoc-openapi-starter-webmvc-ui</artifactId>
    <version>2.6.0</version>
</dependency>
<!-- 访问：http://localhost:8080/swagger-ui/index.html -->
```

### 数据层

| 类别 | 选型 | 版本 | 说明 |
|------|------|------|------|
| **ORM** | Spring Data JPA + Hibernate | ★ 6.4.x | Jakarta Persistence 3.1 |
| **ORM** | MyBatis-Plus | ★ 3.5.x | 国内项目，需 3.5.3.1+ 以支持 Boot 3 |
| **JDBC** | JdbcClient（3.2+） | ★ 内置 | 流式 JDBC，推荐替代 JdbcTemplate |
| **JDBC** | JdbcTemplate | 内置 | 仍可用 |
| **ORM（响应式）** | R2DBC | 1.0.x | 响应式关系数据库 |
| **连接池** | HikariCP | ★ 5.1.x | 默认 |
| **数据库迁移** | Flyway | ★ 10.x | 推荐，Boot 3 对应 Flyway 9/10 |
| **数据库迁移** | Liquibase | 4.28.x | 复杂变更 |
| **缓存（远程）** | Redis（Lettuce） | ★ 6.3.x | 默认客户端 |
| **缓存（本地）** | Caffeine | ★ 3.x | 推荐本地缓存 |
| **NoSQL** | MongoDB | 5.1.x | `spring-boot-starter-data-mongodb` |
| **搜索** | Elasticsearch | 8.15.x | 新 Java Client（替代 HLRC） |

```yaml
# 3.x 推荐数据层配置
spring:
  datasource:
    url: jdbc:postgresql://localhost:5432/mydb
    username: ${DB_USER}
    password: ${DB_PASS}
    hikari:
      maximum-pool-size: 20
      minimum-idle: 5
  jpa:
    hibernate:
      ddl-auto: validate  # 生产用 validate，交给 Flyway 管理
    open-in-view: false  # 推荐关闭（避免 N+1 陷阱）
  flyway:
    enabled: true
    locations: classpath:db/migration
```

### 安全

| 类别 | 选型 | 版本 | 说明 |
|------|------|------|------|
| **认证授权** | Spring Security | ★ 6.3.x | `SecurityFilterChain` Bean 模式 |
| **OAuth2 客户端** | Spring Security OAuth2 Client | ★ 内置 | |
| **OAuth2 资源服务器** | Spring Security OAuth2 RS | ★ 内置 | JWT 验证 |
| **OAuth2 授权服务器** | Spring Authorization Server | ★ 1.3.x | 3.x 时代独立 starter |
| **JWT** | nimbus-jose-jwt | ★ 9.x | Spring Security 内部使用，直接用 |
| **密码加密** | BCryptPasswordEncoder | ★ 内置 | Spring Security 内置 |

```java
// 3.x 标准安全配置
@Configuration
@EnableWebSecurity
public class SecurityConfig {
    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        return http
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/public/**", "/actuator/health").permitAll()
                .requestMatchers("/admin/**").hasRole("ADMIN")
                .anyRequest().authenticated()
            )
            .oauth2ResourceServer(oauth2 -> oauth2.jwt(Customizer.withDefaults()))
            .sessionManagement(s -> s.sessionCreationPolicy(STATELESS))
            .build();
    }
}
```

### 消息队列

| 类别 | 选型 | 版本 | 说明 |
|------|------|------|------|
| **消息队列** | Kafka | ★ 3.7.x | 首选，高吞吐 |
| **消息队列** | RabbitMQ | ★ 5.21.x | 企业集成 |
| **消息队列** | RocketMQ | 2.3.x | 国内，需第三方 starter |
| **消息队列** | Pulsar | ★ 1.0.x | 3.2 起 Boot 原生支持 |

### 可观测（3.x 最大亮点）

| 类别 | 选型 | 版本 | 说明 |
|------|------|------|------|
| **指标** | Micrometer | ★ 1.13.x | 默认内置 |
| **链路追踪** | Micrometer Tracing + OTel | ★ 1.3.x | ⭐ 替代 Spring Cloud Sleuth |
| **链路追踪后端** | Zipkin / Jaeger | ★ — | 接 OTel Collector |
| **全链路观测** | OpenTelemetry Collector | ★ — | 统一采集指标+追踪+日志 |
| **指标后端** | Prometheus + Grafana | ★ — | 标准方案 |
| **日志** | Logback | ★ 1.5.x | 默认 |
| **结构化日志** | 内置 ECS/Logstash 格式（3.4+） | ★ — | `logging.structured.format.console=ecs` |
| **日志收集** | Loki + Grafana | ★ — | 云原生日志方案 |

```xml
<!-- 3.x 可观测全家桶 -->
<dependency>
    <groupId>io.micrometer</groupId>
    <artifactId>micrometer-tracing-bridge-otel</artifactId>
</dependency>
<dependency>
    <groupId>io.opentelemetry</groupId>
    <artifactId>opentelemetry-exporter-otlp</artifactId>
</dependency>
<dependency>
    <groupId>io.micrometer</groupId>
    <artifactId>micrometer-registry-prometheus</artifactId>
</dependency>
```

```yaml
management:
  tracing:
    sampling:
      probability: 0.1  # 10% 采样
  otlp:
    tracing:
      endpoint: http://otel-collector:4318/v1/traces
  endpoints:
    web:
      exposure:
        include: health, info, metrics, prometheus, startup, sbom
logging:
  structured:
    format:
      console: ecs  # 结构化 JSON 日志（3.4+）
```

### 微服务（云原生）

| 类别 | 选型 | 版本 | 说明 |
|------|------|------|------|
| **微服务框架** | Spring Cloud | ★ 2023.0.x | 对应 Boot 3.2/3.3 |
| **服务发现** | Nacos 2.x / Consul | ★ Nacos 2.x | |
| **配置中心** | Nacos Config | ★ — | |
| **网关** | Spring Cloud Gateway | ★ 4.x | 基于 WebFlux |
| **负载均衡** | Spring Cloud LoadBalancer | ★ 内置 | |
| **熔断降级** | Resilience4j | ★ 2.x | Boot 3 对应版本 |
| **RPC/HTTP** | HTTP Interface（内置，3.0+） | ★ 内置 | 替代 OpenFeign，无需额外依赖 |
| **HTTP 客户端** | RestClient（3.2+） | ★ 内置 | ⭐ 推荐，替代 RestTemplate |
| **HTTP 客户端** | WebClient | 内置 | 响应式场景 |

### 测试

| 类别 | 选型 | 版本 | 说明 |
|------|------|------|------|
| **单元测试** | JUnit 5 | ★ 5.11.x | 默认 |
| **Mock** | Mockito | ★ 5.x | |
| **断言** | AssertJ | ★ 3.x | |
| **集成测试** | Testcontainers（3.1 原生支持） | ★ 1.19.x | ⭐ `@ServiceConnection` 零配置 |
| **开发时容器** | Docker Compose（3.1 原生支持） | ★ 内置 | 开发环境标配 |
| **HTTP 测试** | MockMvc / WebTestClient | ★ 内置 | |

```java
// 3.x 推荐集成测试写法
@SpringBootTest
@Testcontainers
class UserServiceIT {
    @Container
    @ServiceConnection  // 无需 @DynamicPropertySource，自动配置
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16");

    @Container
    @ServiceConnection
    static GenericContainer<?> redis = new GenericContainer<>("redis:7")
        .withExposedPorts(6379);

    @Autowired
    private UserService userService;

    @Test
    void shouldPersistUser() { ... }
}
```

### 工具库

| 类别 | 选型 | 版本 | 说明 |
|------|------|------|------|
| **代码简化** | Lombok | ★ 1.18.30+ | 需 1.18.26+ 支持 Jakarta |
| **对象映射** | MapStruct | ★ 1.5.5+ | 需 1.5.3+ 支持 Jakarta |
| **工具集** | Apache Commons Lang3 | ★ 3.x | |
| **JSON 工具** | Jackson | ★ 内置 | |
| **API 文档** | springdoc-openapi 2.x | ★ 2.6.x | 必须用 2.x，1.x 不兼容 Boot 3 |

---

## Spring Boot 4.x 时代（2025–）

> **适用场景**：新建项目、技术前沿探索。
> 注意：4.0 于 2025-11 发布，当前（2026-03）为 4.0.3，生态逐步成熟。

### 运行环境

| 类别 | 选型 | 版本 | 说明 |
|------|------|------|------|
| **Spring Boot** | spring-boot | ★ 4.0.3 | 当前最新稳定版 |
| **Java** | JDK | ★ Java 21 LTS | ⭐ 推荐，Virtual Threads 成熟 |
| **Java** | JDK | Java 25 | 一等公民支持，尝鲜 |
| **Java** | JDK | Java 17 | 最低要求 |
| **构建工具** | Maven | ★ 3.9+ | 推荐 |
| **构建工具** | Gradle | ★ 8.14+ / 9.x | |

### Web 层

| 类别 | 选型 | 版本 | 说明 |
|------|------|------|------|
| **Web 框架（同步）** | Spring MVC | ★ 7.0.x | |
| **Web 框架（响应式）** | Spring WebFlux | 7.0.x | |
| **嵌入式服务器** | Tomcat | ★ 11.0.x | 默认，Jakarta Servlet 6.1 |
| **嵌入式服务器** | Jetty | 12.0.x | 备选 |
| **嵌入式服务器** | ⚠️ Undertow | — | **已移除**，迁移到 Tomcat/Jetty |
| **JSON 序列化** | Jackson | ★ 3.x | **重大升级**，注意行为变化 |
| **JSON 序列化** | Kotlin Serialization | ★ 1.6.x | 4.0 原生 starter，Kotlin 项目推荐 |
| **API 文档** | springdoc-openapi | ★ 待适配版本 | 关注 springdoc 3.x 进展 |
| **参数校验** | Hibernate Validator | ★ 8.x（jakarta.validation 3.1） | |

### 数据层

| 类别 | 选型 | 版本 | 说明 |
|------|------|------|------|
| **ORM** | Spring Data JPA + Hibernate | ★ 7.x | JPA 3.2，AOT Repository 支持 |
| **ORM** | MyBatis-Plus | 待适配 | 关注 Boot 4 兼容性 |
| **JDBC** | JdbcClient | ★ 内置 | 推荐，流式 API |
| **连接池** | HikariCP | ★ 5.1.x | 默认 |
| **数据库迁移** | Flyway | ★ 10.x | |
| **缓存** | Redis（Lettuce） | ★ 6.3.x | |
| **缓存（本地）** | Caffeine | ★ 3.x | |

### 安全

| 类别 | 选型 | 版本 | 说明 |
|------|------|------|------|
| **认证授权** | Spring Security | ★ 7.0.x | `SecurityFilterChain` 模式（无变化） |
| **OAuth2 授权服务器** | 内置于 Spring Security 7 | ★ — | 不再需要独立 starter |
| **JWT** | nimbus-jose-jwt | ★ 9.x | |

### 消息队列

| 类别 | 选型 | 版本 | 说明 |
|------|------|------|------|
| **消息队列** | Kafka | ★ 4.0.x | Spring Kafka 4.0 |
| **消息队列** | RabbitMQ | ★ 4.0.x | Spring AMQP 4.0 |
| **JMS** | JmsClient（新 API） | ★ 内置 | 4.0 新增，替代 JmsTemplate |

### 可观测

| 类别 | 选型 | 版本 | 说明 |
|------|------|------|------|
| **指标 + 追踪** | Micrometer 2.0 | ★ 2.0.x | 重大升级 |
| **全链路** | `spring-boot-starter-opentelemetry` | ★ 内置 | ⭐ 4.0 原生 OTel starter |
| **指标后端** | Prometheus + Grafana | ★ — | |
| **日志** | Logback | ★ 1.5.x | |
| **结构化日志** | 内置 ECS 格式 | ★ — | |

```xml
<!-- 4.x 可观测配置（更简洁） -->
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
        service.name: ${spring.application.name}
    tracing:
      endpoint: http://otel-collector:4318/v1/traces
```

### 4.x 特色选型（新特性充分利用）

| 类别 | 选型 | 说明 |
|------|------|------|
| **HTTP 客户端** | `@ImportHttpServices` | ★ 零配置声明式客户端（替代 OpenFeign） |
| **Bean 注册** | `BeanRegistrar` | ★ 动态/AOT 友好场景 |
| **弹性** | 框架内置 Retry/Timeout | ★ 无需引入 Spring Retry |
| **空安全** | JSpecify `@NullMarked` | 渐进式迁移，逐步启用 |
| **原生镜像** | GraalVM 25 + AOT Repositories | 启动秒级→毫秒级 |
| **API 版本** | 内置 `spring.mvc.apiversion` | 无需自定义拦截器 |

### 测试

| 类别 | 选型 | 版本 | 说明 |
|------|------|------|------|
| **单元测试** | JUnit 5 | ★ 5.11.x | |
| **Mock** | Mockito | ★ 5.x | |
| **HTTP 测试** | RestTestClient（新） | ★ 内置 | ⭐ 替代 MockMvc 繁琐 API |
| **集成测试** | Testcontainers | ★ 1.20.x | |

---

## 跨版本统一选型对比总表

### 核心选型决策

| 维度 | Boot 1.5.x | Boot 2.7.x | Boot 3.5.x | Boot 4.0.x |
|------|-----------|-----------|-----------|-----------|
| **Java** | Java 8 | Java 11/17 | ★ **Java 21** | ★ **Java 21** |
| **Web 服务器** | Tomcat 8.5 | Tomcat 9 | Tomcat 10.1 | Tomcat 11 |
| **ORM** | JPA/MyBatis | JPA/MyBatis-Plus | JPA/MyBatis-Plus | JPA(AOT) |
| **连接池** | ⚠️ Tomcat JDBC | ★ HikariCP | ★ HikariCP | ★ HikariCP |
| **缓存（本地）** | Ehcache 2 | ★ Caffeine | ★ Caffeine | ★ Caffeine |
| **缓存（远程）** | Jedis | ★ Lettuce | ★ Lettuce | ★ Lettuce |
| **API 文档** | Springfox 2.x | ★ springdoc 1.x | ★ springdoc 2.x | springdoc 3.x |
| **安全模型** | 继承 Adapter | 继承 Adapter | ★ FilterChain Bean | ★ FilterChain Bean |
| **链路追踪** | 无 | Spring Sleuth | ★ Micrometer Tracing | ★ OTel Starter |
| **HTTP 客户端** | RestTemplate | RestTemplate | ★ RestClient | ★ @ImportHttpServices |
| **测试框架** | JUnit 4 | ★ JUnit 5 | ★ JUnit 5 + Testcontainers | ★ JUnit 5 + RestTestClient |
| **数据库迁移** | Flyway 3 | ★ Flyway 8 | ★ Flyway 10 | ★ Flyway 10 |
| **消息队列** | Kafka/RabbitMQ | ★ Kafka/RabbitMQ | ★ Kafka/RabbitMQ | ★ Kafka/RabbitMQ |
| **JSON 序列化** | Jackson 2.8 | Jackson 2.13 | Jackson 2.17 | **Jackson 3.x** |

### 选型决策树

```
新项目选哪个版本？

├── 能用 Java 17+ ?
│   ├── YES → 选 Spring Boot 3.5.x（稳定，生态成熟）★推荐
│   │         或 4.0.x（最新，部分生态尚在适配）
│   └── NO  → 选 Spring Boot 2.7.x（最后 2.x 版本）
│
├── 需要 GraalVM Native Image？
│   └── 选 Boot 3.x+（正式支持）或 4.x（需 GraalVM 25+）
│
├── 需要 Virtual Threads（高并发阻塞 I/O）？
│   └── Boot 3.2+ + Java 21
│
├── 遗留系统维护？
│   ├── 运行 1.x → 升至 2.7.x 过渡，再升 3.x
│   └── 运行 2.x → 升至 2.7.18，再规划升 3.x
│
└── 追求最新技术？
    └── Boot 4.0.x + Java 21/25
```

### 2026 年推荐技术栈（新项目）

```yaml
# 推荐：Spring Boot 3.5.x 技术栈
Spring Boot:       3.5.x
Java:              21 LTS
Web:               Spring MVC + Tomcat 10.1
ORM:               Spring Data JPA 3.x + Hibernate 6.4
连接池:             HikariCP 5.1
数据库迁移:         Flyway 10
缓存:               Caffeine(本地) + Redis/Lettuce(分布式)
安全:               Spring Security 6.3 + OAuth2
消息:               Kafka 3.7 / RabbitMQ 5.21
链路追踪:           Micrometer Tracing + OTel Collector
指标:               Micrometer + Prometheus + Grafana
日志:               Logback + 结构化日志(ECS)
HTTP客户端:         RestClient + HTTP Interface
API文档:            springdoc-openapi 2.x
测试:               JUnit 5 + Mockito 5 + Testcontainers
代码工具:           Lombok + MapStruct
构建:               Maven 3.9+ / Gradle 8.x
容器:               Docker + Kubernetes
```
