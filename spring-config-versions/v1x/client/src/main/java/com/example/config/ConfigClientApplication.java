package com.example.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.context.config.annotation.RefreshScope;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Spring Boot 1.x Config Client 启动类
 */
@SpringBootApplication
public class ConfigClientApplication {

    public static void main(String[] args) {
        SpringApplication.run(ConfigClientApplication.class, args);
    }
}

/**
 * 演示从 Config Server 获取配置的 Controller
 *
 * @RefreshScope：标注后，调用 POST /refresh 端点可刷新该 Bean 中的配置值
 * 注意：1.x 中刷新端点是 POST http://localhost:8080/refresh
 */
@RestController
@RefreshScope
class ConfigDemoController {

    /**
     * 从 Config Server 获取的配置值
     * 对应 Git 仓库中 myapp-dev.yml 内的 app.message 属性
     */
    @Value("${app.message:default-message}")
    private String message;

    @Value("${app.version:0.0.1}")
    private String version;

    @GetMapping("/config")
    public String getConfig() {
        return "message=" + message + ", version=" + version;
    }

    /**
     * 手动触发配置刷新（1.x）：
     *   curl -X POST http://localhost:8080/refresh
     *
     * 响应示例：["app.message","app.version"]（返回变化的 key 列表）
     */
}
