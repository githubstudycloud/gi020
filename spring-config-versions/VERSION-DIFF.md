# Spring Cloud Config 各版本核心差异对比

## 一、版本依赖速查

| Spring Boot | Spring Cloud BOM        | Java | spring-cloud-config 版本 |
|-------------|-------------------------|------|--------------------------|
| 1.3.x       | Brixton.SR7             | 7/8  | 1.1.x                    |
| 1.4.x       | Camden.SR7              | 7/8  | 1.2.x                    |
| 1.5.x       | Dalston.SR5 / Edgware   | 8    | 1.3.x / 1.4.x            |
| 2.0.x       | Finchley.SR4            | 8    | 2.0.x                    |
| 2.1.x       | Greenwich.SR6           | 8    | 2.1.x                    |
| 2.2/2.3.x   | Hoxton.SR12             | 8/11 | 2.2.x / 2.3.x            |
| 2.4.x       | 2020.0.6 (Ilford)       | 8/11 | 3.0.x                    |
| 2.5/2.6.x   | 2021.0.9 (Jubilee)      | 8/11 | 3.1.x                    |
| 2.7.x       | 2021.0.9 / 2022.0.x     | 8/11 | 3.1.x / 4.0.x            |
| 3.0/3.1.x   | 2022.0.5 (Kilburn)      | 17   | 4.0.x                    |
| 3.2/3.3.x   | 2023.0.x (Leyton)       | 17   | 4.1.x                    |
| 3.4.x       | 2024.0.x (Moorgate)     | 17   | 4.2.x                    |
| 4.0.x       | 2024.0.x (里程碑)        | 21   | 4.2.x+                   |

---

## 二、客户端配置方式演进

### Spring Boot 1.x / 2.0~2.3.x（bootstrap.yml 时代）

```
src/main/resources/
  bootstrap.yml      ← 配置 Config Server 地址（最先加载）
  application.yml    ← 本地默认配置（被远程配置覆盖）
```

**bootstrap.yml 关键配置：**
```yaml
spring:
  application:
    name: myapp
  cloud:
    config:
      uri: http://localhost:8888
      profile: dev
      label: master
      fail-fast: true
```

---

### Spring Boot 2.4.x（过渡期，两种方式并存）

```
# 方式一：继续使用 bootstrap.yml（需引入额外依赖）
<dependency>
  <groupId>org.springframework.cloud</groupId>
  <artifactId>spring-cloud-starter-bootstrap</artifactId>
</dependency>

# 方式二（推荐）：application.yml 中使用 spring.config.import
spring:
  config:
    import: "optional:configserver:http://localhost:8888"
```

---

### Spring Boot 2.5+ / 3.x / 4.x（spring.config.import 时代）

```yaml
# application.yml
spring:
  application:
    name: myapp
  config:
    import: "optional:configserver:http://admin:pass@localhost:8888"
  cloud:
    config:
      label: main
```

**不再需要 bootstrap.yml！**

---

## 三、服务端变化对比

| 功能                  | 1.x              | 2.x              | 3.x              | 4.x              |
|-----------------------|------------------|------------------|------------------|------------------|
| 启动注解              | @EnableConfigServer | 相同          | 相同             | 相同             |
| Security 配置         | 继承 WebSecurityConfigurerAdapter | 废弃父类，用 @Bean SecurityFilterChain | 移除父类 | Security 7.x   |
| antMatchers           | ✓                | ✓                | ✗（改 requestMatchers）| ✗ |
| Vault 后端            | ✗                | ✓                | ✓                | ✓                |
| 复合后端 composite    | ✗                | ✓                | ✓                | ✓                |
| clone-on-start        | ✓                | ✓                | ✓                | ✓                |
| 虚拟线程              | ✗                | ✗                | ✗（可手动启用）  | ✓（默认启用）    |

---

## 四、配置刷新方式对比

