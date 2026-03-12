# Spring Boot 3.x 微服务三件套

> Spring Boot 3.3.x + Spring Cloud 2023.0.x + Spring Cloud Alibaba 2023.0.3
> 要求 **Java 17+**，全面迁移 **Jakarta EE** 命名空间

## 技术栈

| 组件 | 技术选型 | 版本 |
|------|---------|------|
| 注册中心 | Alibaba Nacos | 2.3.x |
| 配置中心 | Nacos Config | 2.3.x |
| 网关 | Spring Cloud Gateway | 4.1.x |
| 熔断 | Resilience4j | 2.1.x |
| 负载均衡 | Spring Cloud LoadBalancer | 4.1.x |
| 服务调用 | OpenFeign | 4.1.x |
| 链路追踪 | Micrometer Tracing + Zipkin | 1.3.x |
| 指标 | Micrometer + Prometheus | 1.12.x |

## 版本对应

```
Spring Boot:           3.3.5
Spring Cloud:          2023.0.3 (Leyton)
Spring Cloud Alibaba:  2023.0.3.2
Nacos Server:          2.3.2
Java:                  17+ (推荐 21，支持虚拟线程)
```

## 子目录

- [注册中心 (Nacos 2.3.x Discovery)](./registry/README.md)
- [配置中心 (Nacos 2.3.x Config)](./config-center/README.md)
- [网关 (Spring Cloud Gateway 4.1.x)](./gateway/README.md)

## 与 2.x 核心差异

| 对比项 | Spring Boot 2.x | Spring Boot 3.x |
|--------|----------------|----------------|
| Java 最低 | 8 | **17**（LTS）|
| 命名空间 | javax.* | **jakarta.***（所有注解/Servlet API）|
| 链路追踪 | Spring Cloud Sleuth（已停维）| **Micrometer Tracing** |
| 原生镜像 | 实验性 | **GraalVM Native 正式支持** |
| 虚拟线程 | 无 | **Java 21 + spring.threads.virtual.enabled** |
| 配置导入 | bootstrap.yml | **spring.config.import**（推荐）|
| Record 绑定 | 不支持 | **@ConfigurationProperties + Record** |
| 安全 | Spring Security 5.x | **Spring Security 6.x**（大量 API 变化）|

## 迁移注意事项

### javax → jakarta 迁移
```bash
# 使用 OpenRewrite 自动迁移
./mvnw -U org.openrewrite.maven:rewrite-maven-plugin:run \
  -Drewrite.recipeArtifactCoordinates=org.openrewrite.recipe:rewrite-spring:LATEST \
  -Drewrite.activeRecipes=org.openrewrite.java.spring.boot3.UpgradeSpringBoot_3_3
```

### Spring Cloud Sleuth 迁移
```xml
<!-- 移除 -->
<dependency>spring-cloud-starter-sleuth</dependency>

<!-- 添加 -->
<dependency>micrometer-tracing-bridge-brave</dependency>
<dependency>zipkin-reporter-brave</dependency>
```

## 快速启动顺序

1. 启动 Nacos Server 2.3.x（注意开启鉴权）
2. 启动 Redis（Gateway 限流）
3. 启动 Zipkin（链路追踪，可选）
4. 启动业务微服务
5. 启动 Spring Cloud Gateway
