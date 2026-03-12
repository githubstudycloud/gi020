# Spring Boot 核心组件版本矩阵

## 核心框架

| 组件 | Boot 1.5.x | Boot 2.0.x | Boot 2.3.x | Boot 2.7.x | Boot 3.0.x | Boot 3.2.x | Boot 3.5.x | Boot 4.0.x |
|------|-----------|-----------|-----------|-----------|-----------|-----------|-----------|-----------|
| **Spring Framework** | 4.3.x | 5.0.x | 5.2.x | 5.3.x | 6.0.x | 6.1.x | 6.2.x | 7.0.x |
| **Java 最低** | Java 6 | Java 8 | Java 8 | Java 8 | Java 17 | Java 17 | Java 17 | Java 17 |
| **Java 最高测试** | Java 8 | Java 9 | Java 14 | Java 18 | Java 19 | Java 21 | Java 24 | Java 25 |
| **Spring Security** | 4.x | 5.0.x | 5.2.x | 5.7.x | 6.0.x | 6.2.x | 6.3.x | 7.0.x |
| **Spring Data** | Ingalls | Kay | Moore | 2021.2 | 2022.0 | 2023.1 | 2024.0 | 2026.0 |
| **Spring AMQP** | 1.x | 2.0.x | 2.2.x | 2.4.x | 3.0.x | 3.1.x | 3.1.x | 4.0.x |
| **Spring Kafka** | 1.x | 2.1.x | 2.5.x | 2.8.x | 3.0.x | 3.1.x | 3.2.x | 4.0.x |
| **Spring Batch** | 3.x | 4.0.x | 4.2.x | 4.3.x | 5.0.x | 5.1.x | 5.1.x | 6.0.x |
| **Spring GraphQL** | — | — | — | 1.0.x | 1.1.x | 1.2.x | 1.3.x | 2.0.x |

## Web 服务器

| 组件 | Boot 1.5.x | Boot 2.0.x | Boot 2.3.x | Boot 2.7.x | Boot 3.0.x | Boot 3.2.x | Boot 3.5.x | Boot 4.0.x |
|------|-----------|-----------|-----------|-----------|-----------|-----------|-----------|-----------|
| **Tomcat** | 8.5.x | 8.5.x | 9.0.x | 9.0.x | 10.1.x | 10.1.x | 10.1.x | **11.0.x** |
| **Jetty** | 9.x | 9.4.x | 9.4.x | 9.4.x/10 | 11.x | 12.x | 12.x | 12.0.x |
| **Undertow** | 1.x | 1.4.x | 2.1.x | 2.0.x | 2.3.x | 2.3.x | 2.3.x | **已移除** |
| **Netty (Reactive)** | — | 4.1.x | 4.1.x | 4.1.x | 4.1.x | 4.1.x | 4.1.x | 4.1.x |

## 数据访问

| 组件 | Boot 1.5.x | Boot 2.0.x | Boot 2.3.x | Boot 2.7.x | Boot 3.0.x | Boot 3.2.x | Boot 3.5.x | Boot 4.0.x |
|------|-----------|-----------|-----------|-----------|-----------|-----------|-----------|-----------|
| **Hibernate** | 5.0.x | 5.2.x | 5.4.x | 5.6.x | 6.1.x | 6.3.x | 6.4.x | **7.x** |
| **默认连接池** | Tomcat JDBC | HikariCP | HikariCP | HikariCP | HikariCP | HikariCP | HikariCP | HikariCP |
| **HikariCP** | 2.x | 3.0.x | 3.4.x | 4.0.x | 5.0.x | 5.1.x | 5.1.x | 5.1.x |
| **Flyway** | 3.x | 5.0.x | 6.5.x | 8.5.x | 9.x | 9.x | 10.x | 10.x |
| **Liquibase** | 3.x | 3.5.x | 3.8.x | 4.4.x | 4.17.x | 4.24.x | 4.28.x | 4.28.x |
| **MyBatis** | 1.x | 2.0.x | 2.1.x | 2.2.x | 3.0.x | 3.0.x | 3.0.x | 3.0.x |
| **R2DBC** | — | — | — | 0.9.x | 1.0.x | 1.0.x | 1.0.x | 1.0.x |
| **Redis (Lettuce)** | 4.x | 5.0.x | 5.3.x | 6.1.x | 6.2.x | 6.3.x | 6.3.x | 6.3.x |
| **MongoDB Driver** | 3.x | 3.6.x | 4.0.x | 4.6.x | 4.8.x | 5.0.x | 5.1.x | 5.1.x |
| **Elasticsearch** | 5.x | 5.5.x | 7.6.x | 7.17.x | 8.5.x | 8.11.x | 8.15.x | 8.15.x |

