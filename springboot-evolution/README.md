# Spring Boot 版本演进研究

> 系统梳理 Spring Boot 1.x / 2.x / 3.x / 4.x 各主要版本的组件、演变与变化

## 目录结构

```
springboot-evolution/
├── README.md                  # 本文件，总览与导航
├── 01-overview.md             # 版本总览与时间线
├── 02-springboot-1x.md        # Spring Boot 1.x 详解
├── 03-springboot-2x.md        # Spring Boot 2.x 详解
├── 04-springboot-3x.md        # Spring Boot 3.x 详解
├── 05-springboot-4x.md        # Spring Boot 4.x 详解
├── 06-migration-guides.md     # 跨版本迁移指南
├── 07-component-matrix.md     # 核心组件版本矩阵
└── 08-component-selection.md  # 各版本主流组件选型方案 ★
```

## 快速导航

| 主题 | 文件 |
|------|------|
| 版本时间线与支持状态 | [01-overview.md](./01-overview.md) |
| 1.x: Java EE, `@SpringBootApplication`, DevTools | [02-springboot-1x.md](./02-springboot-1x.md) |
| 2.x: Reactive, Micrometer, HikariCP | [03-springboot-2x.md](./03-springboot-2x.md) |
| 3.x: Jakarta EE, GraalVM, Virtual Threads | [04-springboot-3x.md](./04-springboot-3x.md) |
| 4.x: 模块化, JSpecify, BeanRegistrar | [05-springboot-4x.md](./05-springboot-4x.md) |
| 迁移指南 1→2→3→4 | [06-migration-guides.md](./06-migration-guides.md) |
| 组件版本对照矩阵 | [07-component-matrix.md](./07-component-matrix.md) |
| **主流组件选型方案** ★ | [08-component-selection.md](./08-component-selection.md) |

## 三大架构转折点

```
Boot 1.x ──→ Boot 2.0
  Java 6/7 → Java 8 最低要求
  Spring 4 → Spring 5 (响应式编程)
  Tomcat JDBC → HikariCP
  自定义指标 → Micrometer
  无 Kotlin → Kotlin 一等公民

Boot 2.x ──→ Boot 3.0
  Java 8 → Java 17 最低要求  ★最大跳跃
  javax.* → jakarta.*  (EE 命名空间迁移)
  Spring 5 → Spring 6
  Tomcat 9 → Tomcat 10
  实验性 Native → GraalVM 正式支持

Boot 3.x ──→ Boot 4.0
  单体 autoconfigure → 完全模块化
  JSR 305 → JSpecify 空安全
  Spring 6 → Spring 7
  Jakarta EE 10 → Jakarta EE 11
  Hibernate 6 → Hibernate 7
  Jackson 2 → Jackson 3
  移除 Undertow
```
