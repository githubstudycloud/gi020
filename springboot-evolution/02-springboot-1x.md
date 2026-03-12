# Spring Boot 1.x 详解 (2014–2019)

## 概述

Spring Boot 1.x 是整个 Spring Boot 项目的奠基阶段，核心理念是"约定优于配置"（Convention over Configuration）。1.0 GA 于 2014 年 4 月 1 日发布时，已积累了 1,720 次提交、54 位贡献者。

> **生命周期**: 2014-04 ~ 2019-08（全线 EOL）
> **版本后缀**: `.RELEASE`（如 `1.0.0.RELEASE`，区别于 2.x 起的无后缀形式）

## 各小版本时间线

| 版本 | 发布时间 | 主要亮点 |
|------|---------|---------|
| 1.0 | 2014-04 | 第一个 GA 版本，自动配置基础 |
| 1.1 | 2014-06 | Elasticsearch/Solr 自动配置，模板引擎支持 |
| 1.2 | 2015-03 | Servlet 3.1、Tomcat 8、Jetty 9、**`@SpringBootApplication`** |
| 1.3 | 2015-12 | **DevTools**、缓存自动配置、可执行 JAR |
| 1.4 | 2017-01 | Spring 4.3、Couchbase/Neo4j 支持、失败分析器 |
| 1.5 | 2017-02 | **Kafka/LDAP 自动配置**、Actuator loggers 端点（最终版本） |

## 核心组件版本（以 1.5.x 为准）

| 组件 | 版本 |
|------|------|
| Spring Framework | 4.3.x |
| Java 最低要求 | Java 6（1.0–1.3），推荐 Java 7+，支持 Java 8 |
| 嵌入式 Tomcat | 8.5.x（默认） |
| 嵌入式 Jetty | 9.x |
| 嵌入式 Undertow | 1.x |
| Hibernate | 5.0.x |
| Jackson | 2.8.x |
| Logback | 1.1.x |
| JUnit | 4.x |
| Spring Security | 4.x |
| Flyway | 3.x |

## 核心特性详解

### 1. 自动配置（Auto-Configuration）

Spring Boot 最核心的特性，根据类路径内容自动配置 Spring 应用上下文。

```java
// 1.0 写法（三个注解）
@Configuration
@EnableAutoConfiguration
@ComponentScan
public class Application {
    public static void main(String[] args) {
        SpringApplication.run(Application.class, args);
    }
}

// 1.2 起可用的组合注解
@SpringBootApplication  // = @Configuration + @EnableAutoConfiguration + @ComponentScan
public class Application {
    public static void main(String[] args) {
        SpringApplication.run(Application.class, args);
    }
}
```

自动配置原理：
- `@EnableAutoConfiguration` 通过 `spring.factories` 加载 `AutoConfiguration` 类列表
- 每个 AutoConfiguration 类通过 `@Conditional` 族注解按条件生效
- `META-INF/spring.factories` 中的 `org.springframework.boot.autoconfigure.EnableAutoConfiguration` 键

### 2. Starter 依赖

预打包的依赖集合，无需手动管理版本兼容性：

| Starter | 用途 |
|---------|------|
| `spring-boot-starter-web` | Spring MVC + Tomcat |
| `spring-boot-starter-data-jpa` | Hibernate + Spring Data JPA |
| `spring-boot-starter-security` | Spring Security |
| `spring-boot-starter-test` | JUnit + Mockito + Spring Test |
| `spring-boot-starter-actuator` | 监控端点 |
| `spring-boot-starter-data-redis` | Redis |
| `spring-boot-starter-data-mongodb` | MongoDB |
| `spring-boot-starter-thymeleaf` | Thymeleaf 模板 |
| `spring-boot-starter-logging` | Logback（默认） |

### 3. 嵌入式服务器

无需外部部署，直接 `java -jar` 运行：

```xml
<!-- 切换为 Jetty（排除默认 Tomcat） -->
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
    <artifactId>spring-boot-starter-jetty</artifactId>
</dependency>
```

### 4. Spring Boot Actuator（1.x）

监控端点直接暴露在根路径：

| 端点 | URL | 说明 |
|------|-----|------|
| 健康检查 | `/health` | 应用健康状态（默认公开） |
| 应用信息 | `/info` | 应用信息（默认公开） |
| 指标 | `/metrics` | 计数器/计量值（敏感） |
| 环境 | `/env` | 配置属性（敏感） |
| 日志 | `/loggers` | 运行时日志级别（1.5+）|
| 追踪 | `/trace` | HTTP 请求历史（敏感） |
| 线程 | `/dump` | 线程转储（敏感） |
| 关机 | `/shutdown` | 关闭应用（默认禁用） |

