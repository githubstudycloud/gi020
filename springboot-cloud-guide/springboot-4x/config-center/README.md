# Spring Boot 4.x — 配置中心搭建指南

> Spring Boot 4.0.x（预览）+ Spring Framework 7 + Java 21+
> 双轨并行：**Nacos 3.x**（传统微服务）/ **Kubernetes ConfigMap**（云原生）

---

> **版本说明**：本文基于 Spring Boot 4.0 Milestone 和 Spring Cloud 2025.0.x 路线图整理。

---

## 一、方案选型

| 方案 | 适用场景 | 优势 |
|------|---------|------|
| **Nacos 3.x Config** | 传统微服务 / 混合云 | 可视化、动态刷新、灰度发布 |
| **Kubernetes ConfigMap** | 纯 K8s 部署 | 无额外组件，K8s 原生 RBAC |
| **Spring Cloud Config + Git** | 配置版本控制优先 | Git 历史可追溯，PR 审核流程 |

---

## 二、方案一：Nacos 3.x Config（推荐）

### 2.1 Maven 依赖

```xml
<parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>4.0.0-M3</version>
</parent>

<properties>
    <java.version>21</java.version>
</properties>

<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>org.springframework.cloud</groupId>
            <artifactId>spring-cloud-dependencies</artifactId>
            <version>2025.0.0</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>
        <dependency>
            <groupId>com.alibaba.cloud</groupId>
            <artifactId>spring-cloud-alibaba-dependencies</artifactId>
            <version>2025.0.0.0</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>
    </dependencies>
</dependencyManagement>

<dependencies>
    <dependency>
        <groupId>com.alibaba.cloud</groupId>
        <artifactId>spring-cloud-starter-alibaba-nacos-config</artifactId>
    </dependency>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-actuator</artifactId>
    </dependency>
</dependencies>
```

### 2.2 application.yml（4.x 推荐 spring.config.import）

```yaml
spring:
  application:
    name: order-service
  profiles:
    active: ${SPRING_PROFILES_ACTIVE:prod}
  threads:
    virtual:
      enabled: true   # Java 21 虚拟线程
  cloud:
    nacos:
      server-addr: ${NACOS_SERVER_ADDR:nacos:8848}
      username: ${NACOS_USERNAME:nacos}
      password: ${NACOS_PASSWORD:nacos}
      config:
        namespace: ${NACOS_NAMESPACE:prod-xxxx}
        group: ${NACOS_GROUP:ORDER_GROUP}
        file-extension: yaml
        refresh-enabled: true
  config:
    import:
      - nacos:${spring.application.name}-${spring.profiles.active}.yaml
      - nacos:${spring.application.name}.yaml?refreshEnabled=false
      - nacos:common-datasource.yaml?group=SHARED_GROUP
      - nacos:common-observability.yaml?group=SHARED_GROUP

server:
  port: ${SERVER_PORT:8080}
```

### 2.3 Java 21 Record 配置绑定（4.x 特性）

```java
// Java 21 密封类 + Record：完全不可变的配置对象
@ConfigurationProperties(prefix = "order")
public record OrderProperties(
    int timeout,
    int maxPageSize,
    int paymentDeadlineHours,
    DataSourceConfig dataSource,
    CacheConfig cache
) {
    // Record 紧凑构造器：参数校验
    public OrderProperties {
        if (timeout <= 0) throw new IllegalArgumentException("timeout must be positive");
        if (maxPageSize > 1000) throw new IllegalArgumentException("maxPageSize cannot exceed 1000");
    }

    public record DataSourceConfig(String url, String username, int poolSize) {}
    public record CacheConfig(Duration ttl, int maxSize) {}
}

// 注册
@SpringBootApplication
@ConfigurationPropertiesScan
public class OrderServiceApplication { ... }
```

### 2.4 配置变更事件（4.x 响应式风格）

```java
@Component
public class ConfigChangeHandler {

    // 4.x：基于 Spring Application Events
    @EventListener(NacosConfigReceivedEvent.class)
    public void onConfigChanged(NacosConfigReceivedEvent event) {
        log.info("Config refreshed: dataId={}, group={}, namespace={}",
            event.getDataId(), event.getGroup(), event.getNamespace());
        // 触发缓存刷新、连接池重置等操作
    }
}
```

---

## 三、方案二：Kubernetes ConfigMap（云原生）

### 3.1 Maven 依赖

```xml
<dependencies>
    <!-- Spring Cloud Kubernetes Config -->
    <dependency>
        <groupId>org.springframework.cloud</groupId>
        <artifactId>spring-cloud-starter-kubernetes-fabric8-config</artifactId>
    </dependency>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-actuator</artifactId>
    </dependency>
</dependencies>
```

### 3.2 application.yml

