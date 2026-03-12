# Spring Boot 2.x 微服务三件套

> Spring Boot 2.7.x + Spring Cloud 2021.0.x + Spring Cloud Alibaba 2021.0.5

## 技术栈

| 组件 | 技术选型 | 版本 |
|------|---------|------|
| 注册中心 | Alibaba Nacos | 2.0.4 |
| 配置中心 | Nacos Config | 2.0.4 |
| 网关 | Spring Cloud Gateway | 3.1.x |
| 熔断 | Resilience4j | 1.7.x |
| 负载均衡 | Spring Cloud LoadBalancer | 3.1.x |
| 服务调用 | OpenFeign | 3.1.x |

## 版本对应

```
Spring Boot:           2.7.18
Spring Cloud:          2021.0.9 (Jubilee)
Spring Cloud Alibaba:  2021.0.5.0
Nacos Server:          2.0.4
Java:                  8+ (推荐 11)
```

## 子目录

- [注册中心 (Nacos Discovery)](./registry/README.md)
- [配置中心 (Nacos Config)](./config-center/README.md)
- [网关 (Spring Cloud Gateway)](./gateway/README.md)

## 架构图

```
外部请求
    │
    ▼
┌─────────────────────────────────┐
│    Spring Cloud Gateway (9000)  │
│  ┌─────────┐  ┌──────────────┐  │
│  │认证Filter│  │限流Filter(Redis)│ │
│  └─────────┘  └──────────────┘  │
└─────────────┬───────────────────┘
              │ lb://service-name
              ▼
    ┌─────────────────┐
    │   Nacos Server   │  ← 注册中心 + 配置中心
    │   (8848/9848)    │
    └────────┬────────┘
             │ 注册/拉取配置
    ┌────────┼────────┐
    ▼        ▼        ▼
┌────────┐ ┌──────┐ ┌──────────┐
│user-svc│ │order │ │payment   │
│:8081   │ │:8082 │ │:8083     │
└────────┘ └──────┘ └──────────┘
```

## 与 1.x 主要变化

| 对比项 | Spring Boot 1.x | Spring Boot 2.x |
|--------|----------------|----------------|
| 注册中心 | Eureka | **Nacos**（官方维护，功能更强）|
| 配置中心 | Spring Cloud Config | **Nacos Config**（可视化控制台）|
| 网关 | Zuul 1.x（Servlet）| **Spring Cloud Gateway**（Reactor）|
| 熔断 | Hystrix（停维）| **Resilience4j** |
| 负载均衡 | Ribbon（停维）| **Spring Cloud LoadBalancer** |

## 快速启动顺序

1. 启动 Nacos Server（`sh startup.sh -m standalone`）
2. 在 Nacos 控制台创建 Namespace 和配置（或启动时自动拉取）
3. 启动业务微服务
4. 启动 Spring Cloud Gateway
