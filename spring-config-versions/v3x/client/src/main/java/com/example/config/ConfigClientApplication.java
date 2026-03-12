package com.example.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.cloud.context.config.annotation.RefreshScope;
import org.springframework.stereotype.Component;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Spring Boot 3.x Config Client
 *
 * 3.x 关键变化：
 * 1. spring.config.import 是推荐方式，取代 bootstrap.yml
 * 2. javax.* → jakarta.* 包名变更
 * 3. @ConstructorBinding 不再需要显式添加（单构造函数自动绑定）
 * 4. 支持 GraalVM 原生镜像（需要配置 AOT 元数据）
 */
@SpringBootApplication
@EnableConfigurationProperties(AppProperties.class)
public class ConfigClientApplication {

    public static void main(String[] args) {
        SpringApplication.run(ConfigClientApplication.class, args);
    }
}

/**
 * 方式一：@Value + @RefreshScope（简单但不推荐大量使用）
 *
 * 刷新命令（3.x）：
 *   curl -X POST http://localhost:8080/actuator/refresh
 */
@RestController
@RefreshScope
class ConfigValueController {

    @Value("${app.message:default-message}")
    private String message;

    @Value("${app.version:0.0.1}")
    private String version;

    @GetMapping("/config/value")
    public String getConfigByValue() {
        return String.format("Boot 3.x [@Value] message=%s, version=%s", message, version);
    }
}

/**
 * 方式二：@ConfigurationProperties（推荐，类型安全）
 *
 * 3.x 中 @ConfigurationProperties 类不再需要 @ConstructorBinding 注解
 * （单个构造函数会自动推断为构造器绑定）
 *
 * 注意：@ConfigurationProperties 本身不支持热刷新
 * 如需刷新，需结合 @RefreshScope（但会重建整个 Bean，有一定开销）
 */
@Component
@ConfigurationProperties(prefix = "app")
@RefreshScope
class AppProperties {

    private String message;
    private String version;

    // Spring Boot 3.x 支持 record 类型绑定
    // public record AppProperties(String message, String version) {}

    public String getMessage() { return message; }
    public void setMessage(String message) { this.message = message; }
    public String getVersion() { return version; }
    public void setVersion(String version) { this.version = version; }
}

@RestController
class ConfigPropertiesController {

    private final AppProperties appProperties;

    public ConfigPropertiesController(AppProperties appProperties) {
        this.appProperties = appProperties;
    }

    @GetMapping("/config/properties")
    public String getConfigByProperties() {
        return String.format(
            "Boot 3.x [@ConfigProperties] message=%s, version=%s",
            appProperties.getMessage(),
            appProperties.getVersion()
        );
    }
}
