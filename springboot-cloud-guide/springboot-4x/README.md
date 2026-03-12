# Spring Boot 4.x 微服务三件套（预览）

> Spring Boot 4.0.x + Spring Framework 7 + Spring Cloud 2025.0.x
> 要求 **Java 21+**，GraalVM Native 成熟，Virtual Threads 优先，Kubernetes 原生

---

> **版本状态**：Spring Boot 4.0 处于 Milestone 阶段（预计 2026 年 GA），
> 本文基于官方路线图和已发布的 Milestone 版本整理，生产环境请以正式 GA 版为准。

## 技术栈

| 组件 | 技术选型 | 版本 |
|------|---------|------|
| 注册中心 | Nacos 3.x / K8s Service | 3.0.x |
| 配置中心 | Nacos 3.x Config / K8s ConfigMap | 3.0.x |
| 网关 | Spring Cloud Gateway | 5.x |
| 熔断 | Resilience4j | 2.x |
| 负载均衡 | Spring Cloud LoadBalancer | 5.x |
| 服务调用 | OpenFeign | 5.x |
| 链路追踪 | Micrometer Tracing + OpenTelemetry | 1.4.x |
| 指标 | Micrometer + Prometheus | 1.13.x |

## 版本对应

```
Spring Boot:           4.0.0-M3
Spring Cloud:          2025.0.0 (Moorgate)
Spring Cloud Alibaba:  2025.0.0.0
Nacos Server:          3.0.x（或 2.3.x 兼容）
Java:                  21（必须，LTS）
GraalVM:               21+（原生镜像）
```

## 子目录

- [注册中心 (Nacos 3.x / K8s Service)](./registry/README.md)
- [配置中心 (Nacos / K8s ConfigMap)](./config-center/README.md)
- [网关 (Spring Cloud Gateway 5.x)](./gateway/README.md)

## 核心演进亮点

### 1. Java 21 全面拥抱
```java
// Virtual Threads（一键开启）
spring.threads.virtual.enabled=true

// Record + Sealed Classes（类型安全配置/DTO）
sealed interface Result<T> permits Result.Ok, Result.Err { ... }
record OrderProperties(int timeout, String currency) {}

// Pattern Matching（switch 表达式）
switch (response) {
    case Success s -> process(s.data());
    case Failure f -> handleError(f.message());
}
```

### 2. GraalVM Native Image 成熟
| 指标 | JVM 模式 | Native 模式（4.x）|
|------|---------|--------------|
| 启动时间 | 2-5 秒 | **< 100ms** |
| 内存占用 | 300MB+ | **< 100MB** |
| 构建时间 | 秒级 | 3-10 分钟 |

### 3. 全面 Kubernetes 原生
- Spring Boot Actuator 的 Liveness/Readiness/Startup 探针
- Spring Cloud Kubernetes 直接读取 ConfigMap/Secret
- Graceful Shutdown 开箱即用

### 4. OpenTelemetry 替代 Zipkin
```yaml
management:
  otlp:
    tracing:
      endpoint: http://otel-collector:4318/v1/traces
    metrics:
      export:
        url: http://otel-collector:4318/v1/metrics
```

## 与 3.x 核心差异

| 对比项 | Spring Boot 3.x | Spring Boot 4.x |
|--------|----------------|----------------|
| Java 最低 | 17 | **21**（LTS）|
| 虚拟线程 | 可选（3.2+）| **推荐默认开启** |
| Native Image | 正式支持 | **更快构建、更小体积** |
| 链路追踪 | Micrometer + Brave/Zipkin | **Micrometer + OpenTelemetry** |
| K8s 集成 | 基础支持 | **深度 K8s 原生** |
| Structured Concurrency | 预览 | **Java 21 正式 API** |

## 快速启动顺序

### 传统微服务模式
1. 启动 Nacos 3.x Server
2. 启动 Redis（Gateway 限流）
3. 启动 OpenTelemetry Collector（可选）
4. 启动业务微服务
5. 启动 Spring Cloud Gateway

### Kubernetes 模式
```bash
kubectl apply -f k8s/nacos/           # 可选
kubectl apply -f k8s/configmaps/
kubectl apply -f k8s/secrets/
kubectl apply -f k8s/deployments/
kubectl apply -f k8s/services/
kubectl apply -f k8s/ingress/
```
