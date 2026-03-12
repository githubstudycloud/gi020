# Spring Boot 1.x 微服务三件套

> Spring Boot 1.5.x + Spring Cloud Edgware + Netflix OSS

## 技术栈

| 组件 | 技术选型 | 版本 |
|------|---------|------|
| 注册中心 | Netflix Eureka | spring-cloud-starter-eureka |
| 配置中心 | Spring Cloud Config | spring-cloud-config-server |
| 网关 | Netflix Zuul 1.x | spring-cloud-starter-zuul |
| 熔断 | Netflix Hystrix | spring-cloud-starter-hystrix |
| 负载均衡 | Netflix Ribbon | spring-cloud-starter-ribbon |
| 服务调用 | OpenFeign | spring-cloud-starter-feign |

## 版本对应

```
Spring Boot:  1.5.22.RELEASE
Spring Cloud: Edgware.SR6
Java:         8+
```

## 子目录

- [注册中心 (Eureka)](./registry/README.md)
- [配置中心 (Spring Cloud Config)](./config-center/README.md)
- [网关 (Zuul)](./gateway/README.md)

## 架构图

```
                    ┌─────────────────┐
                    │   Eureka Server  │
                    │   (注册中心)      │
                    └────────┬────────┘
                             │ 注册/心跳
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  Config Srv  │   │  API Gateway │   │  User Service│
│  (配置中心)   │   │  (Zuul)      │   │              │
└──────────────┘   └──────┬───────┘   └──────────────┘
        ▲                 │ 路由转发           ▲
        │                 ▼                    │
        │         ┌──────────────┐             │ Feign调用
        │         │  外部请求     │             │
        │         └──────────────┘   ┌──────────────┐
        │                            │ Order Service│
        └────────────────────────────┘
             拉取配置（bootstrap）
```

## 快速启动顺序

1. 启动 Eureka Server（端口 8761）
2. 启动 Config Server（端口 8888）
3. 启动业务服务（user-service, order-service 等）
4. 启动 Zuul Gateway（端口 9000）

## 注意事项

- Spring Boot 1.x 已停止维护（EOL: 2019年8月）
- `spring-cloud-starter-eureka` 在 2.x 后改名为 `spring-cloud-starter-netflix-eureka-client`
- Config Client 必须使用 `bootstrap.yml`，不能只用 `application.yml`
- Zuul 1.x 基于 Servlet，同步阻塞，高并发场景建议升级到 2.x 的 Spring Cloud Gateway
