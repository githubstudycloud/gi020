# Spring Boot 微服务三件套搭建指南

> 配置中心 · 注册中心 · 网关 完整搭建指南

## 版本对应关系

| Spring Boot | Spring Cloud | 注册中心（主流） | 配置中心（主流） | 网关（主流） |
|-------------|--------------|-----------------|-----------------|-------------|
| 1.5.x       | Dalston / Edgware | Eureka      | Spring Cloud Config | Zuul 1.x |
| 2.3.x–2.7.x | Hoxton / 2021.0.x | Nacos 1.x   | Nacos Config        | Spring Cloud Gateway |
| 3.1.x–3.3.x | 2022.0.x / 2023.0.x | Nacos 2.3.x | Nacos Config      | Spring Cloud Gateway |
| 4.0.x（预览）| 2025.0.x    | Nacos / Kubernetes | Nacos / K8s ConfigMap | Spring Cloud Gateway |

## 目录结构

```
springboot-cloud-guide/
├── springboot-1x/       # Spring Boot 1.5.x + Spring Cloud Dalston
│   ├── registry/        # Eureka Server & Client
│   ├── config-center/   # Spring Cloud Config Server & Client
│   └── gateway/         # Zuul 网关
│
├── springboot-2x/       # Spring Boot 2.7.x + Spring Cloud 2021.0.x
│   ├── registry/        # Nacos 注册中心
│   ├── config-center/   # Nacos 配置中心
│   └── gateway/         # Spring Cloud Gateway
│
├── springboot-3x/       # Spring Boot 3.3.x + Spring Cloud 2023.0.x
│   ├── registry/        # Nacos 2.3.x 注册中心
│   ├── config-center/   # Nacos 配置中心
│   └── gateway/         # Spring Cloud Gateway (Reactive)
│
└── springboot-4x/       # Spring Boot 4.0.x + Spring Cloud 2025.0.x（预览）
    ├── registry/        # Kubernetes / Nacos 注册中心
    ├── config-center/   # Kubernetes ConfigMap / Nacos
    └── gateway/         # Spring Cloud Gateway (Virtual Threads)
```

## 核心演进趋势

- **1.x → 2.x**：从 Netflix OSS（Eureka/Zuul）迁移到 Alibaba Cloud（Nacos）+ 响应式网关
- **2.x → 3.x**：Jakarta EE 命名空间迁移，要求 Java 17+，全面拥抱 GraalVM Native
- **3.x → 4.x**：Spring Framework 7，要求 Java 21+，Virtual Threads 优先，Kubernetes 原生
