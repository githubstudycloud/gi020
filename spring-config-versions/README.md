# Spring Cloud Config 各版本搭建指南

## 版本对应关系

| Spring Boot | Spring Cloud      | Java |
|-------------|-------------------|------|
| 1.x         | Brixton / Camden  | 7/8  |
| 2.x         | Hoxton / 2020.x   | 8/11 |
| 3.x         | 2022.x / 2023.x   | 17   |
| 4.x         | 2024.x (实验性)    | 21   |

## 目录结构

```
spring-config-versions/
├── v1x/        # Spring Boot 1.5.x + Spring Cloud Brixton/Camden
│   ├── server/ # Config Server
│   └── client/ # Config Client
├── v2x/        # Spring Boot 2.7.x + Spring Cloud Hoxton
│   ├── server/
│   └── client/
├── v3x/        # Spring Boot 3.2.x + Spring Cloud 2023.x
│   ├── server/
│   └── client/
└── v4x/        # Spring Boot 4.0.x + Spring Cloud 2024.x
    ├── server/
    └── client/
```

## 核心变化说明

1. **v1.x → v2.x**: bootstrap.yml 仍是主要配置方式，加入了 Vault/Consul 支持
2. **v2.x → v3.x**: 移除 bootstrap.yml 默认支持，需引入 spring-cloud-starter-bootstrap 或使用 spring.config.import
3. **v3.x → v4.x**: 完全拥抱 spring.config.import，支持 GraalVM 原生镜像
