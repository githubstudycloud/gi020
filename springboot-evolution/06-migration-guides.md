# Spring Boot 跨版本迁移指南

## 1.x → 2.x 迁移

### 前提条件
- Java 8+（必须升级，Java 6/7 不再支持）
- Maven 3.2+ 或 Gradle 4+

### 步骤 1：升级版本号

```xml
<!-- Maven -->
<parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <!-- 从 1.5.22.RELEASE 升级 -->
    <version>2.7.18</version>  <!-- 推荐先升至 2.7.x -->
</parent>
```

### 步骤 2：Actuator 路径适配

```yaml
# 1.x 写法（已失效）
# 访问 /health, /info, /metrics

# 2.x 需要
management:
  endpoints:
    web:
      exposure:
        include: health, info, metrics  # 明确指定暴露的端点
  endpoint:
    health:
      show-details: always
# 访问 /actuator/health, /actuator/info, /actuator/metrics
```

代码中如有直接引用路径的地方也需更新：
```java
// 1.x 硬编码的端点路径检查
// "/health" → "/actuator/health"
```

### 步骤 3：Actuator 安全配置合并

```java
// 1.x：Actuator 有独立安全配置
// management.security.enabled=true

// 2.x：统一在 Spring Security 中配置
@Bean
public SecurityFilterChain actuatorSecurity(HttpSecurity http) throws Exception {
    http.requestMatcher(EndpointRequest.toAnyEndpoint())
        .authorizeRequests()
            .requestMatchers(EndpointRequest.to("health", "info")).permitAll()
            .anyRequest().hasRole("ACTUATOR")
        .and()
        .httpBasic();
    return http.build();
}
```

### 步骤 4：自定义 Actuator 端点

```java
// 1.x 方式（废弃）
public class CustomEndpoint extends AbstractEndpoint<Map<String, Object>> {
    public CustomEndpoint() {
        super("custom");
    }
    @Override
    public Map<String, Object> invoke() {
        return Map.of("status", "OK");
    }
}

// 2.x 方式
@Component
@Endpoint(id = "custom")
public class CustomEndpoint {
    @ReadOperation
    public Map<String, Object> info() {
        return Map.of("status", "OK");
    }
}
```

### 步骤 5：Spring Data 方法重命名

```java
// 1.x（旧方法名）
userRepository.findOne(id);          // 返回 T，可能返回 null
userRepository.delete(id);           // 按 ID 删除
userRepository.exists(id);           // 检查存在

// 2.x（新方法名）
userRepository.findById(id);         // 返回 Optional<T>
userRepository.deleteById(id);       // 按 ID 删除
userRepository.existsById(id);       // 检查存在
```

### 步骤 6：配置属性重命名

使用迁移工具自动检测：
```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-properties-migrator</artifactId>
    <scope>runtime</scope>
</dependency>
```

常见属性变化：
| 1.x 属性 | 2.x 属性 |
|---------|---------|
| `server.context-path` | `server.servlet.context-path` |
| `spring.datasource.initialize` | `spring.datasource.initialization-mode` |
| `security.user.name` | `spring.security.user.name` |
| `management.context-path` | `management.endpoints.web.base-path` |

### 步骤 7：JPA 变化

```yaml
spring:
  jpa:
    hibernate:
      # 1.x 默认：false（兼容旧 ID 生成策略）
      # 2.x 默认：true（对齐 Hibernate 默认值，可能影响已有数据）
      use-new-id-generator-mappings: false  # 若需要保持 1.x 行为
```

### 步骤 8：CRaSH 远程 Shell 替代

```
# 1.x 可用，2.x 已移除
# 替代方案：
# 1. JMX（management.jmx.enabled=true）
# 2. SSH 直接连接服务器
# 3. 自定义 Actuator 端点
```

---

## 2.x → 3.x 迁移（最复杂）

> 这是历史上最大的 Spring Boot 迁移，核心挑战是 `javax.*` → `jakarta.*` 命名空间迁移。

### 前提条件
- Java 17+（必须升级）
- Spring Boot 先升至 2.7.x（中间步骤）

### 步骤 1：先升至 2.7.x

在升到 3.x 之前，先升至 2.7.x，解决所有 2.x 废弃警告。

### 步骤 2：升级 Java 版本

