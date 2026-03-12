package com.example.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.context.config.annotation.RefreshScope;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Spring Boot 2.x Config Client
 *
 * 2.x 主要变化：
 * 1. /refresh 端点路径变为 /actuator/refresh
 * 2. 可配合 Spring Cloud Bus 实现广播刷新（所有实例同时刷新）
 * 3. Spring Boot 2.4+ 推荐用 spring.config.import 替代 bootstrap.yml
 */
@SpringBootApplication
public class ConfigClientApplication {

    public static void main(String[] args) {
        SpringApplication.run(ConfigClientApplication.class, args);
    }
}

/**
 * @RefreshScope 使用方式与 1.x 相同
 * 刷新命令（2.x）：
 *   curl -X POST http://localhost:8080/actuator/refresh
 *
 * 配合 Spring Cloud Bus + RabbitMQ 广播刷新：
 *   curl -X POST http://localhost:8080/actuator/bus-refresh
 *   （所有注册到总线的服务都会刷新，无需逐个调用）
 */
@RestController
@RefreshScope
class ConfigDemoController {

    @Value("${app.message:default-message}")
    private String message;

    @Value("${app.version:0.0.1}")
    private String version;

    @GetMapping("/config")
    public String getConfig() {
        return String.format("Boot 2.x | message=%s, version=%s", message, version);
    }
}

/**
 * 使用 @ConfigurationProperties 的推荐方式（配合 @RefreshScope 效果相同）
 */
// @Component
// @ConfigurationProperties(prefix = "app")
// @RefreshScope
// class AppProperties {
//     private String message;
//     private String version;
//     // getter/setter...
// }
