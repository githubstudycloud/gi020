# Spring Boot 版本总览与时间线

## 发布时间线

```
2014 ─── 1.0 GA (Apr)  ← 诞生
2014 ─── 1.1
2015 ─── 1.2  (@SpringBootApplication)
2015 ─── 1.3  (DevTools)
2017 ─── 1.4
2017 ─── 1.5  (Kafka/LDAP) ← 1.x 最终版

2018 ─── 2.0  (Reactive, Micrometer, Java 8+) ← 重大变革
2018 ─── 2.1  (Java 11, 懒加载)
2019 ─── 2.2  (JUnit 5 默认, proxyBeanMethods)
2020 ─── 2.3  (Docker 镜像, 优雅关机)
2020 ─── 2.4  (新配置处理, Spring 5.3)
2021 ─── 2.5
2021 ─── 2.6  (禁止循环引用)
2022 ─── 2.7  (GraphQL, @AutoConfiguration) ← 2.x 最终版

2022 ─── 3.0  (Jakarta EE, Java 17+, GraalVM) ← 重大变革
2023 ─── 3.1  (Testcontainers, SSL Bundles)
2023 ─── 3.2  (Virtual Threads, RestClient)
2024 ─── 3.3  (CDS, SBOM)
2024 ─── 3.4  (结构化日志)
2025 ─── 3.5  ← 3.x 最终版

2025 ─── 4.0  (模块化, JSpecify, Spring 7) ← 重大变革
2026 ─── 4.1  (开发中)
```

## 版本支持状态（截至 2026-03）

| 版本线 | 最新补丁 | OSS 支持截止 | 商业支持截止 | 状态 |
|--------|---------|------------|------------|------|
| 1.5.x | 1.5.22 | 2019-08 | 2019-08 | EOL |
| 2.7.x | 2.7.18 | 2023-11 | 2029-06 (延长) | 商业支持 |
| 3.0.x | 3.0.13 | 2023-12 | 2024-12 | EOL |
| 3.1.x | 3.1.12 | 2024-06 | 2025-06 | EOL |
| 3.2.x | 3.2.12 | 2024-12 | 2025-12 | EOL |
| 3.3.x | 3.3.13 | 2025-06 | 2026-06 | 活跃 |
| 3.4.x | 3.4.13 | 2025-12 | 2026-12 | 活跃 |
| 3.5.x | 3.5.x  | 2026-06 | 2032-06 (延长) | 活跃 |
| 4.0.x | 4.0.3  | 2026-12 | 2027-12 | 活跃 |
| 4.1   | —      | —        | —        | 预览 |

> 发布节奏：每 6 个月发布新版本（5 月和 11 月）

## 各大版本核心依赖一览

| 维度 | 1.5.x | 2.0.x | 2.7.x | 3.0.x | 3.5.x | 4.0.x |
|------|-------|-------|-------|-------|-------|-------|
| Spring Framework | 4.3 | 5.0 | 5.3 | 6.0 | 6.2 | 7.0 |
| Java 最低版本 | Java 6 | Java 8 | Java 8 | Java 17 | Java 17 | Java 17 |
| EE 命名空间 | javax.* | javax.* | javax.* | jakarta.* | jakarta.* | jakarta.* |
| Tomcat | 8.5 | 8.5 | 9.0 | 10.1 | 10.1 | 11.0 |
| Hibernate | 5.0 | 5.2 | 5.6 | 6.1 | 6.4 | 7.x |
| Jackson | 2.8 | 2.9 | 2.13 | 2.14 | 2.17 | 3.x |
| JUnit | 4.x | 5 (2.2+) | 5.8 | 5.9 | 5.11 | 5.x |
| Micrometer | 无 | 1.0 | 1.9 | 1.10 | 1.13 | 2.0 |
| Kotlin | 无 | 1.2 | 1.6 | 1.7 | 1.9 | 2.2+ |
| GraalVM Native | 无 | 无 | 无 | 正式支持 | 正式支持 | GraalVM 25+ |
| 默认连接池 | Tomcat JDBC | HikariCP | HikariCP | HikariCP | HikariCP | HikariCP |

## 功能里程碑

| 功能 | 首次引入版本 |
|------|------------|
| `@SpringBootApplication` | 1.2 |
| 嵌入式 Servlet 容器 | 1.0 |
| Spring Boot Actuator | 1.0 |
| Spring Boot DevTools | 1.3 |
| Spring WebFlux (响应式) | 2.0 |
| Micrometer 指标 | 2.0 |
| HikariCP 默认连接池 | 2.0 |
| Kotlin 一等公民支持 | 2.0 |
| JUnit 5 默认 | 2.2 |
| Docker 镜像构建 | 2.3 |
| 优雅关机 | 2.3 |
| Kubernetes 探针 | 2.3 |
| `@AutoConfiguration` 注解 | 2.7 |
| `.imports` 注册文件 | 2.7 |
| Jakarta EE 命名空间 | 3.0 |
| GraalVM Native Image (正式) | 3.0 |
| Micrometer Tracing | 3.0 |
| Testcontainers 集成 | 3.1 |
| Docker Compose 集成 | 3.1 |
| SSL Bundles | 3.1 |
| Virtual Threads (Loom) | 3.2 |
| RestClient | 3.2 |
| JdbcClient | 3.2 |
| CDS 支持 | 3.3 |
| SBOM 端点 | 3.3 |
| 结构化日志 | 3.4 |
| 完全模块化 autoconfigure | 4.0 |
| JSpecify 空安全 | 4.0 |
| BeanRegistrar | 4.0 |
| `@ImportHttpServices` | 4.0 |
| Micrometer 2.0 | 4.0 |
| Jackson 3.x | 4.0 |