```bash
# 检查 Java 版本
java -version

# 需要 Java 17+，推荐 Java 21（LTS）
# 更新项目 Java 版本
```

```xml
<!-- pom.xml -->
<properties>
    <java.version>17</java.version>
</properties>

<!-- 或显式设置 compiler -->
<plugin>
    <groupId>org.apache.maven.plugins</groupId>
    <artifactId>maven-compiler-plugin</artifactId>
    <configuration>
        <release>17</release>
    </configuration>
</plugin>
```

### 步骤 3：升级 Spring Boot 版本

```xml
<parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>3.5.x</version>
</parent>
```

### 步骤 4：Jakarta EE 命名空间迁移（最关键）

**推荐：使用 OpenRewrite 自动迁移**

```xml
<!-- pom.xml 中添加 OpenRewrite 插件 -->
<plugin>
    <groupId>org.openrewrite.maven</groupId>
    <artifactId>rewrite-maven-plugin</artifactId>
    <version>5.x.x</version>
    <configuration>
        <activeRecipes>
            <recipe>org.openrewrite.java.spring.boot3.UpgradeSpringBoot_3_0</recipe>
        </activeRecipes>
    </configuration>
    <dependencies>
        <dependency>
            <groupId>org.openrewrite.recipe</groupId>
            <artifactId>rewrite-spring</artifactId>
            <version>5.x.x</version>
        </dependency>
    </dependencies>
</plugin>
```

```bash
./mvnw rewrite:run
```

**手动替换（小项目）**：
```bash
# 使用 IDE 的全局替换（注意大小写）
javax.persistence     → jakarta.persistence
javax.servlet         → jakarta.servlet
javax.validation      → jakarta.validation
javax.annotation      → jakarta.annotation
javax.transaction     → jakarta.transaction
javax.websocket       → jakarta.websocket
javax.xml.bind        → jakarta.xml.bind
javax.inject          → jakarta.inject

# 以下不需要替换（JDK 标准库）：
javax.sql.*           ← 保持不变
javax.crypto.*        ← 保持不变
javax.net.*           ← 保持不变
```

### 步骤 5：Spring Security 迁移

```java
// 2.x（废弃方式）
@Configuration
public class SecurityConfig extends WebSecurityConfigurerAdapter {
    @Override
    protected void configure(HttpSecurity http) throws Exception {
        http.authorizeRequests()
            .antMatchers("/public/**").permitAll()
            .anyRequest().authenticated();
    }
}

// 3.x（必须改为此方式，WebSecurityConfigurerAdapter 已移除）
@Configuration
@EnableWebSecurity
public class SecurityConfig {
    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http.authorizeHttpRequests(auth -> auth
            .requestMatchers("/public/**").permitAll()
            .anyRequest().authenticated()
        );
        return http.build();
    }
}
```

方法迁移对应表：

| 2.x | 3.x |
|-----|-----|
| `authorizeRequests()` | `authorizeHttpRequests()` |
| `antMatchers("/path")` | `requestMatchers("/path")` |
| `mvcMatchers("/path")` | `requestMatchers("/path")` |
| `regexMatchers("pattern")` | `requestMatchers(RegexRequestMatcher...)` |
| `WebSecurityConfigurerAdapter` | `SecurityFilterChain @Bean` |

### 步骤 6：升级第三方库到 Jakarta 兼容版本

常见库的 Jakarta 兼容版本：

| 库 | 2.x 版本（javax） | 3.x 版本（jakarta） |
|---|----------|----------|
| Hibernate | 5.x | 6.x+ |
| Flyway | 8.x | 9.x+ |
| MapStruct | 1.4.x | 1.5.x+ |
| Lombok | 1.18.20 | 1.18.24+ |
| Springfox Swagger | 不支持 | 使用 springdoc-openapi 2.x |
| springdoc-openapi | 1.x | 2.x |

### 步骤 7：Spring Boot 3.0 其他变化

```java
// 自动配置注册文件迁移
// spring.factories 中 AutoConfiguration 已不再加载
// 必须迁移到：
// META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports

// 尾部斜杠不再匹配
// /api/users/ 和 /api/users 不再等同
// 修复方式：去掉请求中的尾部斜杠，或在 Controller 中显式处理

// PathMatchConfigurer 中的 setUseTrailingSlashMatch 已废弃
```

---

