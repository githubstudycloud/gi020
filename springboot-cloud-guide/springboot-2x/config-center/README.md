# Spring Boot 2.x — Nacos 配置中心搭建指南

> Spring Boot 2.7.x + Spring Cloud Alibaba 2021.0.5 + Nacos Config

---

## 一、Nacos 配置中心核心概念

```
Data ID    = {spring.application.name}-{spring.profiles.active}.{file-extension}
           = order-service-dev.yaml

Group      = DEFAULT_GROUP（业务分组）

Namespace  = dev（环境隔离）
```

---

## 二、Maven 依赖

```xml
<dependencies>
    <!-- Nacos 配置中心 -->
    <dependency>
        <groupId>com.alibaba.cloud</groupId>
        <artifactId>spring-cloud-starter-alibaba-nacos-config</artifactId>
    </dependency>
    <!-- Spring Boot 2.4+ 需要额外引入 bootstrap -->
    <dependency>
        <groupId>org.springframework.cloud</groupId>
        <artifactId>spring-cloud-starter-bootstrap</artifactId>
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

> **注意**：Spring Boot 2.4+ 默认禁用 bootstrap 上下文，
> 必须引入 `spring-cloud-starter-bootstrap` 或使用 `spring.config.import`。

---

## 三、配置文件

### 3.1 bootstrap.yml（2.4以下 或 引入bootstrap依赖后）

```yaml
spring:
  application:
    name: order-service
  profiles:
    active: dev
  cloud:
    nacos:
      config:
        # Nacos Server 地址
        server-addr: 127.0.0.1:8848
        # 配置文件格式（properties/yaml）
        file-extension: yaml
        # 命名空间（对应 Nacos namespace ID，非名称）
        namespace: a1b2c3d4-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        # 分组
        group: ORDER_GROUP
        # 认证
        username: nacos
        password: nacos

        # 共享配置（多个服务共用的配置）
        shared-configs:
          - data-id: common-datasource.yaml
            group: SHARED_GROUP
            refresh: true
          - data-id: common-redis.yaml
            group: SHARED_GROUP
            refresh: true

        # 扩展配置（优先级高于 shared，低于主配置）
        extension-configs:
          - data-id: order-service-ext.yaml
            group: ORDER_GROUP
            refresh: true
```

### 3.2 application.yml（2.4+ 推荐 spring.config.import 方式）

```yaml
# Spring Boot 2.4+ 新方式（无需 bootstrap.yml）
spring:
  application:
    name: order-service
  profiles:
    active: dev
  config:
    import:
      - nacos:order-service-dev.yaml?group=ORDER_GROUP&refreshEnabled=true
      - nacos:common-datasource.yaml?group=SHARED_GROUP&refreshEnabled=true
  cloud:
    nacos:
      config:
        server-addr: 127.0.0.1:8848
        namespace: a1b2c3d4-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        username: nacos
        password: nacos
```

---

## 四、Nacos 控制台创建配置

在 `http://localhost:8848/nacos` 中：

1. 切换到对应命名空间（如 dev）
2. 配置管理 → 配置列表 → 新建配置

```
Data ID:   order-service-dev.yaml
Group:     ORDER_GROUP
格式:      YAML
```

```yaml
# 配置内容示例
server:
  port: 8080

order:
  timeout: 5000
  currency: CNY
  max-retry: 3

spring:
  datasource:
    url: jdbc:mysql://dev-db:3306/orders?useSSL=false&serverTimezone=UTC
    username: dev_user
    password: dev_pass
    hikari:
      maximum-pool-size: 10
      minimum-idle: 5
```

---

## 五、使用配置

### 5.1 @Value + @RefreshScope（动态刷新）

```java
@RestController
@RefreshScope  // 配置变更时自动刷新此 Bean
public class OrderController {

    @Value("${order.timeout:5000}")
    private int timeout;

    @Value("${order.currency:CNY}")
    private String currency;

    @GetMapping("/config")
    public Map<String, Object> getConfig() {
        return Map.of("timeout", timeout, "currency", currency);
    }
}
```