| 版本     | 手动刷新端点                        | 广播刷新（Bus）                        |
|----------|-------------------------------------|----------------------------------------|
| 1.x      | POST /refresh                       | POST /bus/refresh                      |
| 2.x      | POST /actuator/refresh              | POST /actuator/bus-refresh             |
| 3.x/4.x  | POST /actuator/refresh              | POST /actuator/busrefresh              |

**所有版本都需要 @RefreshScope 标注需要刷新的 Bean。**

---

## 五、加密值使用方式（所有版本通用）

### 服务端加密操作
```bash
# 加密
curl http://admin:admin123@localhost:8888/encrypt -d "my-secret-value"
# 返回：AQA8xxxxxxxxxxxxxxxxx

# 解密
curl http://admin:admin123@localhost:8888/decrypt -d "AQA8xxxxxxxxxxxxxxxxx"
# 返回：my-secret-value
```

### Git 仓库中使用加密值
```yaml
# myapp-dev.yml
spring:
  datasource:
    password: '{cipher}AQA8xxxxxxxxxxxxxxxxx'
```

### 服务端配置（对称加密）
```yaml
encrypt:
  key: my-32-char-secret-key-here!!
```

### 服务端配置（RSA 非对称加密，推荐生产使用）
```bash
# 生成 keystore
keytool -genkeypair -alias mykey -keyalg RSA \
  -keystore keystore.jks -storepass storepass \
  -keypass keypass -validity 3650
```
```yaml
encrypt:
  key-store:
    location: classpath:keystore.jks
    alias: mykey
    password: storepass
    secret: keypass
```

---

## 六、常见问题排查

### 问题1：Spring Boot 2.4+ 客户端启动报 "No spring.config.import property"
**原因**：引入了 spring-cloud-starter-config 但没有配置导入方式
**解决**：
```yaml
# application.yml 中添加
spring:
  config:
    import: "optional:configserver:http://localhost:8888"
```
或引入 `spring-cloud-starter-bootstrap` 并使用 bootstrap.yml

### 问题2：1.x 升级 2.x 后 /refresh 返回 404
**原因**：Actuator 端点路径变化
**解决**：改用 `POST /actuator/refresh`，并在 application.yml 配置：
```yaml
management:
  endpoints:
    web:
      exposure:
        include: refresh
```

### 问题3：3.x 中 antMatchers 编译错误
**原因**：Spring Security 6.x 移除了 antMatchers
**解决**：改用 `requestMatchers`

### 问题4：Config Server 的 Git 仓库每次都重新克隆
**原因**：basedir 未配置或被清理
**解决**：
```yaml
spring.cloud.config.server.git:
  basedir: /var/config-cache   # 指定稳定的缓存目录
  force-pull: true
  refresh-rate: 30             # 缓存30秒
```

### 问题5：客户端连不上 Config Server（fail-fast=false 时无提示）
**解决**：启动时加 `--spring.cloud.config.fail-fast=true` 或查看 DEBUG 日志：
```yaml
logging:
  level:
    org.springframework.cloud.config.client: DEBUG
```

---

## 七、Config Server URL 规则

```
GET /{application}/{profile}[/{label}]
GET /{application}-{profile}.yml
GET /{label}/{application}-{profile}.yml
GET /{application}-{profile}.properties
GET /{label}/{application}-{profile}.properties
```

示例（应用 myapp，profile=dev，分支 main）：
- `http://localhost:8888/myapp/dev`
- `http://localhost:8888/myapp/dev/main`
- `http://localhost:8888/myapp-dev.yml`
- `http://localhost:8888/main/myapp-dev.yml`

---

## 八、Git 仓库配置文件加载优先级

客户端 `spring.application.name=myapp`，`profile=dev` 时，加载顺序（**越后越优先**）：

1. `application.yml`（公共默认）
2. `application-dev.yml`（公共 dev 配置）
3. `myapp.yml`（应用默认）
4. `myapp-dev.yml`（应用 dev 配置）← 最高优先级