安全配置（1.x 特有）：
```yaml
# application.yml
management:
  security:
    enabled: true  # Actuator 独立安全配置

# 开启 shutdown 端点
endpoints:
  shutdown:
    enabled: true
```

### 5. DevTools（1.3 引入）

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-devtools</artifactId>
    <optional>true</optional>
</dependency>
```

功能：
- **自动重启**：类路径变化时自动重启（使用双类加载器，比冷启动快）
- **LiveReload**：浏览器自动刷新
- **开发属性默认值**：如 `spring.thymeleaf.cache=false`

### 6. Spring Security（1.x）

```java
// 1.x 安全配置方式
@Configuration
public class SecurityConfig extends WebSecurityConfigurerAdapter {
    @Override
    protected void configure(HttpSecurity http) throws Exception {
        http
            .authorizeRequests()
                .antMatchers("/public/**").permitAll()
                .anyRequest().authenticated()
            .and()
            .formLogin();
    }
}
```

特点：
- 基于 `WebSecurityConfigurerAdapter`（继承重写）
- CSRF 保护默认开启
- Actuator 有独立的安全配置
- OAuth2 通过外部库 `spring-security-oauth2` 实现

### 7. 数据访问（1.x）

```yaml
# 1.x 默认连接池：Tomcat JDBC Pool
spring:
  datasource:
    url: jdbc:mysql://localhost:3306/mydb
    username: root
    password: secret
  jpa:
    hibernate:
      ddl-auto: update
      # 1.x 默认 use-new-id-generator-mappings=false
      use-new-id-generator-mappings: false
```

## 1.x 版本演进细节

### 1.2：`@SpringBootApplication` 的诞生

```java
// 在 1.2 之前需要写三个注解
@Configuration
@EnableAutoConfiguration
@ComponentScan(basePackages = "com.example")
public class App { ... }

// 1.2 起，一个注解搞定
@SpringBootApplication
public class App { ... }
```

### 1.3：可执行 JAR

1.3 引入了将 Spring Boot 应用打包为可执行 Unix 服务的能力：

```bash
# 直接作为服务运行（Linux/macOS）
chmod +x myapp.jar
./myapp.jar start
./myapp.jar stop
./myapp.jar status
```

### 1.4：启动失败分析

引入人性化的启动失败信息：

```
***************************
APPLICATION FAILED TO START
***************************

Description:

Embedded servlet container failed to start. Port 8080 was already in use.

Action:

Identify and stop the process that's listening on port 8080 or configure this
application to listen on another port.
```

### 1.5：Kafka 自动配置

```yaml
spring:
  kafka:
    bootstrap-servers: localhost:9092
    consumer:
      group-id: myGroup
      auto-offset-reset: earliest
```

```java
@KafkaListener(topics = "myTopic", groupId = "myGroup")
public void listen(String message) {
    System.out.println("Received: " + message);
}
```

## 配置文件结构（1.x）

```
src/main/resources/
├── application.properties  # 主配置
├── application-dev.properties   # dev profile
├── application-prod.properties  # prod profile
└── application.yml         # YAML 格式（也支持）
```

```yaml
# application.yml
server:
  port: 8080

spring:
  datasource:
    url: jdbc:h2:mem:testdb
  jpa:
    show-sql: true

management:
  security:
    enabled: false  # 禁用 Actuator 安全（开发环境）
```

## 依赖管理方式

```xml
<!-- Maven：继承 starter-parent -->
<parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>1.5.22.RELEASE</version>
</parent>

<!-- 或导入 BOM（不继承时使用） -->
<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-dependencies</artifactId>
            <version>1.5.22.RELEASE</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>
    </dependencies>
</dependencyManagement>
```

## 1.x 主要废弃/移除

| 特性 | 状态 | 说明 |
|------|------|------|
| CRaSH 远程 Shell | 1.5 废弃，2.0 移除 | SSH/Telnet 进入应用 Shell |
| `/trace` 端点 | 后续版本改名 | HTTP 请求历史记录 |
| `spring.data.neo4j.*` | 属性命名空间变化 | 小版本间有调整 |

## 与 2.x 对比速览

| 方面 | Spring Boot 1.x | Spring Boot 2.x |
|------|----------------|----------------|
| Java 最低 | Java 6 | Java 8 |
| Spring Framework | 4.x | 5.x |
| Actuator 路径 | `/health` | `/actuator/health` |
| 默认连接池 | Tomcat JDBC | HikariCP |
| 指标系统 | 简单计数器 | Micrometer（多维度） |
| 响应式支持 | 无 | Spring WebFlux |
| Kotlin | 无 | 一等公民 |