## 序列化 & 消息

| 组件 | Boot 1.5.x | Boot 2.0.x | Boot 2.3.x | Boot 2.7.x | Boot 3.0.x | Boot 3.2.x | Boot 3.5.x | Boot 4.0.x |
|------|-----------|-----------|-----------|-----------|-----------|-----------|-----------|-----------|
| **Jackson** | 2.8.x | 2.9.x | 2.11.x | 2.13.x | 2.14.x | 2.16.x | 2.17.x | **3.x** |
| **Gson** | 2.7.x | 2.8.x | 2.8.x | 2.9.x | 2.10.x | 2.10.x | 2.11.x | 2.11.x |
| **Kafka Client** | 0.10.x | 1.0.x | 2.5.x | 3.0.x | 3.3.x | 3.6.x | 3.7.x | 3.7.x |
| **RabbitMQ Client** | 4.x | 5.0.x | 5.9.x | 5.14.x | 5.16.x | 5.20.x | 5.21.x | 5.21.x |
| **ActiveMQ** | 5.14.x | 5.15.x | 5.15.x | 5.17.x | 5.18.x | 5.18.x | 6.0.x | 6.0.x |

## 监控 & 可观测

| 组件 | Boot 1.5.x | Boot 2.0.x | Boot 2.3.x | Boot 2.7.x | Boot 3.0.x | Boot 3.2.x | Boot 3.5.x | Boot 4.0.x |
|------|-----------|-----------|-----------|-----------|-----------|-----------|-----------|-----------|
| **Micrometer** | — | 1.0.x | 1.5.x | 1.9.x | 1.10.x | 1.12.x | 1.13.x | **2.0.x** |
| **Micrometer Tracing** | — | — | — | — | 1.0.x | 1.2.x | 1.3.x | 2.0.x |
| **Prometheus Client** | — | 0.x | 0.x | 0.x | 0.x | 0.x | 1.x | 1.x |
| **Zipkin Reporter** | — | 2.x | 2.x | 2.x | 2.x | 3.x | 3.x | 3.x |
| **Logback** | 1.1.x | 1.2.x | 1.2.x | 1.2.x | 1.4.x | 1.4.x | 1.5.x | 1.5.x |
| **Log4j2** | 2.7.x | 2.10.x | 2.13.x | 2.17.x | 2.19.x | 2.21.x | 2.23.x | 2.23.x |
| **SLF4J** | 1.7.x | 1.7.x | 1.7.x | 1.7.x | 2.0.x | 2.0.x | 2.0.x | 2.0.x |

## 测试

| 组件 | Boot 1.5.x | Boot 2.0.x | Boot 2.2.x | Boot 2.7.x | Boot 3.0.x | Boot 3.2.x | Boot 4.0.x |
|------|-----------|-----------|-----------|-----------|-----------|-----------|-----------|
| **JUnit** | 4.x | 4.x/5.x | **5.x (默认)** | 5.8.x | 5.9.x | 5.10.x | 5.11.x |
| **Mockito** | 1.x | 2.x | 3.x | 4.x | 5.x | 5.x | 5.x |
| **AssertJ** | 2.x | 3.x | 3.x | 3.x | 3.x | 3.x | 3.x |
| **Testcontainers** | — | 1.x | 1.x | 1.16.x | 1.17.x | 1.19.x | 1.20.x |
| **JSONassert** | 1.x | 1.x | 1.5.x | 1.5.x | 1.5.x | 1.5.x | 1.5.x |
| **HTMLUnit** | 2.x | 2.x | 2.x | 2.x | 2.x | 3.x | 3.x |

## Kotlin

| 特性 | Boot 1.5.x | Boot 2.0.x | Boot 2.3.x | Boot 2.7.x | Boot 3.0.x | Boot 4.0.x |
|------|-----------|-----------|-----------|-----------|-----------|-----------|
| **Kotlin 版本** | — | 1.2.x | 1.3.x | 1.6.x | 1.7.x | 2.2.x |
| **Kotlin Coroutines** | — | — | 1.3.x | 1.6.x | 1.6.x | 1.9.x |
| **kotlinx.serialization** | — | — | — | — | — | 1.6.x (4.0) |
| `runApplication` 函数 | — | ✓ | ✓ | ✓ | ✓ | ✓ |
| suspend 路由方法 | — | — | ✓ | ✓ | ✓ | ✓ |
| BeanRegistrarDsl | — | — | — | — | — | ✓ (4.0) |

