# Spring Boot 3.x — Nacos 配置中心搭建指南

> Spring Boot 3.3.x + Spring Cloud Alibaba 2023.0.3 + Nacos 2.3.x
> Java 17+，支持 GraalVM Native、Virtual Threads

---

## 一、Maven 依赖

```xml
<dependencies>
    <!-- Nacos 配置中心（已适配 Jakarta EE）-->
    <dependency>
        <groupId>com.alibaba.cloud</groupId>
        <artifactId>spring-cloud-starter-alibaba-nacos-config</artifactId>
    </dependency>
    <!-- Spring Boot 3.x 不再需要单独引入 bootstrap，
         通过 spring.config.import 替代 -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-actuator</artifactId>
    </dependency>
    <!-- 配置属性注解处理器（IDE 提示）-->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-configuration-processor</artifactId>
        <optional>true</optional>
    </dependency>
</dependencies>
```

---

## 二、配置方式（Spring Boot 3.x 推荐 spring.config.import）

### 2.1 application.yml（推荐方式）

```yaml
spring:
  application:
    name: order-service
  profiles:
    active: dev
  cloud:
    nacos:
      # 统一配置（discovery 和 config 共用）
      server-addr: 127.0.0.1:8848
      username: nacos
      password: nacos
      config:
        namespace: ${NACOS_NAMESPACE:dev-xxxxxx}
        group: ORDER_GROUP
        file-extension: yaml
        # 是否开启自动刷新（默认 true）
        refresh-enabled: true
  # Spring Boot 3.x 推荐的配置导入方式
  config:
    import:
      # 格式: nacos:{data-id}?group={group}&refreshEnabled=true
      - nacos:${spring.application.name}-${spring.profiles.active}.yaml
      - nacos:${spring.application.name}.yaml?refreshEnabled=false
      - nacos:common-datasource.yaml?group=SHARED_GROUP
      - nacos:common-redis.yaml?group=SHARED_GROUP

# 优先使用环境变量覆盖（12-Factor App 原则）
server:
  port: ${SERVER_PORT:8080}
```

### 2.2 bootstrap.yml（兼容旧方式，需引入 bootstrap 依赖）

```xml
<!-- 若仍需 bootstrap.yml -->
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-bootstrap</artifactId>
</dependency>
```

```yaml
# bootstrap.yml
spring:
  application:
    name: order-service
  profiles:
    active: dev
  cloud:
    nacos:
      config:
        server-addr: 127.0.0.1:8848
        namespace: dev-xxxxxx
        group: ORDER_GROUP
        file-extension: yaml
        username: nacos
        password: nacos
        shared-configs:
          - data-id: common-datasource.yaml
            group: SHARED_GROUP
            refresh: true
```

---

## 三、Nacos 控制台配置示例

在 Nacos 控制台创建如下配置：

**Data ID**: `order-service-dev.yaml`
**Group**: `ORDER_GROUP`
**Namespace**: `dev`

```yaml
server:
  port: 8080

order:
  timeout: 5000
  max-page-size: 100
  payment-deadline-hours: 24

spring:
  datasource:
    driver-class-name: com.mysql.cj.jdbc.Driver
    url: jdbc:mysql://dev-db:3306/orders?useSSL=false&serverTimezone=Asia/Shanghai
    username: dev_user
    password: ${DB_PASSWORD:dev_pass}   # 支持环境变量占位符
    hikari:
      maximum-pool-size: 20
      minimum-idle: 5
      connection-timeout: 30000
  data:
    redis:
      host: dev-redis
      port: 6379
      password: ${REDIS_PASSWORD:}
```

---

## 四、使用配置（3.x 最佳实践）

### 4.1 @ConfigurationProperties（推荐）

```java
// Spring Boot 3.x：@ConstructorBinding 变为可选（记录类自动支持）
@ConfigurationProperties(prefix = "order")
public record OrderProperties(
    int timeout,
    int maxPageSize,
    int paymentDeadlineHours
) {}

// 注册配置类
@SpringBootApplication
@ConfigurationPropertiesScan   // 自动扫描所有 @ConfigurationProperties
public class OrderServiceApplication { ... }
```