### 5.2 @ConfigurationProperties（推荐，类型安全）

```java
@Component
@ConfigurationProperties(prefix = "order")
@RefreshScope
public class OrderProperties {

    private int timeout = 5000;
    private String currency = "CNY";
    private int maxRetry = 3;

    // getter/setter（或使用 Lombok @Data）
}

// 使用
@Service
public class OrderService {

    @Autowired
    private OrderProperties orderProps;

    public void processOrder() {
        int timeout = orderProps.getTimeout();
        // ...
    }
}
```

### 5.3 监听配置变更事件

```java
@Component
public class ConfigChangeListener {

    @Autowired
    private NacosConfigManager nacosConfigManager;

    @PostConstruct
    public void init() throws NacosException {
        // 监听指定 DataId 的变化
        nacosConfigManager.getConfigService().addListener(
            "order-service-dev.yaml",
            "ORDER_GROUP",
            new Listener() {
                @Override
                public Executor getExecutor() { return null; }

                @Override
                public void receiveConfigInfo(String configInfo) {
                    System.out.println("配置已更新: " + configInfo);
                    // 自定义处理逻辑（如重新初始化连接池）
                }
            }
        );
    }
}
```

---

## 六、配置优先级（从高到低）

```
1. 主配置（spring.application.name + profile + file-extension）
   → order-service-dev.yaml

2. 扩展配置（extension-configs，按 index 倒序，大 index 优先）
   → order-service-ext.yaml

3. 共享配置（shared-configs，按 index 倒序）
   → common-datasource.yaml

4. 本地 application.yml

5. 本地 bootstrap.yml
```

---

## 七、灰度发布配置

Nacos 控制台支持 Beta 发布（灰度）：

1. 编辑配置 → 点击"Beta发布"
2. 填写灰度 IP：`192.168.1.100,192.168.1.101`
3. 保存后只有指定 IP 的实例收到新配置
4. 验证通过后点击"发布"全量生效

---

## 八、配置加密（使用 Jasypt）

```xml
<dependency>
    <groupId>com.github.ulisesbocchio</groupId>
    <artifactId>jasypt-spring-boot-starter</artifactId>
    <version>3.0.5</version>
</dependency>
```

```yaml
# application.yml
jasypt:
  encryptor:
    password: my-encryption-key      # 加密密钥（建议通过环境变量传入）
    algorithm: PBEWITHHMACSHA512ANDAES_256
```

```yaml
# Nacos 配置内容（密文用 ENC() 包裹）
spring:
  datasource:
    password: ENC(encryptedPasswordHere...)
```

```bash
# 生成密文
java -cp jasypt-1.9.3.jar \
  org.jasypt.intf.cli.JasyptPBEStringEncryptionCLI \
  input="my-plain-password" \
  password="my-encryption-key" \
  algorithm="PBEWITHHMACSHA512ANDAES_256"
```

---

## 九、多环境配置最佳实践

```
Nacos Namespace 划分：
├── public（公共，不建议用）
├── 开发: namespace-id = dev-xxxx
├── 测试: namespace-id = test-xxxx
└── 生产: namespace-id = prod-xxxx

DataID 规范：
{service-name}.yaml              → 所有环境通用基础配置
{service-name}-{profile}.yaml   → 环境特定配置（覆盖基础）
common-{type}.yaml               → 跨服务共享配置（放在 SHARED_GROUP）
```

启动命令：
```bash
# 通过 JVM 参数指定环境（无需修改配置文件）
java -jar order-service.jar \
  --spring.profiles.active=prod \
  --spring.cloud.nacos.config.namespace=prod-xxxx \
  --spring.cloud.nacos.config.server-addr=prod-nacos:8848
```