## 构建工具

| 特性 | Boot 1.5.x | Boot 2.0.x | Boot 2.3.x | Boot 2.7.x | Boot 3.0.x | Boot 4.0.x |
|------|-----------|-----------|-----------|-----------|-----------|-----------|
| **Maven** | 3.2+ | 3.2+ | 3.3+ | 3.5+ | 3.5+ | 3.6.3+ |
| **Gradle** | 2.9–3.x | 4.x | 6.x | 6.8+ | 7.x+ | 8.14+ / 9.x |
| Docker 镜像构建 | — | — | ✓ (2.3) | ✓ | ✓ | ✓ |
| 分层 JAR | — | — | ✓ (2.3) | ✓ | ✓ | ✓ |
| GraalVM 原生编译 | — | — | — | ✓ (实验) | ✓ (正式) | ✓ (GraalVM 25+) |
| CDS 支持 | — | — | — | — | ✓ (3.3) | ✓ |
| CRaC 支持 | — | — | — | — | ✓ (3.2) | ✓ |

## 功能特性演进

| 功能 | 引入版本 | 备注 |
|------|---------|------|
| 自动配置 | 1.0 | 核心特性 |
| Starter 依赖 | 1.0 | 核心特性 |
| 嵌入式服务器 | 1.0 | 核心特性 |
| Actuator | 1.0 | 监控端点 |
| `@SpringBootApplication` | 1.2 | 组合注解 |
| DevTools | 1.3 | 开发者工具 |
| Kotlin 支持 | 2.0 | 一等公民 |
| Spring WebFlux | 2.0 | 响应式 Web |
| Micrometer 指标 | 2.0 | 替代内置计数器 |
| HikariCP 默认 | 2.0 | 替代 Tomcat JDBC |
| JUnit 5 默认 | 2.2 | 替代 JUnit 4 |
| proxyBeanMethods | 2.2 | 性能优化选项 |
| Docker 镜像构建 | 2.3 | OCI/Buildpacks |
| 优雅关机 | 2.3 | `server.shutdown=graceful` |
| K8s 健康探针 | 2.3 | Liveness/Readiness |
| 新配置导入 | 2.4 | `spring.config.import` |
| 禁止循环引用 | 2.6 | 默认行为变更 |
| `@AutoConfiguration` | 2.7 | 专用注解 |
| `.imports` 注册 | 2.7 | 替代 spring.factories |
| Spring GraphQL | 2.7 | 图查询支持 |
| Jakarta EE | 3.0 | javax→jakarta |
| GraalVM 正式 | 3.0 | 原生镜像 |
| Micrometer Tracing | 3.0 | 分布式追踪 |
| HTTP 接口客户端 | 3.0 | 声明式 HTTP 客户端 |
| Testcontainers 集成 | 3.1 | `@ServiceConnection` |
| Docker Compose 集成 | 3.1 | 开发时容器管理 |
| SSL Bundles | 3.1 | 统一 SSL 配置 |
| Virtual Threads | 3.2 | Project Loom (Java 21) |
| RestClient | 3.2 | 新阻塞 HTTP 客户端 |
| JdbcClient | 3.2 | 新 JDBC 流式 API |
| CRaC | 3.2 | 毫秒级启动 |
| CDS | 3.3 | 类数据共享 |
| SBOM 端点 | 3.3 | 软件物料清单 |
| 结构化日志 | 3.4 | ECS/GELF/Logstash |
| 完全模块化 | 4.0 | autoconfigure 拆分 |
| JSpecify 空安全 | 4.0 | 编译期空检查 |
| BeanRegistrar | 4.0 | AOT 友好注册 |
| `@ImportHttpServices` | 4.0 | 零配置 HTTP 客户端 |
| API 版本控制 | 4.0 | 内置版本路由 |
| Micrometer 2.0 | 4.0 | 指标系统升级 |
| Jackson 3.x | 4.0 | 重大序列化升级 |
| Hibernate 7.x | 4.0 | ORM 重大升级 |
| OpenTelemetry Starter | 4.0 | 内置 OTel 支持 |
| RestTestClient | 4.0 | MockMvc 测试客户端 |