```yaml
spring:
  application:
    name: order-service
  cloud:
    kubernetes:
      config:
        enabled: true
        # 从 ConfigMap 加载配置
        sources:
          - name: order-service-config    # ConfigMap 名称
            namespace: production
          - name: common-datasource       # 共享 ConfigMap
            namespace: production
        # 自动刷新（监听 ConfigMap 变更）
        reload:
          enabled: true
          mode: event       # event（推荐，基于 K8s Watch）或 polling
          period: 15000     # polling 模式的轮询间隔（毫秒）
      secrets:
        enabled: true
        sources:
          - name: order-service-secrets   # K8s Secret（密码等敏感信息）
            namespace: production
```

### 3.3 创建 Kubernetes ConfigMap

```yaml
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: order-service-config
  namespace: production
  labels:
    app: order-service
data:
  # 方式1：直接 key-value（扁平化）
  server.port: "8080"
  order.timeout: "5000"
  order.max-page-size: "100"

  # 方式2：application.yaml 文件内容（推荐，支持嵌套结构）
  application.yaml: |
    server:
      port: 8080
    order:
      timeout: 5000
      maxPageSize: 100
      paymentDeadlineHours: 24
    spring:
      datasource:
        url: jdbc:mysql://prod-db:3306/orders
        hikari:
          maximum-pool-size: 20
```

```yaml
# k8s/secret.yaml（敏感信息）
apiVersion: v1
kind: Secret
metadata:
  name: order-service-secrets
  namespace: production
type: Opaque
stringData:
  spring.datasource.username: prod_user
  spring.datasource.password: super_secret_pass
  spring.data.redis.password: redis_secret
```

```bash
# 应用配置
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml

# 实时更新配置（Spring Cloud Kubernetes 自动感知）
kubectl edit configmap order-service-config -n production
# 或通过 kubectl patch
kubectl patch configmap order-service-config -n production \
  --type merge \
  -p '{"data":{"order.timeout":"8000"}}'
```

### 3.4 Deployment 挂载 ConfigMap

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order-service
  namespace: production
spec:
  replicas: 3
  template:
    spec:
      serviceAccountName: spring-cloud-k8s
      containers:
        - name: order-service
          image: registry/order-service:4.0.0
          # 方式1：通过 Spring Cloud Kubernetes 自动加载（推荐）
          # 方式2：通过环境变量注入 Secret（Sidecar 模式）
          env:
            - name: DB_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: order-service-secrets
                  key: spring.datasource.password
          # 方式3：挂载为文件（ConfigMap → Volume）
          volumeMounts:
            - name: config-volume
              mountPath: /app/config
              readOnly: true
      volumes:
        - name: config-volume
          configMap:
            name: order-service-config
```

---

## 四、Sealed Secrets（K8s 加密 Secret 管理）

```bash
# 安装 kubeseal
brew install kubeseal

# 加密 Secret（只有集群内才能解密）
kubeseal --format=yaml < k8s/secret-plain.yaml > k8s/secret-sealed.yaml

# 将加密文件提交到 Git（安全！）
git add k8s/secret-sealed.yaml
git commit -m "Add sealed secrets for order-service"
```

---

## 五、方案三：Spring Cloud Config + Git（配置版本控制）

```xml
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-config</artifactId>
</dependency>
```

```yaml
spring:
  config:
    import: "configserver:http://config-server:8888"
  cloud:
    config:
      fail-fast: true
      retry:
        max-attempts: 6
      label: main    # Git 分支
```

Config Server 配置：
```yaml
spring:
  cloud:
    config:
      server:
        git:
          uri: https://github.com/org/config-repo
          default-label: main
          # SSH 私钥认证（推荐）
          private-key: |
            -----BEGIN OPENSSH PRIVATE KEY-----
            ...
          # 或 GitHub App Token
          username: git
          password: ${GITHUB_TOKEN}
```

---

## 六、Observability 配置（4.x 标准）

```yaml
# common-observability.yaml（共享配置）
management:
  tracing:
    sampling:
      probability: 0.1
  otlp:
    tracing:
      endpoint: http://otel-collector:4318/v1/traces
    metrics:
      export:
        url: http://otel-collector:4318/v1/metrics
  endpoints:
    web:
      exposure:
        include: health,info,metrics,prometheus,configprops
  endpoint:
    configprops:
      show-values: always
      # 4.x 新增：屏蔽敏感值
      roles: ADMIN
```

---

## 七、配置优先级（4.x，从高到低）

```
1. 命令行参数（--key=value）
2. 环境变量（SPRING_xxx）
3. Kubernetes Secret（挂载为环境变量）
4. Nacos / Config Server / K8s ConfigMap 远程配置
5. 本地 application-{profile}.yml
6. 本地 application.yml
```

最佳实践：
- **密码/密钥** → 环境变量 / K8s Secret / Vault
- **业务配置** → Nacos Config / K8s ConfigMap
- **默认值** → 本地 application.yml