## 3.x → 4.x 迁移

### 前提条件
- 已在 Spring Boot 3.5.x 上运行
- Java 17+（最低要求不变）
- Gradle 8.14+（如使用 Gradle）

### 步骤 1：升级版本

```xml
<parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>4.0.3</version>
</parent>
```

### 步骤 2：移除 Undertow 依赖（如使用）

```xml
<!-- 迁移到 Jetty 12 -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-web</artifactId>
    <exclusions>
        <exclusion>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-tomcat</artifactId>
        </exclusion>
    </exclusions>
</dependency>
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-jetty</artifactId>
</dependency>

<!-- 或保持 Tomcat 11 默认即可 -->
```

### 步骤 3：处理 Jackson 3.x 变化

```yaml
# 检查 Jackson 行为变化
spring:
  jackson:
    # 4.x Jackson 3 默认不序列化 null
    # 若需要保持 2.x 行为：
    default-property-inclusion: always

    # 检查以下默认值是否有变化：
    deserialization:
      fail-on-unknown-properties: false
    serialization:
      write-dates-as-timestamps: false
```

```java
// 检查自定义 Jackson 模块
// Jackson 3 移除了部分模块，需要检查是否有影响
@Bean
public Jackson2ObjectMapperBuilderCustomizer jacksonCustomizer() {
    return builder -> builder
        .featuresToEnable(SerializationFeature.INDENT_OUTPUT)
        .featuresToDisable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES);
}
```

### 步骤 4：处理 Hibernate 7.x 变化

```java
// 检查原生 Hibernate API 使用（如 Session、SessionFactory 直接调用）
// Hibernate 7 在 org.hibernate.orm 包下有重组

// JPA 3.2 新特性（可选使用）
// @IdClass 和 @EmbeddedId 有更严格的规范

// ID 生成策略变化检查
@Entity
public class MyEntity {
    @Id
    @GeneratedValue  // 检查 Hibernate 7 下的默认策略变化
    private Long id;
}
```

### 步骤 5：处理 Spring Security 7.0

```java
// Spring Security 7 保持 SecurityFilterChain 模式（无大变化）
// 检查 OAuth2 配置（Spring Authorization Server 已整合进 Security）

// 移除（如有使用）：
// spring-boot-starter-oauth2-authorization-server（已不需要，Security 7 内置）
```

### 步骤 6：处理 Spring Batch 6.0（如使用）

```java
// Spring Batch 6.0 有较多 API 变化
// 参考：https://github.com/spring-projects/spring-batch/wiki/Spring-Batch-6.0-Migration-Guide
```

### 步骤 7：处理废弃的自动配置模块

```
# 4.x 模块化后，部分 autoconfigure 模块路径变化
# 若有直接引用 spring-boot-autoconfigure 内部类的代码需要检查
# 使用公开 API 的代码不受影响
```

---

## 通用迁移技巧

### 渐进式升级策略

```
推荐路径：
1.5.x → 2.7.x → 3.5.x → 4.0.x

每次只升一个主版本，确保所有测试通过后再升下一个。
```

### 使用属性迁移助手

```xml
<!-- 任何版本迁移都建议加入此工具 -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-properties-migrator</artifactId>
    <scope>runtime</scope>
</dependency>
<!-- 迁移完成后移除此依赖 -->
```

### 常见错误排查

| 错误信息 | 可能原因 | 解决方案 |
|---------|---------|---------|
| `ClassNotFoundException: javax.servlet.Servlet` | 升至 3.x 后 javax→jakarta 未迁移 | 全局替换 javax.servlet→jakarta.servlet |
| `BeanCreationException: WebSecurityConfigurerAdapter` | 3.x 移除了该类 | 改用 SecurityFilterChain Bean |
| `No qualifying bean of type 'RestTemplate'` | 2.x 起不再自动注入 RestTemplate | 注入 RestTemplate.Builder 自行构建 |
| 循环依赖启动失败 | 2.6 起默认禁止 | 重构代码消除循环，或设置 allow-circular-references=true |
| Actuator 端点 404 | 2.x 路径变化或未暴露 | 检查 management.endpoints.web.exposure.include |
| `UnsatisfiedDependencyException` 在 Native 编译 | 反射信息缺失 | 添加 @RegisterReflectionForBinding 或 RuntimeHints |
