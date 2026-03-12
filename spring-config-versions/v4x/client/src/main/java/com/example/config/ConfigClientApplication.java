package com.example.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.cloud.context.config.annotation.RefreshScope;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Spring Boot 4.x Config Client
 *
 * 4.x 相比 3.x 的变化：
 * 1. Java 21 Record 类型完整支持（@ConfigurationProperties 绑定 Record）
 * 2. 虚拟线程（Virtual Threads）默认可用
 * 3. spring.config.import 是唯一推荐方式（bootstrap 机制为遗留）
 * 4. 更好的 GraalVM Native Image 支持
 */
@SpringBootApplication
@EnableConfigurationProperties(AppConfig.class)
public class ConfigClientApplication {

    public static void main(String[] args) {
        SpringApplication.run(ConfigClientApplication.class, args);
    }
}

/**
 * 4.x 推荐：使用 Java Record + @ConfigurationProperties
 * Record 不可变，天然线程安全，与虚拟线程完美配合
 *
 * 注意：Record 类型的 @ConfigurationProperties 不支持 @RefreshScope
 * （因为 Record 不可变，无法重新绑定值）
 * 如需热刷新，使用普通类 + @RefreshScope（见下方示例）
 */
@ConfigurationProperties(prefix = "app")
record AppConfig(String message, String version) {}

@RestController
class ConfigRecordController {

    private final AppConfig appConfig;

    ConfigRecordController(AppConfig appConfig) {
        this.appConfig = appConfig;
    }

    @GetMapping("/config/record")
    public String getConfigByRecord() {
        return String.format(
            "Boot 4.x [Record] message=%s, version=%s",
            appConfig.message(),
            appConfig.version()
        );
    }
}

/**
 * 方式二：@Value + @RefreshScope（支持热刷新）
 *
 * 刷新命令（4.x，与 3.x 相同）：
 *   curl -X POST http://localhost:8080/actuator/refresh
 *
 * 响应：{"changed": ["app.message", "app.version"]}（4.x 返回格式）
 */
@RestController
@RefreshScope
class ConfigRefreshController {

    @Value("${app.message:default-message}")
    private String message;

    @Value("${app.version:0.0.1}")
    private String version;

    @GetMapping("/config/refresh")
    public String getRefreshableConfig() {
        return String.format(
            "Boot 4.x [@RefreshScope] message=%s, version=%s",
            message, version
        );
    }
}