```java
// 传统类风格
@ConfigurationProperties(prefix = "order")
@RefreshScope   // 支持 Nacos 动态刷新
public class OrderProperties {
    private int timeout = 5000;
    private int maxPageSize = 100;
    private int paymentDeadlineHours = 24;
    // getter/setter
}
```

### 4.2 @Value（简单场景）

```java
@RestController
@RefreshScope
public class OrderController {

    // 支持 SpEL 默认值
    @Value("${order.timeout:5000}")
    private int timeout;

    // 直接注入配置类（推荐）
    private final OrderProperties orderProperties;

    public OrderController(OrderProperties orderProperties) {
        this.orderProperties = orderProperties;
    }
}
```

### 4.3 动态刷新监听（程序化）

```java
@Component
public class NacosConfigChangeListener {

    @Autowired
    private NacosConfigManager nacosConfigManager;

    @PostConstruct
    public void registerListener() throws NacosException {
        nacosConfigManager.getConfigService().addListener(
            "order-service-dev.yaml",
            "ORDER_GROUP",
            new AbstractSharedListener() {
                @Override
                public void innerReceive(String dataId, String group, String configInfo) {
                    log.info("Config changed: dataId={}, group={}", dataId, group);
                    // 重新解析配置，触发特定业务逻辑
                    // 例如：重新加载黑名单、刷新缓存等
                }
            }
        );
    }
}
```

---

## 五、配置加密（Spring Boot 3.x + Jasypt 3.x）

```xml
<dependency>
    <groupId>com.github.ulisesbocchio</groupId>
    <artifactId>jasypt-spring-boot-starter</artifactId>
    <version>3.0.5</version>
</dependency>
```

```yaml
jasypt:
  encryptor:
    # 密钥通过环境变量注入（不写死在配置文件）
    password: ${JASYPT_ENCRYPTOR_PASSWORD}
    algorithm: PBEWITHHMACSHA512ANDAES_256
    iv-generator-class-name: org.jasypt.iv.RandomIvGenerator
```

```bash
# 生产环境启动命令（密钥通过环境变量传入）
export JASYPT_ENCRYPTOR_PASSWORD="my-secret-key"
java -jar order-service.jar
```

---

## 六、GraalVM Native Image 配置适配

```java
// src/main/resources/META-INF/native-image/reflect-config.json
// Nacos 客户端需要反射配置（Spring Cloud Alibaba 2023.0.1+ 已自动生成）

// 手动添加项目中的配置类
@RegisterReflectionForBinding({
    OrderProperties.class,
    DatasourceProperties.class
})
@SpringBootApplication
public class OrderServiceApplication { ... }
```

```bash
# 构建原生镜像
./mvnw -Pnative spring-boot:build-image

# 或使用 GraalVM 本地编译
./mvnw -Pnative native:compile -DskipTests
```

---

## 七、Actuator 配置刷新端点

```yaml
management:
  endpoints:
    web:
      exposure:
        include: refresh,health,configprops,env
  endpoint:
    configprops:
      show-values: always   # 3.x 新增，可查看所有配置值
```

```bash
# 手动触发刷新（POST）
curl -X POST http://localhost:8080/actuator/refresh

# 查看当前所有配置（含来源）
curl http://localhost:8080/actuator/env

# 查看 @ConfigurationProperties 当前值
curl http://localhost:8080/actuator/configprops
```

---

## 八、多配置文件加载优先级（从高到低）

```
1. 命令行参数 --spring.cloud.nacos.config.xxx
2. 环境变量 SPRING_CLOUD_NACOS_CONFIG_XXX
3. Nacos：{application}-{profile}.yaml（主配置）
4. Nacos：{application}.yaml（不含profile）
5. Nacos：共享配置（extension-configs）
6. 本地 application-{profile}.yml
7. 本地 application.yml
```

---

## 九、Spring Boot 3.x 配置中心演进亮点

| 特性 | 说明 |
|------|------|
| `spring.config.import` | 替代 bootstrap，更标准的配置导入方式 |
| Record 类配置绑定 | `@ConfigurationProperties` 支持 Java Record |
| `show-values: always` | Actuator 可直接查看配置绑定值 |
| GraalVM Native | 配置中心客户端支持原生镜像 |
| Virtual Threads | 配置刷新回调自动使用虚拟线程 |
